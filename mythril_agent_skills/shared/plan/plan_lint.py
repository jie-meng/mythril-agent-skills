#!/usr/bin/env python3
"""Lint the work-tracking documents for cross-document consistency.

The four documents are a causal chain (analysis → plan → progress →
review) and each one is edited independently during planning and
implementation, so they drift. This script checks the drift that LLM
reviewers routinely miss, deterministically and cheaply.

Checks:

1. **Success Criteria ↔ Evidence rows** — `review.md`'s Evidence table
   must hold exactly one row per Success Criterion id in `plan.md`. A
   revision that adds a criterion and forgets the table is the classic
   case (an unverifiable criterion enters the definition of done).
2. **Plan-review closure** — the last `## Plan Review` / `## 方案审查`
   round must end in `PASS` or `PASS_WITH_RISKS`. A `NEEDS_FIXES` round
   with no successor round means review-driven revisions were self-
   attested and never independently verified.
3. **Round numbering** — plan-review rounds must run 1..N ascending
   without gaps or duplicates, so "round 2+" can be scoped to the
   previous findings.
4. **Task ids** — every task id cited in `review.md` must exist in
   `plan.md`; a review that references a removed task cannot be acted on.
5. **Unresolved placeholders** — `待确认` / `待定` / `TBD` in `analysis.md`
   or `plan.md` are warnings: they must become a formal
   `NEEDS_USER_DECISION`, not stay a parenthetical nobody answers.
6. **Requirements of record** — `analysis.md` carries a `## 需求原文` /
   `## Original Requirements` section holding the user's words verbatim,
   each under a `REQ<n>` id. That section is the baseline the
   requirements-coverage matrix is falsified against; without it,
   "was a requirement dropped or narrowed?" has nothing to compare to
   except the planner's own summary — the party being audited. Every
   `REQ` cited in a review round's coverage matrix must exist there, and
   every declared `REQ` must have a row in at least one round's matrix —
   a prose mention never counts as coverage.
7. **Finding discipline** — a round listing more than five P2 findings,
   or a later round carrying more P0/P1 than the round before it
   (oscillation). Both are capped in prose by the reviewer's brief;
   neither is checkable by a reader scanning the document.
8. **Decision-reader summary** — `plan.md` should open with a
   `## 摘要` / `## Summary` section: the one place a person can read in
   30 seconds what the problem is, what the approach is, what needs
   deciding, and where to read next. Heading matching reuses
   `find_section_body`'s prefix match, so a parenthetical suffix
   (`## 摘要（给人读的——…）`) still hits.
9. **Code Map** — `plan.md` carries a `## 代码地图` / `## Code Map` table
   of the files this work item owns, one row per file, as
   `<repo> | <repo-relative path> | <symbols> | <what changed>`. It is
   the reverse index: a later reader holding a file path or a function
   name uses it to find which document authorized that code. A path that
   changed but is not listed cannot be traced back, so the follow-up
   that invalidates the design never finds the document it should have
   updated. Rows that a lookup cannot hit are rejected: a wildcard
   (`src/ui/*`), a directory, a placeholder, and more than one file in
   the path cell — each silently drops traceability for the files it
   pretends to cover. A path with no directory is a warning, since only a
   file at the repo root can honestly be written that way.
10. **Document sync attestation** — every code-review round must carry a
    `**文档同步**` / `**Document Sync**` paragraph naming all four documents,
    each followed by a clause stating what this round did to it (or why
    nothing changed). Code-touching rounds are the moments the documents
    go stale, and "did I break a diagram in analysis.md by moving this
    responsibility?" is exactly the question a fast fix round does not ask
    itself. The line forces the answer to be written down, so naming the
    four files with no clause after them does not pass. Rounds are
    recognized in both heading styles the format doc sanctions —
    `## 代码审查` / `## Code Review` and the legacy `## <repo> — Review
    Round N` — because a follow-up round is written in whatever style the
    item already uses. The **newest** round is always required — it is the
    one being written now, and it is the round a follow-up fix produces;
    earlier rounds are never back-filled, so an item that predates the
    convention is not asked to invent history it did not record.

Checks 5, 7 and 8 are warnings because none of them breaks the chain.
Checks 1-4, 6, 9 and 10 are errors: each one lets an unverifiable claim
enter the definition of done, or leaves the work item untraceable from
its own code. Item 6 stays silent for work items that have
neither the section nor a coverage matrix, so legacy items do not
generate noise. Item 8 warns rather than errors for the same reason in
mirror image: work items written before the summary existed have no
section to find, and the lint only runs on active work-item gates, so
it never re-scans archived items.

## Reverse lookup mode

`--find <path-or-symbol>` answers the other direction of the same
question: given a file or function someone just reported a problem with,
which work item owns it. It scans every work directory under the docs
dir — active and archived — and reports Code Map hits first, then prose
mentions as candidates. This is what makes "update the docs" executable
rather than something the user has to say twice.

Usage:
    python3 plan_lint.py <work-dir>
    python3 plan_lint.py --quiet <work-dir>
    python3 plan_lint.py --find api/src/preferences/dark_mode.py
    python3 plan_lint.py --find ThemePreference <docs-dir>

Output (one field per line, machine-readable):
    STATUS=PASS|FAIL
    CHECKS=<n>  WARNINGS=<n>
    ERROR: <message>
    WARN: <message>

`--find` output:
    STATUS=OWNER|CANDIDATE|NONE
    CODEMAP: <work-dir> | <repo> | <path> | <symbols> | <change>
    SUBSTRING: <work-dir> | <repo> | <path> | <symbols> | <change>
    MENTION: <work-dir> | <file>:<line> | <text>
    HITS=<n>

Only `CODEMAP:` lines are ownership. `SUBSTRING:` rows matched a bare
name or a substring, and `MENTION:` lines are prose — both are places to
look, not claims that the item owns the file.

Exit codes: in lint mode 0=PASS, 1=FAIL, 2=bad path or usage. In `--find`
mode 0 is returned only for STATUS=OWNER; CANDIDATE and NONE both exit 1,
and 2 means no docs directory could be found. A nonzero lookup exit always
means "ask before editing", so reading exit 0 as "owner found" is safe.
Findings are emitted in
check order; the STATUS line always comes first.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PLAN_FILE = "plan.md"
ANALYSIS_FILE = "analysis.md"
PROGRESS_FILE = "progress.md"
REVIEW_FILE = "review.md"
DOC_FILES = (ANALYSIS_FILE, PLAN_FILE, PROGRESS_FILE, REVIEW_FILE)

SC_ID_RE = re.compile(r"\bSC\d+[a-z]?\b")
TASK_ID_RE = re.compile(r"\bT\d+[a-z]?\b")
REQ_ID_RE = re.compile(r"\bREQ\d+\b")
ROUND_NUMBER_RE = re.compile(r"(?:Round|第)\s*(\d+)")

# Longest first: PASS_WITH_RISKS must be matched before PASS.
VERDICTS = ("PASS_WITH_RISKS", "NEEDS_USER_DECISION", "NEEDS_FIXES", "PASS")
VERDICT_RE = re.compile(r"\b(" + "|".join(VERDICTS) + r")\b")

PLACEHOLDER_RE = re.compile(r"待确认|待定|\bTBD\b")

EVIDENCE_HEADINGS = ("## 证据核验", "## Evidence")
REQUIREMENTS_HEADINGS = ("## 需求原文", "## Original Requirements")
SUMMARY_HEADINGS = ("## 摘要", "## Summary")
CODE_MAP_HEADINGS = ("## 代码地图", "## Code Map")
CODE_REVIEW_HEADINGS = ("## 代码审查", "## Code Review")
# Items written before the prefixed convention title their code rounds
# `## <repo> — Review Round 3`. A follow-up round inherits that style, so
# keying only on the prefix would let the newest round escape check 10.
LEGACY_CODE_REVIEW_RE = re.compile(r"^##\s.*\bReview Round\b", re.IGNORECASE)
ATTESTATION_RE = re.compile(
    r"\*\*\s*(?:文档同步|Document Sync|Docs ?Synced?)\s*\*\*", re.IGNORECASE
)
# The sub-section the format puts the attestation in.
ATTESTATION_HEAD_RE = re.compile(
    r"^#{2,4}\s*(?:文档同步|Document Sync)\b", re.IGNORECASE
)
# A document name counts as answered only when a clause follows it.
ATTESTED_DOC_RES = {
    doc: re.compile(re.escape(doc) + r"[`'\"”]\s*(?:——|—|–|:|：|-)\s*(\S.*)", re.IGNORECASE)
    for doc in DOC_FILES
}
WILDCARD_RE = re.compile(r"[*?\[\]]")
MULTI_PATH_RE = re.compile(r"[,，、]|\.\w+\s+\S+[\w./]*\.\w+")
PLACEHOLDER_PATH_RE = re.compile(r"^(?:—|-+|<[^\n>]*>|\{\{?[^\n}]*\}?\}|待定|TBD)$", re.IGNORECASE)
CONFIG_FILENAME = "fullstack.json"
WORK_ITEM_TYPES = ("feat", "refactor", "fix")
MAX_MENTIONS_PER_ITEM = 3
MAX_DOCS_DIR_WALK_UP = 6
PLAN_REVIEW_HEADING_RE = re.compile(r"^##\s+(?:Plan Review|方案审查)\b", re.MULTILINE)
VERDICT_HEADING_RE = re.compile(
    r"^#{3,}\s*(?:Verdict|判定|结论)", re.MULTILINE
)
COVERAGE_HEADING_RE = re.compile(
    r"^#{3,}\s*(?:Requirements Coverage|需求覆盖)", re.MULTILINE
)
HEADING_RE = re.compile(r"^##\s+(.*)$", re.MULTILINE)

# A finding bullet is `- [P0] ...` / `* [P1] ...` per the reviewer's output
# contract in agents/plan-reviewer.md.
SEVERITY_BULLET_RE = re.compile(r"^\s*[-*]\s*\[P([0-9])\]", re.MULTILINE)
MAX_P2_PER_ROUND = 5

CLOSING_VERDICTS = ("PASS", "PASS_WITH_RISKS")


@dataclass(frozen=True)
class Finding:
    """One lint result. `level` is "ERROR" or "WARN"."""

    level: str
    message: str


@dataclass(frozen=True)
class PlanReviewRound:
    """One `## Plan Review — Round N` section."""

    number: int
    heading: str
    body: str
    verdict: str | None


def read(path: Path) -> str:
    """Return a file's text, or "" when it does not exist."""
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into (heading_line, body) pairs on `##` headings.

    Content before the first `##` heading is returned under an empty
    heading, so callers can still search it.
    """
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [("", text)]
    sections: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        sections.append(("", text[: matches[0].start()]))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(0).strip(), text[match.start() : end]))
    return sections


def parse_sc_ids(text: str) -> set[str]:
    """Return every `SC<n>` id used in the text."""
    return set(SC_ID_RE.findall(text))


def parse_task_ids(text: str) -> set[str]:
    """Return every `T<n>` id used in the text."""
    return set(TASK_ID_RE.findall(text))


def parse_req_ids(text: str) -> set[str]:
    """Return every `REQ<n>` id used in the text."""
    return set(REQ_ID_RE.findall(text))


def find_section_body(text: str, headings: tuple[str, ...]) -> str | None:
    """Return the body of the first section matching one of `headings`."""
    for heading, body in split_sections(text):
        if heading.startswith(headings):
            return body
    return None


def count_severities(body: str) -> dict[str, int]:
    """Return how many `- [P<n>]` bullets a review round carries."""
    counts = {"0": 0, "1": 0, "2": 0}
    for severity in SEVERITY_BULLET_RE.findall(body):
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def parse_evidence_rows(review_text: str) -> set[str] | None:
    """Return the SC ids in the Evidence table, or None when absent.

    Only rows of a markdown table inside the Evidence section count, so a
    criterion mentioned in prose does not mask a missing row.
    """
    for heading, body in split_sections(review_text):
        if heading.startswith(EVIDENCE_HEADINGS):
            rows: set[str] = set()
            for line in body.splitlines():
                if not line.lstrip().startswith("|"):
                    continue
                first_cell = line.lstrip().lstrip("|").split("|")[0]
                rows.update(SC_ID_RE.findall(first_cell))
            return rows
    return None


def parse_coverage_rows(review_text: str) -> set[str] | None:
    """Return the REQ ids rowed in every plan-review coverage matrix.

    Only table rows inside a `### 需求覆盖` / `### Requirements Coverage`
    section of a plan-review round count, so a REQ named in a finding
    bullet or in prose does not. Returns None when no coverage matrix
    exists in any round.
    """
    found = False
    ids: set[str] = set()
    for heading, body in split_sections(review_text):
        if not heading.startswith("## ") or not PLAN_REVIEW_HEADING_RE.match(
            heading
        ):
            continue
        in_matrix = False
        for line in body.splitlines():
            if COVERAGE_HEADING_RE.match(line.strip()):
                found = True
                in_matrix = True
                continue
            if line.lstrip().startswith("#"):
                in_matrix = False
                continue
            if in_matrix and line.lstrip().startswith("|"):
                first_cell = line.lstrip().lstrip("|").split("|")[0]
                ids.update(REQ_ID_RE.findall(first_cell))
    return ids if found else None


def detect_verdict(section_body: str) -> str | None:
    """Return the verdict a plan-review section ends on.

    Prefers the token that follows the last verdict heading
    (`### Verdict` / `### 判定` / `### 结论`); a section that writes the
    gate results ("Mermaid PASS") before its verdict must not be read as
    a PASS. Falls back to the last verdict token in the section.
    """
    headings = list(VERDICT_HEADING_RE.finditer(section_body))
    if headings:
        tail = section_body[headings[-1].end() :]
        match = VERDICT_RE.search(tail)
        if match:
            return match.group(1)
    matches = list(VERDICT_RE.finditer(section_body))
    return matches[-1].group(1) if matches else None


def parse_plan_review_rounds(review_text: str) -> list[PlanReviewRound]:
    """Return every plan-review round in document order."""
    rounds: list[PlanReviewRound] = []
    for heading, body in split_sections(review_text):
        if not heading.startswith("## ") or not PLAN_REVIEW_HEADING_RE.match(heading):
            continue
        number_match = ROUND_NUMBER_RE.search(heading)
        number = int(number_match.group(1)) if number_match else 0
        rounds.append(
            PlanReviewRound(
                number=number,
                heading=heading,
                body=body,
                verdict=detect_verdict(body),
            )
        )
    return rounds


def find_placeholders(text: str) -> list[str]:
    """Return the distinct lines carrying an unresolved placeholder.

    Two false positives are filtered out, because flagging them trains the
    reader to ignore the check: a heading that merely names the section
    ("## Risks / Open Questions") states nothing, and a *negated* mention
    ("无待确认问题", "no TBD") declares the opposite of a placeholder.
    """
    hits: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for match in PLACEHOLDER_RE.finditer(line):
            before = line[max(0, match.start() - 3) : match.start()]
            if "无" in before or "no " in before.lower():
                continue
            hits.append(stripped)
            break
    return hits


def parse_code_map_rows(plan_text: str) -> list[dict[str, str]] | None:
    """Return the Code Map data rows of `plan.md`, or None when absent.

    One dict per table row: repository, path, symbols, change. Header and
    separator rows are dropped, and a row without both a repository and a
    path is not counted — a prose paragraph under the heading is not a
    map.
    """
    body = find_section_body(plan_text, CODE_MAP_HEADINGS)
    if body is None:
        return None

    rows: list[dict[str, str]] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if all(not c or set(c) <= set("-: ") for c in cells):
            continue
        if cells[0].lower() in {"repository", "仓库"} or cells[1].lower() in {
            "path",
            "路径",
        }:
            continue
        if not cells[0] or not cells[1]:
            continue
        rows.append(
            {
                "repository": cells[0],
                "path": cells[1],
                "symbols": cells[2] if len(cells) > 2 else "",
                "change": cells[3] if len(cells) > 3 else "",
            }
        )
    return rows


def normalize_path(value: str) -> str:
    """Return a path comparable across the ways a reader may spell it."""
    text = value.strip().strip("`").replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    text = re.sub(r"/{2,}", "/", text)
    return text.lower().lstrip("/").rstrip("/")


def code_map_row_candidates(row: dict[str, str]) -> list[str]:
    """Return the spellings a Code Map row answers to (repo-relative and not)."""
    path = normalize_path(row["path"])
    repo = normalize_path(row["repository"])
    candidates = [path]
    if repo and repo not in {"—", "-", "—"}:
        candidates.append(f"{repo}/{path}")
    return candidates


def match_code_map_row(needle: str, row: dict[str, str]) -> int:
    """Score one Code Map row against a lookup needle.

    3 = whole path, 2 = trailing path segment or symbol, 1 = substring,
    0 = no match. The score exists so a lookup for `src/x.py` does not
    rank a `docs/x.py` row beside the real owner.
    """
    target = normalize_path(needle)
    if not target:
        return 0
    candidates = code_map_row_candidates(row)
    if target in candidates:
        return 3
    for candidate in candidates:
        base = candidate.rsplit("/", 1)[-1]
        if target == base or candidate.endswith("/" + target):
            return 2
    for symbol in re.split(r"[,，、;；/]+", row.get("symbols", "")):
        cleaned = normalize_path(symbol)
        if cleaned and (cleaned == target or cleaned in target or target in cleaned):
            return 2
    for candidate in candidates:
        if target in candidate or candidate in target:
            return 1
    return 0


def _check_code_map(plan_text: str) -> list[Finding]:
    """Check 9 — plan.md carries a usable reverse index of owned files."""
    rows = parse_code_map_rows(plan_text)
    if rows is None:
        return [
            Finding(
                "ERROR",
                f"{PLAN_FILE} has no '## 代码地图' / '## Code Map' table — the "
                "work item cannot be found from a file path, so a follow-up "
                "fix has no way to learn which document it invalidates. Add "
                "one row per file: repo | repo-relative path | symbols | what "
                "changed",
            )
        ]
    if not rows:
        return [
            Finding(
                "ERROR",
                f"the Code Map section in {PLAN_FILE} has no data row — a "
                "path lookup finds nothing even though the section exists",
            )
        ]

    findings: list[Finding] = []
    for row in rows:
        label = f"{row['repository']}/{row['path']}"
        if WILDCARD_RE.search(row["path"]):
            findings.append(
                Finding(
                    "ERROR",
                    f"Code Map row '{label}' is a glob or range — one row per "
                    "file. A range cannot be matched by a path lookup, so it "
                    "silently drops traceability for every file it covers",
                )
            )
        if row["path"].startswith(("/", "~")):
            findings.append(
                Finding(
                    "ERROR",
                    f"Code Map row '{label}' is not repo-relative — paths must "
                    "start at the repo root, not at a machine location",
                )
            )
        if MULTI_PATH_RE.search(row["path"]):
            findings.append(
                Finding(
                    "ERROR",
                    f"Code Map row '{label}' lists more than one file — one "
                    "row per file, because a lookup matches rows, not cells",
                )
            )
        if row["path"].endswith("/") or PLACEHOLDER_PATH_RE.match(row["path"]):
            findings.append(
                Finding(
                    "ERROR",
                    f"Code Map row '{label}' names no file (a directory or a "
                    "placeholder) — a path lookup can never hit it, so every "
                    "file it stands for is untraceable to this item",
                )
            )
        if "/" not in row["path"] and not row["path"].startswith("."):
            findings.append(
                Finding(
                    "WARN",
                    f"Code Map row '{label}' has no directory — fine for a "
                    "file at the repo root, but a nested file written by name "
                    "alone makes `--find` guess, and it cannot be told apart "
                    "from another repo's same-named file",
                )
            )
    return findings


def _is_code_review_round(heading: str) -> bool:
    """Return whether a `## ` heading is a code-review round.

    Both the prefixed form and the legacy `## <repo> — Review Round N`
    shape count, because a follow-up round inherits whatever style the
    item already uses. Plan-review rounds do not: they review the plan and
    change no code.
    """
    if heading.startswith(CODE_REVIEW_HEADINGS):
        return True
    return bool(
        LEGACY_CODE_REVIEW_RE.match(heading)
    ) and not PLAN_REVIEW_HEADING_RE.match(heading)


def _attestation_line(body: str) -> str:
    """Return the Document Sync paragraph of a review round, or "" when absent.

    The round's own `### Document Sync` / `### 文档同步` sub-section is the
    place the format puts the attestation, so it is searched first; a line
    outside a table row counts when no such sub-section exists. A table row
    that merely quotes the bold label — which a round reviewing this very
    check will contain — is not an attestation.

    The label line and the lines wrapped under it are read as one paragraph:
    the shipped template soft-wraps its four clauses, so reading only the
    label line would reject a round that copied the template verbatim. Text
    outside that paragraph does not count — a round cannot satisfy the check
    by naming documents somewhere else in the section.
    """
    lines = body.splitlines()
    start = 0
    for index, line in enumerate(lines):
        if ATTESTATION_HEAD_RE.match(line.strip()):
            start = index
            break

    for index in range(start, len(lines)):
        line = lines[index]
        if line.strip().startswith("|") or not ATTESTATION_RE.search(line):
            continue
        paragraph = [line]
        for following in lines[index + 1 :]:
            if not following.strip():
                break
            paragraph.append(following)
        return " ".join(part.strip() for part in paragraph)
    return ""


def _documents_without_clause(paragraph: str) -> list[str]:
    """Return the document names that are named but never answered.

    The line exists to force a judgement per document, so a bare name is
    not an answer; the separator the templates use (—— / — / : / -) must be
    followed by text.
    """
    unanswered = []
    for doc, pattern in ATTESTED_DOC_RES.items():
        answered = False
        for match in pattern.finditer(paragraph):
            tail = match.group(1).strip().strip("`'\"”")
            if tail:
                answered = True
                break
        if not answered:
            unanswered.append(doc)
    return unanswered


def _check_document_sync(review_text: str) -> list[Finding]:
    """Check 10 — each code-review round attests what it did to the docs."""
    rounds = [
        (heading, body)
        for heading, body in split_sections(review_text)
        if _is_code_review_round(heading)
    ]
    if not rounds:
        return []

    lines = [_attestation_line(body) for _, body in rounds]
    marked = [index for index, line in enumerate(lines) if line]
    newest = len(rounds) - 1
    findings: list[Finding] = []

    # The newest round is the one being written right now, so it has no
    # legacy excuse — and it is the round a follow-up fix produces, which
    # is where the documents actually go stale.
    if not lines[newest]:
        findings.append(
            Finding(
                "ERROR",
                f"'{rounds[newest][0]}' is the newest code review round and "
                "carries no '**文档同步**' / '**Document Sync**' line — state "
                "for each of analysis.md, plan.md, progress.md, review.md "
                "what this round did to it, or why nothing changed (earlier "
                "rounds are not back-filled)",
            )
        )

    # Once the convention is in use inside the item, no later round opts out.
    if marked and marked[0] < newest:
        for index in range(marked[0] + 1, newest):
            if not lines[index]:
                findings.append(
                    Finding(
                        "ERROR",
                        f"'{rounds[index][0]}' changes code but carries no "
                        "'**文档同步**' / '**Document Sync**' line, while an "
                        "earlier round does — state the outcome for each of "
                        "the four documents",
                    )
                )

    for index in marked:
        missing = [doc for doc in DOC_FILES if doc not in lines[index]]
        if missing:
            findings.append(
                Finding(
                    "ERROR",
                    f"'{rounds[index][0]}' Document Sync line omits "
                    + ", ".join(missing)
                    + " — all four documents must be answered, each with one "
                    "clause; an omitted document is the one nobody checked",
                )
            )
        silent = _documents_without_clause(lines[index])
        if silent:
            findings.append(
                Finding(
                    "ERROR",
                    f"'{rounds[index][0]}' Document Sync line names "
                    + ", ".join(silent)
                    + " with no clause after it — the line exists to force the "
                    "judgement, not to be filled in; state what the round did "
                    "to each document or why nothing changed",
                )
            )
    return findings


def lint_work_dir(work_dir: Path) -> list[Finding]:
    """Lint one work directory. Returns findings (errors and warnings)."""
    findings: list[Finding] = []

    plan_text = read(work_dir / PLAN_FILE)
    review_text = read(work_dir / REVIEW_FILE)
    analysis_text = read(work_dir / ANALYSIS_FILE)

    if not plan_text:
        findings.append(Finding("ERROR", f"{PLAN_FILE} is missing or empty"))
    if not review_text:
        findings.append(Finding("ERROR", f"{REVIEW_FILE} is missing or empty"))
    if findings:
        return findings

    findings.extend(_check_evidence_coverage(plan_text, review_text))
    findings.extend(_check_plan_review_rounds(review_text))
    findings.extend(_check_task_ids(plan_text, review_text))
    findings.extend(_check_requirements_of_record(analysis_text, review_text))
    findings.extend(_check_placeholders(plan_text, analysis_text))
    findings.extend(_check_finding_discipline(review_text))
    findings.extend(_check_summary_section(plan_text))
    findings.extend(_check_code_map(plan_text))
    findings.extend(_check_document_sync(review_text))

    return findings


def _check_evidence_coverage(plan_text: str, review_text: str) -> list[Finding]:
    """Check 1 — every Success Criterion has exactly one Evidence row."""
    criteria = parse_sc_ids(plan_text)
    rows = parse_evidence_rows(review_text)

    if rows is None:
        return [
            Finding(
                "WARN",
                f"no Evidence table section found in {REVIEW_FILE}; "
                "Success Criteria cannot be tracked (legacy work item?)",
            )
        ]
    if not criteria and not rows:
        return []

    missing = sorted(criteria - rows, key=_natural_key)
    extra = sorted(rows - criteria, key=_natural_key)
    findings: list[Finding] = []
    if missing:
        findings.append(
            Finding(
                "ERROR",
                "Evidence table is missing a row for: "
                + ", ".join(missing)
                + f" ({len(criteria)} criteria in {PLAN_FILE}, "
                f"{len(rows)} rows)",
            )
        )
    if extra:
        findings.append(
            Finding(
                "ERROR",
                "Evidence table has rows for criteria not in "
                f"{PLAN_FILE}: " + ", ".join(extra),
            )
        )
    return findings


def _check_plan_review_rounds(review_text: str) -> list[Finding]:
    """Checks 2 and 3 — the review loop is closed and numbered."""
    rounds = parse_plan_review_rounds(review_text)
    if not rounds:
        return [
            Finding(
                "WARN",
                f"no plan review round found in {REVIEW_FILE}; the plan was "
                "never audited (legacy work item, or the gate was skipped)",
            )
        ]

    findings: list[Finding] = []
    expected = list(range(1, len(rounds) + 1))
    numbers = [r.number for r in rounds]
    if numbers != expected:
        findings.append(
            Finding(
                "ERROR",
                "plan review rounds must be numbered 1..N without gaps: "
                f"found {numbers}",
            )
        )

    last = rounds[-1]
    if last.verdict is None:
        findings.append(
            Finding(
                "ERROR",
                f"plan review round {last.number} has no verdict "
                "(expected PASS / PASS_WITH_RISKS / NEEDS_FIXES / "
                "NEEDS_USER_DECISION)",
            )
        )
    elif last.verdict not in CLOSING_VERDICTS:
        findings.append(
            Finding(
                "ERROR",
                f"plan review is not closed: last round {last.number} ended in "
                f"{last.verdict} — the revisions were never independently "
                "verified",
            )
        )
    return findings


def _check_task_ids(plan_text: str, review_text: str) -> list[Finding]:
    """Check 4 — review.md only cites tasks that exist in plan.md."""
    tasks = parse_task_ids(plan_text)
    cited = parse_task_ids(review_text)
    unknown = sorted(cited - tasks, key=_natural_key)
    if not unknown:
        return []
    return [
        Finding(
            "ERROR",
            f"{REVIEW_FILE} cites task ids that are not in {PLAN_FILE}: "
            + ", ".join(unknown),
        )
    ]


def _check_placeholders(plan_text: str, analysis_text: str) -> list[Finding]:
    """Check 5 — unresolved placeholders must become a real decision."""
    findings: list[Finding] = []
    for name, text in ((PLAN_FILE, plan_text), (ANALYSIS_FILE, analysis_text)):
        hits = find_placeholders(text)
        if hits:
            findings.append(
                Finding(
                    "WARN",
                    f"{name} has {len(hits)} unresolved placeholder(s) "
                    "(待确认 / 待定 / TBD) — convert them into a formal "
                    "NEEDS_USER_DECISION or resolve them: " + hits[0][:80],
                )
            )
    return findings


def _check_requirements_of_record(
    analysis_text: str, review_text: str
) -> list[Finding]:
    """Check 6 — the coverage matrix must be falsified against a baseline.

    A work item with neither the section nor a coverage matrix is simply
    older than this check, so it stays silent — a warning that fires on
    every legacy item trains the reader to ignore it. The moment a round
    asserts requirement coverage, though, it must say against what — and
    only a row in the coverage matrix counts as having said it.
    """
    body = find_section_body(analysis_text, REQUIREMENTS_HEADINGS)
    if body is None:
        if parse_req_ids(review_text):
            return [
                Finding(
                    "ERROR",
                    f"{REVIEW_FILE} cites REQ ids but {ANALYSIS_FILE} has no "
                    "'## 需求原文' / '## Original Requirements' section to "
                    "check them against",
                )
            ]
        if COVERAGE_HEADING_RE.search(review_text):
            return [
                Finding(
                    "WARN",
                    f"{REVIEW_FILE} asserts a requirements-coverage matrix "
                    f"but {ANALYSIS_FILE} has no '## 需求原文' / '## Original "
                    "Requirements' section — coverage is being judged "
                    "against the planner's own summary, and a narrowing of "
                    "a user-stated requirement cannot be told apart from a "
                    "documented limitation",
                )
            ]
        return []

    declared = parse_req_ids(body)
    if not declared:
        return [
            Finding(
                "ERROR",
                "the requirements-of-record section is empty — no REQ<n> id "
                f"declared in {ANALYSIS_FILE}",
            )
        ]

    # Coverage is asserted row by row, in the matrix — a REQ named in a
    # finding bullet is one that was discussed, not one whose coverage
    # was asserted.
    covered = parse_coverage_rows(review_text) or set()
    findings: list[Finding] = []
    unknown = sorted(covered - declared, key=_natural_key)
    if unknown:
        findings.append(
            Finding(
                "ERROR",
                f"{REVIEW_FILE} coverage-matrix rows cite requirement ids "
                f"that are not declared in {ANALYSIS_FILE}: "
                + ", ".join(unknown),
            )
        )
    uncited = sorted(declared - covered, key=_natural_key)
    if uncited:
        findings.append(
            Finding(
                "ERROR",
                "declared requirements never appear in any review round's "
                "coverage matrix, so nobody asserted their coverage: "
                + ", ".join(uncited),
            )
        )
    return findings


def _check_finding_discipline(review_text: str) -> list[Finding]:
    """Check 7 — P2 inflation and oscillation, both capped in prose only."""
    findings: list[Finding] = []
    blocking_previous: int | None = None
    for plan_round in parse_plan_review_rounds(review_text):
        counts = count_severities(plan_round.body)
        if counts["2"] > MAX_P2_PER_ROUND:
            findings.append(
                Finding(
                    "WARN",
                    f"round {plan_round.number} lists {counts['2']} P2 findings "
                    f"(the reviewer's brief caps P2 at {MAX_P2_PER_ROUND}; "
                    "P2 must never block)",
                )
            )
        blocking = counts["0"] + counts["1"]
        if blocking_previous is not None and blocking > blocking_previous:
            findings.append(
                Finding(
                    "WARN",
                    f"round {plan_round.number} carries {blocking} P0/P1 "
                    f"findings against {blocking_previous} in the previous "
                    "round — the loop may be oscillating; stop and hand the "
                    "residual disagreement to the user",
                )
            )
        if blocking or counts["2"]:
            blocking_previous = blocking
    return findings


def _check_summary_section(plan_text: str) -> list[Finding]:
    """Check 8 — plan.md carries the decision-reader summary section."""
    if find_section_body(plan_text, SUMMARY_HEADINGS) is None:
        return [
            Finding(
                "WARN",
                f"{PLAN_FILE} has no '## 摘要' / '## Summary' section — a "
                "reader has no 30-second entry point into the work item "
                "(legacy work item?)",
            )
        ]
    return []


def discover_docs_dir(start: Path) -> Path | None:
    """Walk up from `start` to locate the workspace's shared docs directory.

    Prefers `fullstack.json`'s `docs_dir` (the workspace's own record), and
    falls back to any child directory that holds `changes/<type>/`. So a
    lookup run from the workspace root or from inside a repo resolves
    without the caller having to pass a path.
    """
    resolved = start.resolve()
    for root in [resolved, *resolved.parents][:MAX_DOCS_DIR_WALK_UP]:
        if not root.is_dir():
            continue
        config_path = root / CONFIG_FILENAME
        if config_path.is_file():
            try:
                saved = json.loads(config_path.read_text(encoding="utf-8")).get(
                    "docs_dir"
                )
            except (json.JSONDecodeError, OSError):
                saved = None
            if saved and (root / saved / "changes").is_dir():
                return root / saved
        for child in sorted(root.iterdir()):
            if child.name.startswith("."):
                continue
            changes = child / "changes"
            if changes.is_dir() and any(
                (changes / work_type).is_dir() for work_type in WORK_ITEM_TYPES
            ):
                return child
    return None


def find_doc_mentions(
    work_dir: Path,
    needle: str,
    label: str = "",
    max_mentions: int = MAX_MENTIONS_PER_ITEM,
) -> list[str]:
    """Return prose lines in a work item that mention `needle`.

    Candidates, not ownership: a path named in an `analysis.md` option
    table does not mean that file belongs to the item. `label` is the
    item's path under `changes/`, so an archived item is visible as one
    and the "never reopen an archived item" rule can be applied here too.
    """
    lines: list[str] = []
    lowered = needle.lower()
    shown = label or work_dir.name
    for doc in sorted(work_dir.glob("*.md")):
        for number, line in enumerate(read(doc).splitlines(), start=1):
            if lowered not in line.lower():
                continue
            lines.append(
                f"MENTION: {shown} | {doc.name}:{number} | {line.strip()[:120]}"
            )
            if len(lines) >= max_mentions:
                return lines
    return lines


def find_in_docs_dir(
    docs_dir: Path, needle: str
) -> tuple[list[str], list[str]]:
    """Look up `needle` across every work item under the docs dir.

    Returns (Code Map ownership hits, bare-name/substring hits, prose
    mentions) — only the first bucket is ownership. Archived items are
    scanned too: a bug reported against shipped code is often owned by
    work that has already been archived, and that is exactly the case
    where the reader needs to be told not to reopen it.
    """
    changes_dir = docs_dir / "changes"
    codemap_hits: list[tuple[int, str]] = []
    weak_hits: list[str] = []
    mentions: list[str] = []

    for plan_path in sorted(changes_dir.rglob(PLAN_FILE)):
        work_dir = plan_path.parent
        if any(part.startswith(".") for part in plan_path.relative_to(changes_dir).parts):
            continue
        label = f"{work_dir.relative_to(docs_dir)}"
        rows = parse_code_map_rows(read(plan_path)) or []
        best = 0
        best_rows: list[dict[str, str]] = []
        for row in rows:
            score = match_code_map_row(needle, row)
            if score > best:
                best, best_rows = score, [row]
            elif score == best and score:
                best_rows.append(row)
        if best >= 2:
            for row in best_rows:
                codemap_hits.append(
                    (
                        best,
                        f"CODEMAP: {label} | {row['repository']} | {row['path']} | "
                        f"{row['symbols'] or '—'} | {row['change'] or '—'}",
                    )
                )
        elif best == 1:
            # A bare-name or substring row is a hint, not ownership: two
            # repos can both carry `dark_mode.py`, and the lookup cannot
            # tell which one the needle meant.
            for row in best_rows:
                weak_hits.append(
                    f"SUBSTRING: {label} | {row['repository']} | "
                    f"{row['path']} | {row['symbols'] or '—'} | "
                    f"{row['change'] or '—'}"
                )
        else:
            mentions.extend(find_doc_mentions(work_dir, needle, label))

    codemap_hits.sort(key=lambda item: (-item[0], item[1]))
    return [line for _, line in codemap_hits], weak_hits, mentions


def format_find_result(
    docs_dir: Path,
    needle: str,
    codemap_hits: list[str],
    weak_hits: list[str],
    mentions: list[str],
) -> str:
    """Render the reverse lookup in the script's machine-readable style.

    STATUS answers ownership directly rather than "did anything match":
    OWNER means a Code Map row claims the needle, CANDIDATE means only
    weak rows or prose pointed here, and NONE means no work item knows
    about it. An agent that reads exit 0 as "owner found" would treat a
    mention as a specification, which is the mistake this lookup exists to
    prevent.
    """
    candidates = len(weak_hits) + len(mentions)
    if codemap_hits:
        status = "OWNER"
    elif candidates:
        status = "CANDIDATE"
    else:
        status = "NONE"
    lines = [
        f"STATUS={status}",
        f"HITS={len(codemap_hits) + candidates}",
        f"NEEDLE={needle}",
        f"DOCS_DIR={docs_dir}",
    ]
    lines.extend(codemap_hits)
    lines.extend(weak_hits)
    lines.extend(mentions)
    if not codemap_hits and (weak_hits or mentions):
        lines.append(
            "NOTE: no Code Map owns this — SUBSTRING rows matched on a bare "
            "name and MENTION lines are prose. Confirm ownership before "
            "treating a candidate as the spec"
        )
    if status == "NONE":
        lines.append(
            "NOTE: no work item owns this path or symbol. Ask the user "
            "whether the change belongs to an existing item or needs a new "
            "one; never edit code silently on the grounds that no doc applies"
        )
    return "\n".join(lines)


def _natural_key(value: str) -> tuple[str, int]:
    """Sort SC2 before SC10."""
    match = re.match(r"([A-Z]+)(\d+)([a-z]?)", value)
    if not match:
        return (value, 0)
    return (match.group(1) + match.group(3), int(match.group(2)))


def format_findings(findings: list[Finding]) -> str:
    """Render findings in the machine-readable output format."""
    errors = [f for f in findings if f.level == "ERROR"]
    warnings = [f for f in findings if f.level == "WARN"]
    lines = [
        f"STATUS={'FAIL' if errors else 'PASS'}",
        f"CHECKS={len(findings)}  WARNINGS={len(warnings)}",
    ]
    lines.extend(f"ERROR: {f.message}" for f in errors)
    lines.extend(f"WARN: {f.message}" for f in warnings)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        description="Lint the work-tracking documents for consistency, or "
        "look up which work item owns a code path.",
    )
    parser.add_argument(
        "work_dir",
        nargs="?",
        help="Work directory holding the four docs (lint mode)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the STATUS line and the errors",
    )
    parser.add_argument(
        "--find",
        metavar="NEEDLE",
        help="Reverse lookup mode: which work item owns this path, file, or "
        "symbol",
    )
    parser.add_argument(
        "--docs-dir",
        metavar="DIR",
        help="Shared docs directory for --find (default: discover from "
        f"{CONFIG_FILENAME} upward from the current directory)",
    )
    args = parser.parse_args(argv)

    if args.find:
        docs_arg = args.docs_dir or args.work_dir
        if args.docs_dir and args.work_dir:
            parser.error("--find takes one docs directory, not two")
        if docs_arg:
            docs_dir: Path | None = Path(docs_arg)
            if not docs_dir.is_dir():
                print(f"ERROR: not a directory: {docs_dir}", file=sys.stderr)
                return 2
        else:
            docs_dir = discover_docs_dir(Path.cwd())
            if docs_dir is None:
                print(
                    "ERROR: could not locate the shared docs directory — pass "
                    "--docs-dir <dir>",
                    file=sys.stderr,
                )
                return 2
        changes_dir = docs_dir / "changes"
        if not changes_dir.is_dir():
            print(
                f"ERROR: no changes/ under {docs_dir} — is this the workspace's "
                "shared docs directory?",
                file=sys.stderr,
            )
            return 2
        hits, weak, mentions = find_in_docs_dir(docs_dir, args.find)
        print(format_find_result(docs_dir, args.find, hits, weak, mentions))
        # 0 only when a Code Map row claims the needle. Candidates and
        # misses both exit 1, so "the lookup succeeded" can never be read
        # as "the owner is known".
        return 0 if hits else 1

    if args.docs_dir:
        parser.error("--docs-dir is only meaningful with --find")
    if not args.work_dir:
        parser.error("work_dir is required unless --find is used")

    work_dir = Path(args.work_dir)
    if not work_dir.is_dir():
        print(f"ERROR: not a directory: {work_dir}", file=sys.stderr)
        return 2

    findings = lint_work_dir(work_dir)
    if args.quiet:
        errors = [f for f in findings if f.level == "ERROR"]
        print(f"STATUS={'FAIL' if errors else 'PASS'}")
        for finding in errors:
            print(f"ERROR: {finding.message}")
    else:
        print(format_findings(findings))

    return 1 if any(f.level == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
