"""Vendored secret scanner.

This file is maintained in parallel across portfolio repositories and kept
aligned. docs/PROVENANCE.md records the sha256 of this copy.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "artifacts",
    "dist",
    "build",
    ".eggs",
    "var",
}
PLACEHOLDERS = {"changeme", "your-key-here", "todo", "unset", "none", ""}


@dataclass(frozen=True)
class SecretFinding:
    path: str
    line: int
    rule: str


def _pem(kind: str) -> str:
    return "-----BEGIN " + kind + "-----"


def _patterns() -> list[tuple[str, re.Pattern[str]]]:
    """More specific token shapes are listed before the generic ``sk-`` shape."""
    url_safe = r"[A-Za-z0-9._~-]{20,}"
    alnum = r"[A-Za-z0-9]{20,}"
    return [
        ("private_key", re.compile(re.escape(_pem("PRIVATE KEY")))),
        ("private_key", re.compile(re.escape(_pem("RSA PRIVATE KEY")))),
        ("private_key", re.compile(re.escape(_pem("OPENSSH PRIVATE KEY")))),
        ("private_key", re.compile(re.escape(_pem("EC PRIVATE KEY")))),
        ("private_key", re.compile(re.escape(_pem("DSA PRIVATE KEY")))),
        ("private_key", re.compile(re.escape(_pem("PGP PRIVATE KEY BLOCK")))),
        ("anthropic_key", re.compile("sk-ant-" + url_safe)),
        ("openai_key", re.compile("sk-proj-" + url_safe)),
        ("openai_key", re.compile("sk-" + alnum)),
        ("xai_key", re.compile("xai-" + url_safe)),
        ("elevenlabs_key", re.compile("sk_" + alnum)),
        ("github_token", re.compile("ghp_" + alnum)),
        ("github_token", re.compile("github_pat_" + r"[A-Za-z0-9_]{20,}")),
        ("aws_access_key", re.compile("AKIA" + r"[0-9A-Z]{16}")),
        ("bearer_token", re.compile(r"(?i)Bearer\s+" + r"[A-Za-z0-9._~+/-]{20,}")),
        ("slack_token", re.compile(r"xox[baprs]-" + r"[A-Za-z0-9-]{10,}")),
        (
            "assigned_secret",
            re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\b\s*=\s*['\"]([^'\"]+)['\"]"),
        ),
    ]


def scan(root: Path) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    patterns = _patterns()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix == ".egg-info" or path.name.endswith(".egg-info"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "\0" in text[:1024]:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for rule, pattern in patterns:
                match = pattern.search(line)
                if match is None:
                    continue
                if rule == "assigned_secret":
                    value = match.group(2).strip().lower()
                    if value in PLACEHOLDERS or len(value) < 16:
                        continue
                findings.append(SecretFinding(str(path), line_number, rule))
                break
    return findings


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hemp.secretscan")
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    findings = scan(Path(args.root))
    if findings:
        for finding in findings:
            print(f"{finding.path}:{finding.line}: {finding.rule}")
        return 1
    print("secretscan: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
