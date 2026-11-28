"""Every shipped Python file must parse on the oldest supported Python (3.10).

`pyproject.toml` declares `requires-python = ">=3.10"`, but tests usually run
on a newer interpreter. `ast.parse(feature_version=(3, 10))` catches most
newer syntax, yet NOT the f-string relaxations of PEP 701 (Python 3.12): a
backslash or a reused quote inside an f-string's `{...}` parses on 3.12 and
is a SyntaxError on 3.10/3.11. On 3.12+ this test therefore also inspects
each f-string replacement field's source text for those two constructs.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOTS = (REPO_ROOT / "mythril_agent_skills", REPO_ROOT / "scripts")


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in ROOTS:
        files.extend(
            path for path in root.rglob("*.py") if "__pycache__" not in path.parts
        )
    return sorted(files)


def _string_quote(segment: str) -> str:
    """Return the opening quote (`'`, `"`, `'''` or `\"\"\"`) of a literal."""
    body = segment.lstrip("rRbBfFuU")
    for quote in ('"""', "'''", '"', "'"):
        if body.startswith(quote):
            return quote
    return ""


def pep701_violations(source: str) -> list[str]:
    """Return f-string constructs that only Python 3.12+ accepts.

    Checks each replacement field's expression text for a backslash, and
    for the enclosing f-string's own quote, both of which pre-3.12
    tokenizers reject. Format specs are not inspected.
    """
    tree = ast.parse(source)
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr):
            continue
        outer = ast.get_source_segment(source, node) or ""
        quote = _string_quote(outer)
        for value in node.values:
            if not isinstance(value, ast.FormattedValue):
                continue
            expr = ast.get_source_segment(source, value.value) or ""
            if "\\" in expr:
                problems.append(
                    f"line {value.lineno}: backslash inside f-string expression"
                )
            elif quote and quote in expr:
                problems.append(
                    f"line {value.lineno}: f-string expression reuses the "
                    f"enclosing quote {quote}"
                )
    return problems


class TestPep701Detector:
    """The detector must flag what 3.10 rejects and pass what it accepts."""

    @pytest.mark.skipif(sys.version_info < (3, 12), reason="needs PEP 701 parser")
    def test_backslash_in_nested_fstring_is_flagged(self):
        src = 'x = ""\ny = f"""a {x and f"  {x}\\n"} b"""\n'
        assert pep701_violations(src)

    @pytest.mark.skipif(sys.version_info < (3, 12), reason="needs PEP 701 parser")
    def test_reused_quote_is_flagged(self):
        src = 'd = {}\ny = f"{d["k"]}"\n'
        assert pep701_violations(src)

    def test_plain_fstrings_pass(self):
        src = 'x = 1\nnote = "\\n"\ny = f"{x!r} {note} {x:>4}"\nz = f"""{"a"}"""\n'
        assert pep701_violations(src) == []


@pytest.mark.parametrize(
    "path", _python_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_parses_on_python_310(path: Path):
    source = path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(path), feature_version=(3, 10))
    if sys.version_info >= (3, 12):
        assert pep701_violations(source) == [], (
            f"{path.relative_to(REPO_ROOT)} uses f-string syntax that "
            "Python 3.10/3.11 reject; build the value outside the f-string"
        )
