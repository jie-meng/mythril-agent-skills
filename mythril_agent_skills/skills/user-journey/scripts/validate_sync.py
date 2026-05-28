#!/usr/bin/env python3
"""Validate that JOURNEY.md and journey.json agree.

Checks structural drift between the human-readable source (JOURNEY.md) and
the machine-readable source (journey.json) for a user-journey workspace.
Exit codes:
    0 — in sync, OK to continue
    1 — drift detected, must fix before declaring an edit done
    2 — workspace structure invalid (missing files)

Usage:
    python3 validate_sync.py <workspace>
    python3 validate_sync.py <workspace> --json   # machine-readable output

Pure stdlib (Python 3.10+).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def normalize_id(value: str) -> str:
    """Normalize a stage / persona id to its canonical form."""
    return (value or "").strip().lower()


def extract_mermaid_node_ids(markdown: str) -> list[str]:
    """Extract node IDs from the first mermaid flowchart block in the markdown.

    Handles chained edges (`a --> b --> c`) by splitting on edge tokens
    first, then extracting the bare identifier from each fragment.
    """
    block = re.search(
        r"```mermaid\s*\n([\s\S]*?)\n```",
        markdown,
        flags=re.MULTILINE,
    )
    if not block:
        return []
    body = block.group(1)
    ids: list[str] = []
    edge_split_re = re.compile(r"\s*(?:-{1,3}>|={1,3}>|---|===)\s*")
    ident_re = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)")
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("%%", "flowchart", "graph", "subgraph", "end", "classDef", "class ")):
            continue
        for fragment in edge_split_re.split(stripped):
            fragment = fragment.strip()
            if not fragment:
                continue
            m = ident_re.match(fragment)
            if m:
                token = normalize_id(m.group(1))
                if token and token not in ids:
                    ids.append(token)
    return ids


def extract_stage_subsection_ids(markdown: str) -> list[str]:
    """Extract stage IDs derived from `### N. <Label>` headings under `## Stages`.

    We do not parse the labels themselves; we slugify them and compare to the
    JSON `stage.id`. The match is informational only — drift here is a warning,
    not a hard error, because users may rename labels freely.
    """
    in_stages = False
    headings: list[str] = []
    for line in markdown.splitlines():
        if re.match(r"^##\s+Stages", line, flags=re.IGNORECASE):
            in_stages = True
            continue
        if in_stages and line.startswith("## "):
            break
        if in_stages:
            m = re.match(r"^###\s+\d+\.\s*(.+?)\s*$", line)
            if m:
                headings.append(_slugify(m.group(1)))
    return headings


def _slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"[^a-z0-9\-]+", "", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text


VALID_SCHEMA_VERSIONS = {"1", "2", "3"}


def validate_journey_structure(journey: dict) -> list[str]:
    """Run JSON-only structural validation. Returns a list of error strings.

    Accepts schema_version "1" (legacy, read-only), "2" (deprecated v2 nested
    transitions), and "3" (current — canvas + top-level arrows).
    """
    errors: list[str] = []
    if str(journey.get("schema_version") or "") not in VALID_SCHEMA_VERSIONS:
        errors.append(
            f"schema_version must be one of {sorted(VALID_SCHEMA_VERSIONS)}, "
            f"got {journey.get('schema_version')!r}"
        )
    if not journey.get("title"):
        errors.append("title is required")
    if journey.get("language") not in ("en", "zh"):
        errors.append(
            f"language must be 'en' or 'zh', got {journey.get('language')!r}"
        )
    personas = journey.get("personas") or []
    if not personas:
        errors.append("at least one persona is required")
    persona_ids: set[str] = set()
    for idx, p in enumerate(personas):
        if not p.get("id"):
            errors.append(f"personas[{idx}].id is required")
            continue
        if p["id"] in persona_ids:
            errors.append(f"duplicate persona id: {p['id']}")
        persona_ids.add(p["id"])
        if not p.get("name"):
            errors.append(f"personas[{idx}].name is required")
    stages = journey.get("stages") or []
    if not stages:
        errors.append("at least one stage is required")
    if len(stages) > 7:
        errors.append(
            f"too many stages ({len(stages)}). Consider splitting into two journeys."
        )
    stage_ids: set[str] = set()
    valid_emotions = {"delighted", "happy", "neutral", "frustrated", "blocked"}
    for idx, s in enumerate(stages):
        if not s.get("id"):
            errors.append(f"stages[{idx}].id is required")
            continue
        if s["id"] in stage_ids:
            errors.append(f"duplicate stage id: {s['id']}")
        stage_ids.add(s["id"])
        if not s.get("label"):
            errors.append(f"stages[{idx}].label is required")
        pid = s.get("persona_id")
        if pid and pid not in persona_ids:
            errors.append(
                f"stages[{idx}].persona_id={pid!r} not in defined personas"
            )
        steps = s.get("steps") or []
        step_ids: set[str] = set()
        for sidx, step in enumerate(steps):
            if not step.get("id"):
                errors.append(f"stages[{idx}].steps[{sidx}].id is required")
                continue
            if step["id"] in step_ids:
                errors.append(
                    f"stages[{idx}] has duplicate step id: {step['id']}"
                )
            step_ids.add(step["id"])
            emo = step.get("emotion")
            if emo and emo not in valid_emotions:
                errors.append(
                    f"stages[{idx}].steps[{sidx}].emotion={emo!r} not in {sorted(valid_emotions)}"
                )
    return errors


def compare_sync(journey: dict, markdown: str) -> dict:
    """Compare JSON stages to markdown mermaid + subsections.

    Returns a structured report with `errors`, `warnings`, and `info` lists.
    """
    json_stage_ids = [s.get("id") or "" for s in (journey.get("stages") or [])]
    mermaid_ids = extract_mermaid_node_ids(markdown)
    md_subsection_ids = extract_stage_subsection_ids(markdown)

    json_set = {normalize_id(x) for x in json_stage_ids if x}
    mermaid_set = {normalize_id(x) for x in mermaid_ids}

    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    if not mermaid_ids:
        warnings.append("no mermaid flowchart found in JOURNEY.md")
    else:
        missing_in_md = json_set - mermaid_set
        extra_in_md = mermaid_set - json_set
        if missing_in_md:
            errors.append(
                f"mermaid flowchart is missing stages defined in journey.json: "
                f"{sorted(missing_in_md)}"
            )
        if extra_in_md:
            errors.append(
                f"mermaid flowchart has stages not in journey.json: "
                f"{sorted(extra_in_md)}"
            )

    json_normalized = [normalize_id(x) for x in json_stage_ids]
    if md_subsection_ids and len(md_subsection_ids) == len(json_normalized):
        if md_subsection_ids != json_normalized:
            warnings.append(
                "stage subsection order in JOURNEY.md does not match "
                "journey.json stage order — labels or order differ"
            )
    elif md_subsection_ids and len(md_subsection_ids) < len(json_normalized):
        info.append(
            f"JOURNEY.md has only {len(md_subsection_ids)} stage subsection(s) "
            f"but journey.json defines {len(json_normalized)} stage(s) — "
            "fill in the remaining subsections as you author the journey"
        )
    elif md_subsection_ids and len(md_subsection_ids) > len(json_normalized):
        warnings.append(
            f"JOURNEY.md has {len(md_subsection_ids)} stage subsections "
            f"but journey.json only defines {len(json_normalized)} stage(s)"
        )

    title = journey.get("title", "")
    md_h1 = next(
        (line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")),
        "",
    )
    if title and md_h1 and md_h1 != title:
        info.append(
            f"H1 in JOURNEY.md is {md_h1!r} but JSON title is {title!r} — auto-fixable"
        )

    return {"errors": errors, "warnings": warnings, "info": info}


# ---------------------------------------------------------------------------
# Filesystem orchestration
# ---------------------------------------------------------------------------

def validate_workspace(workspace: Path) -> dict:
    """Top-level: load both files and produce a full report."""
    journey_path = workspace / "journey.json"
    md_path = workspace / "JOURNEY.md"
    report = {
        "workspace": str(workspace),
        "errors": [],
        "warnings": [],
        "info": [],
        "structure_ok": True,
    }
    if not journey_path.exists():
        report["errors"].append(f"missing {journey_path.name}")
        report["structure_ok"] = False
    if not md_path.exists():
        report["errors"].append(f"missing {md_path.name}")
        report["structure_ok"] = False
    if not report["structure_ok"]:
        return report

    try:
        journey = json.loads(journey_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report["errors"].append(f"journey.json is not valid JSON: {exc}")
        report["structure_ok"] = False
        return report

    markdown = md_path.read_text(encoding="utf-8")

    struct_errors = validate_journey_structure(journey)
    report["errors"].extend(struct_errors)

    sync_report = compare_sync(journey, markdown)
    report["errors"].extend(sync_report["errors"])
    report["warnings"].extend(sync_report["warnings"])
    report["info"].extend(sync_report["info"])

    return report


def print_report(report: dict) -> None:
    """Pretty-print a report to stdout."""
    print(f"Workspace: {report['workspace']}")
    if not report["structure_ok"]:
        for err in report["errors"]:
            print(f"{RED}!! {err}{NC}")
        print(f"\n{RED}FAIL: invalid workspace structure.{NC}")
        return
    if report["errors"]:
        for err in report["errors"]:
            print(f"{RED}!! ERROR  {err}{NC}")
    if report["warnings"]:
        for w in report["warnings"]:
            print(f"{YELLOW}** WARN   {w}{NC}")
    if report["info"]:
        for m in report["info"]:
            print(f"   INFO   {m}")
    if not report["errors"] and not report["warnings"]:
        print(f"{GREEN}OK: JOURNEY.md and journey.json are in sync.{NC}")
    elif not report["errors"]:
        print(f"\n{GREEN}OK with warnings.{NC}")
    else:
        print(f"\n{RED}FAIL: drift detected. Fix the errors above before continuing.{NC}")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "workspace",
        help="path to the user-journey workspace",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a machine-readable JSON report instead of pretty output",
    )
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()
    report = validate_workspace(workspace)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)

    if not report["structure_ok"]:
        return 2
    if report["errors"]:
        return 1
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
