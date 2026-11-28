#!/usr/bin/env python3
"""Scan text files for secret-looking values before they leave the machine.

Skills that write files meant for other people — a context brief pasted
into a third-party web AI, issue evidence committed to a shared docs repo —
run this as a blocking gate. It is deterministic: the agent does not judge
by eye whether a log line holds a token.

Findings never print the secret: each shows the rule, the location, and a
masked excerpt (first 4 characters plus the length).

A line containing the marker `secret-scan: allow` is skipped, so a
confirmed false positive can be acknowledged in place.

Usage:
    python3 secret_scan.py <file-or-dir> [<file-or-dir> ...]

Output (machine-readable lines):
    FINDING=<path>:<line> | <rule> | <masked excerpt>
    SKIPPED=<path> (binary)
    STATUS=PASS|FAIL  FILES=<n>  FINDINGS=<n>

Exit codes:
    0 — no findings
    1 — at least one finding (the caller must redact before writing/committing)
    2 — usage error (no arguments, or a path that does not exist)
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ALLOW_MARKER = "secret-scan: allow"

# (rule name, pattern). The value to mask is group "v" when present,
# otherwise the whole match.
RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----")),
    ("aws-access-key-id", re.compile(r"\b(?P<v>(?:AKIA|ASIA)[0-9A-Z]{16})\b")),
    (
        "github-token",
        re.compile(r"\b(?P<v>(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}))"),
    ),
    ("slack-token", re.compile(r"\b(?P<v>xox[abposr]-[A-Za-z0-9-]{10,})")),
    ("anthropic-key", re.compile(r"\b(?P<v>sk-ant-[A-Za-z0-9_-]{20,})")),
    ("openai-style-key", re.compile(r"\b(?P<v>sk-(?:proj-)?[A-Za-z0-9_-]{20,})")),
    ("stripe-live-key", re.compile(r"\b(?P<v>(?:sk|rk)_live_[A-Za-z0-9]{16,})")),
    ("google-api-key", re.compile(r"\b(?P<v>AIza[0-9A-Za-z_-]{35})")),
    (
        "jwt",
        re.compile(r"\b(?P<v>eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})"),
    ),
    (
        "authorization-header",
        re.compile(
            r"(?i)\bauthorization\b[\"']?\s*[:=]\s*[\"']?(?:bearer|basic|token)\s+"
            r"(?P<v>[A-Za-z0-9._~+/=-]{12,})"
        ),
    ),
    (
        "url-credentials",
        re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@]+:(?P<v>[^\s/@]{3,})@[^\s/]+", re.I),
    ),
    (
        "credential-assignment",
        re.compile(
            r"(?i)\b[\w.-]*(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?key|"
            r"auth[_-]?token|access[_-]?token|private[_-]?key|client[_-]?secret)"
            r"[\"']?\s*[:=]\s*[\"']?(?P<v>[^\s\"',;]{8,})"
        ),
    ),
)

# A run of token characters long and random enough to be a key even when no
# known prefix or variable name announces it.
# `/` and `.` are excluded so long file paths and dotted names never match.
HIGH_ENTROPY_RE = re.compile(r"(?<![A-Za-z0-9+_=-])(?P<v>[A-Za-z0-9+_=-]{40,})")
HIGH_ENTROPY_MIN_BITS = 4.5

# Values that are documentation, not secrets.
PLACEHOLDER_RE = re.compile(
    r"(?i)^(?:<[^>]*>|\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|%\(?[A-Za-z_]+\)?s?|"
    r"\{\{.*\}\}|x{4,}|\*{3,}|\.{3,}|\[redacted\]|redacted|changeme|"
    r"your[_-].*|example.*|dummy.*|placeholder.*|none|null|true|false)$"
)


@dataclass(frozen=True)
class Finding:
    """One secret-looking value: where it is and which rule matched."""

    line: int
    rule: str
    excerpt: str


def mask(value: str) -> str:
    """Return a masked form that identifies a value without revealing it."""
    head = value[:4] if len(value) > 8 else ""
    return f"{head}…[{len(value)} chars]"


def shannon_entropy(value: str) -> float:
    """Bits of entropy per character of `value`."""
    if not value:
        return 0.0
    counts: dict[str, int] = {}
    for char in value:
        counts[char] = counts.get(char, 0) + 1
    total = len(value)
    return -sum(n / total * math.log2(n / total) for n in counts.values())


def _is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_RE.match(value.strip("\"'`")))


def _looks_random(value: str) -> bool:
    """Mixed case plus digits and high entropy — not a hash, path, or word."""
    return (
        any(c.islower() for c in value)
        and any(c.isupper() for c in value)
        and any(c.isdigit() for c in value)
        and shannon_entropy(value) >= HIGH_ENTROPY_MIN_BITS
    )


def scan_text(text: str) -> list[Finding]:
    """Return every secret-looking value in `text`, one finding per span."""
    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), 1):
        if ALLOW_MARKER in line:
            continue
        covered: list[tuple[int, int]] = []
        for rule, pattern in RULES:
            for match in pattern.finditer(line):
                has_value = "v" in pattern.groupindex and match.group("v")
                value = match.group("v") if has_value else match.group(0)
                start, end = match.span("v") if has_value else match.span()
                if _is_placeholder(value):
                    continue
                if any(s <= start < e for s, e in covered):
                    continue
                covered.append((start, end))
                findings.append(Finding(number, rule, mask(value)))
        for match in HIGH_ENTROPY_RE.finditer(line):
            start, end = match.span("v")
            if any(s <= start < e or start <= s < end for s, e in covered):
                continue
            value = match.group("v")
            if _looks_random(value):
                covered.append((start, end))
                findings.append(Finding(number, "high-entropy-string", mask(value)))
    return findings


def _is_binary(data: bytes) -> bool:
    return b"\0" in data[:8192]


def iter_files(paths: list[Path]) -> list[Path]:
    """Expand directories into their files (sorted, `.git/` skipped)."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(
                p
                for p in sorted(path.rglob("*"))
                if p.is_file() and ".git" not in p.relative_to(path).parts
            )
        else:
            files.append(path)
    return files


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in ("-h", "--help"):
        print("Usage: secret_scan.py <file-or-dir> [<file-or-dir> ...]", file=sys.stderr)
        return 2
    paths = [Path(arg) for arg in args]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print(f"ERROR: path not found: {', '.join(missing)}", file=sys.stderr)
        return 2

    files = iter_files(paths)
    total = 0
    for file in files:
        try:
            data = file.read_bytes()
        except OSError as exc:
            print(f"ERROR: cannot read {file}: {exc}", file=sys.stderr)
            return 2
        if _is_binary(data):
            print(f"SKIPPED={file} (binary)")
            continue
        for finding in scan_text(data.decode("utf-8", errors="replace")):
            total += 1
            print(f"FINDING={file}:{finding.line} | {finding.rule} | {finding.excerpt}")
    status = "PASS" if total == 0 else "FAIL"
    print(f"STATUS={status}  FILES={len(files)}  FINDINGS={total}")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
