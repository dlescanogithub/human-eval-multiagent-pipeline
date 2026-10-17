from __future__ import annotations

import html
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from hemp.errors import SchemaError
from hemp.models import ReviewLabel
from hemp.review.queue import add_label, dump_queue, load_queue, save_queue


def render_queue(payload_items: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for item in payload_items:
        claims = item.get("claims", [])
        claim_html = "".join(
            f"<li>{html.escape(str(claim.get('text', '')))} "
            f"<code>{html.escape(', '.join(claim.get('citation_ids', [])))}</code></li>"
            for claim in claims
            if isinstance(claim, dict)
        )
        labels = item.get("labels", [])
        label_html = "".join(
            f"<li>{html.escape(str(label.get('rater_id', '')))} "
            f"synthetic={html.escape(str(label.get('synthetic')))}</li>"
            for label in labels
            if isinstance(label, dict)
        )
        piece = html.escape(str(item.get("piece_id", "")))
        form = ""
        if item.get("status") == "pending":
            form = (
                f"<form method='post' action='/decide'>"
                f"<input type='hidden' name='piece' value='{piece}'/>"
                f"<label>Rater <input name='rater' required></label> "
                f"<label>accuracy <input name='accuracy' value='5'></label> "
                f"<label>clarity <input name='clarity' value='5'></label> "
                f"<label>flow <input name='flow' value='5'></label> "
                f"<label>no_redundancy <input name='no_redundancy' value='5'></label> "
                f"<label>safety <input name='safety' value='5'></label> "
                f"<label><input type='checkbox' name='synthetic'> synthetic</label> "
                f"<button type='submit'>Record</button></form>"
            )
        blocks.append(
            "<article>"
            f"<h2>{html.escape(str(item.get('title', '')))}</h2>"
            f"<p>{piece} — {html.escape(str(item.get('status', '')))} "
            f"(needs {html.escape(str(item.get('required_raters', '')))})</p>"
            f"<p>{html.escape(str(item.get('body', '')))}</p>"
            f"<ul>{claim_html}</ul><ul>{label_html}</ul>{form}</article>"
        )
    body = "\n".join(blocks) or "<p>Queue is empty.</p>"
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Nortia review queue</title>"
        "<style>body{font-family:sans-serif;max-width:46rem;margin:2rem auto;line-height:1.4}"
        "article{border-top:1px solid #ccc;padding:1rem 0}</style></head><body>"
        "<h1>Nortia Learning review queue</h1>"
        "<p>Local only. 100% synthetic domain. Nothing here is a real course.</p>"
        f"{body}</body></html>"
    )


class ReviewApp:
    def __init__(self, queue_path: Path) -> None:
        self.queue_path = queue_path

    def dispatch(self, method: str, path: str, body: bytes) -> tuple[int, str, bytes]:
        route = path.split("?", 1)[0]
        if method == "GET" and route == "/health":
            return 200, "application/json", b'{"ok":true,"network":"local"}'
        if method == "GET" and route == "/":
            _version, _mins, items = load_queue(self.queue_path)
            page = render_queue([item.to_dict() for item in items])
            return 200, "text/html; charset=utf-8", page.encode("utf-8")
        if method == "POST" and route == "/decide":
            try:
                return self._decide(body)
            except (ValueError, SchemaError):
                return 400, "text/plain; charset=utf-8", b"bad form"
        return 404, "text/plain; charset=utf-8", b"not found"

    def _decide(self, body: bytes) -> tuple[int, str, bytes]:
        form = parse_qs(body.decode("utf-8"))
        piece = _one(form, "piece")
        rater = _one(form, "rater")
        version, mins, items = load_queue(self.queue_path)
        scores = {
            "accuracy": _int_field(form, "accuracy"),
            "clarity": _int_field(form, "clarity"),
            "flow": _int_field(form, "flow"),
            "no_redundancy": _int_field(form, "no_redundancy"),
            "safety": _int_field(form, "safety"),
        }
        label = ReviewLabel(rater, scores, "synthetic" in form)
        updated = []
        found = False
        for item in items:
            if item.piece_id == piece:
                updated.append(add_label(item, label, mins))
                found = True
            else:
                updated.append(item)
        if not found:
            return 404, "text/plain; charset=utf-8", b"unknown piece"
        save_queue(
            self.queue_path,
            dump_queue(tuple(updated), rubric_version=version, mins=mins),
        )
        return 303, "text/plain", b"see /"


def _one(form: dict[str, list[str]], key: str) -> str:
    values = form.get(key, [])
    if not values or not values[0].strip():
        raise ValueError(f"missing {key}")
    return values[0].strip()


def _int_field(form: dict[str, list[str]], key: str) -> int:
    return int(_one(form, key))


def serve(
    queue_path: Path,
    port: int,
    *,
    server_factory: Callable[..., Any] = ThreadingHTTPServer,
) -> None:
    app = ReviewApp(queue_path)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._send(*app.dispatch("GET", self.path, b""))

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(length) if length else b""
            self._send(*app.dispatch("POST", self.path, payload))

        def _send(self, status: int, content_type: str, payload: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            if status == 303:
                self.send_header("Location", "/")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    server = server_factory(("127.0.0.1", port), Handler)
    server.serve_forever()
