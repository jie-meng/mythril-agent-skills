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

Checks 5 and 7 are warnings because neither breaks the chain. Checks 1-4
and 6 are errors: each one lets an unverifiable claim enter the
definition of done. Item 6 stays silent for work items that have neither
the section nor a coverage matrix, so legacy items do not generate noise.

Usage:
    python3 plan_lint.py <work-dir>
    python3 plan_lint.py --quiet <work-dir>

Output (one field per line, machine-readable):
    STATUS=PASS|FAIL
    CHECKS=<n>  WARNINGS=<n>
    ERROR: <message>
    WARN: <message>

Exit code is 0 when STATUS=PASS, 1 otherwise. Findings are emitted in
check order; the STATUS line always comes first.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

PLAN_FILE = "plan.md"
ANALYSIS_FILE = "analysis.md"
REVIEW_FILE = "review.md"

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
        description="Lint the work-tracking documents for consistency.",
    )
    parser.add_argument("work_dir", help="Work directory holding the four docs")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the STATUS line and the errors",
    )
    args = parser.parse_args(argv)

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
