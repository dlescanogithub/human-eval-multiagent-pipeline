from __future__ import annotations

import argparse
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
}
PLACEHOLDERS = {"changeme", "your-key-here", "todo", "unset", "none", ""}


@dataclass(frozen=True)
class SecretFinding:
    path: str
    line: int
    rule: str


def _patterns() -> list[tuple[str, re.Pattern[str]]]:
    private = "-----BEGIN " + "PRIVATE KEY-----"
    rsa = "-----BEGIN " + "RSA PRIVATE KEY-----"
    openssh = "-----BEGIN " + "OPENSSH PRIVATE KEY-----"
    return [
        ("private_key", re.compile(re.escape(private))),
        ("private_key", re.compile(re.escape(rsa))),
        ("private_key", re.compile(re.escape(openssh))),
        ("aws_access_key", re.compile("AKIA" + r"[0-9A-Z]{16}")),
        ("openai_style_key", re.compile(r"sk-" + r"[A-Za-z0-9]{20,}")),
        ("github_token", re.compile(r"ghp_" + r"[A-Za-z0-9]{20,}")),
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
