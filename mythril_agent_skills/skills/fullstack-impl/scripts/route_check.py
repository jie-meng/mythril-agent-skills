#!/usr/bin/env python3
"""Routing helper for fullstack-impl: pick the right Mode deterministically.

Picking the wrong Mode (Fresh / Reference / Iteration / Followup / Resume)
is the #1 failure of the fullstack-impl skill. The routing rules live in
`references/mode-selection.md`, but reading scattered Markdown rules and
applying them under uncertainty has proven unreliable across LLMs.

This script encodes the deterministic parts of routing as code:

  1. Locate the named work directory under <docs-dir>/{feat,refactor,fix}/.
  2. Parse plan.md's Status field and normalize it to a fixed enum.
  3. Detect whether progress.md has a `## Successors` table (and which
     successor is the latest).
  4. Detect whether the user prompt contains explicit reading verbs,
     follow-up verbs, iteration / fix verbs, or resume verbs.
  5. Combine 1-4 into a recommended ROUTE, defaulting to AskUser when
     ambiguous (the cost of asking once is far below the cost of a wrong
     route).

What it does NOT decide:
  - Whether the new work item is in-scope of the matched directory
    (semantic judgment — left to the agent).
  - Branch source / branch name / -vN suffix details (left to the
    Mode-specific reference docs).
  - Anything that requires reading source code or git history.

Usage:
    python3 route_check.py \\
        --workspace-root <path> \\
        [--work-dir-name <name>] \\
        [--prompt <user-prompt-text>] \\
        [--prompt-file <path>]

Exit codes:
    0 — analysis succeeded; check ROUTE for the recommendation
    1 — invalid arguments
    2 — workspace not valid (delegate to check_workspace.py)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from check_workspace import check_workspace

WORK_TYPES = ("feat", "refactor", "fix")

STATUS_PATTERN_EN = re.compile(
    r"^\s*\*\*Status\*\*\s*[:：]\s*(.+?)\s*$",
    re.MULTILINE,
)
STATUS_PATTERN_ZH = re.compile(
    r"^\s*\*\*状态\*\*\s*[:：]\s*(.+?)\s*$",
    re.MULTILINE,
)

SUCCESSORS_HEADERS = ("## Successors", "## 后续工作")
SUCCESSOR_LINK_PATTERN = re.compile(r"\[`?([^`\]]+)`?\]\(([^)]+)\)")
ITERATION_LOG_HEADERS = ("## Iteration Log", "## 迭代记录")

PLANNING_TOKENS = (
    "planning",
    "in progress",
    "in-progress",
    "ongoing",
    "wip",
    "规划中",
    "进行中",
    "实施中",
)

DONE_TOKENS = (
    "done",
    "complete",
    "completed",
    "finished",
    "已完成",
    "完成",
    "已实现",
    "已实施",
    "已实现并测试通过",
)

CLOSED_TOKENS = (
    "closed",
    "merged",
    "shipped",
    "released",
    "已关闭",
    "已合并",
    "已发布",
    "已上线",
)


READ_VERBS = (
    "look at",
    "read",
    "reference",
    "based on the",
    "use for context",
    "see what we did",
    "check the",
    "as background",
    "as context",
    "参考",
    "看一下",
    "看看",
    "看下",
    "当背景",
    "当参考",
    "回顾",
)

FOLLOWUP_VERBS = (
    "follow up on",
    "follow-up on",
    "extend",
    "build on top of",
    "on top of",
    "based on x work",
    "继续做",
    "在 x 基础上",
    "基于 x 做后续",
    "x 的后续",
    "扩展",
    "follow up x",
)

ITERATION_VERBS = (
    "this is wrong",
    "doesn't work",
    "fix this",
    "tweak",
    "adjust",
    "change this",
    "also add",
    "got this error",
    "report",
    "broken",
    "update this",
    "调一下",
    "再改一下",
    "这里不对",
    "改一下",
    "改成",
    "改下",
    "修一下",
    "修复一下",
    "顺便加一下",
    "log 报错",
    "报错",
    "我想改",
    "想改",
    "调整一下",
    "调整下",
    "再加",
    "再加个",
    "我想",
)

RESUME_VERBS = (
    "continue",
    "resume",
    "carry on",
    "继续",
    "接着做",
    "接着干",
)


@dataclass
class WorkDirInfo:
    """Parsed metadata for a single work directory."""

    name: str
    path: Path
    work_type: str
    status_raw: str
    status_normalized: str
    has_successors: bool
    latest_successor: str | None
    iteration_log_found: bool


@dataclass
class TriggerInfo:
    """Trigger verbs detected in the user prompt."""

    has_read: bool = False
    has_followup: bool = False
    has_iteration: bool = False
    has_resume: bool = False

    @property
    def labels(self) -> list[str]:
        out = []
        if self.has_read:
            out.append("read")
        if self.has_followup:
            out.append("followup")
        if self.has_iteration:
            out.append("iteration")
        if self.has_resume:
            out.append("resume")
        return out


@dataclass
class RouteResult:
    """Final routing decision plus reasoning."""

    route: str
    work_dir_info: WorkDirInfo | None = None
    triggers: TriggerInfo = field(default_factory=TriggerInfo)
    recommended_next_doc: str = ""
    reasoning: list[str] = field(default_factory=list)


def normalize_status(raw: str) -> str:
    """Map a free-form Status field to one of: Planning|InProgress|Done|Closed|Unknown.

    The match is case-insensitive substring on the lowercased raw value.
    'Done v3 — final approach' counts as Done. Free text with no enum
    keyword counts as Unknown.
    """
    if not raw:
        return "Unknown"
    lower = raw.lower().strip()
    for token in CLOSED_TOKENS:
        if token in lower:
            return "Closed"
    for token in DONE_TOKENS:
        if token in lower:
            return "Done"
    for token in PLANNING_TOKENS:
        if "in progress" in lower or "in-progress" in lower or "进行中" in lower:
            return "InProgress"
        if token in lower:
            if "progress" in token or "进行中" in token:
                return "InProgress"
            return "Planning"
    return "Unknown"


def parse_status(plan_text: str) -> str:
    """Extract the Status / 状态 line from a plan.md, preferring the first match."""
    match = STATUS_PATTERN_EN.search(plan_text)
    if not match:
        match = STATUS_PATTERN_ZH.search(plan_text)
    if not match:
        return ""
    return match.group(1).strip()


def find_latest_successor(progress_text: str) -> tuple[bool, str | None]:
    """Detect the Successors table and return the bottom-most successor link."""
    lines = progress_text.splitlines()
    in_section = False
    table_started = False
    last_link: str | None = None
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(h) for h in SUCCESSORS_HEADERS):
            in_section = True
            table_started = False
            continue
        if in_section and stripped.startswith("## "):
            break
        if not in_section or not stripped.startswith("|"):
            continue
        if not table_started:
            table_started = True
            continue
        if set(stripped.replace(" ", "")) <= set("-:|"):
            continue
        m = SUCCESSOR_LINK_PATTERN.search(stripped)
        if m:
            last_link = m.group(2)
    return (in_section and last_link is not None, last_link)


def has_iteration_log(progress_text: str) -> bool:
    """Return True if progress.md contains an Iteration Log section header."""
    for line in progress_text.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(h) for h in ITERATION_LOG_HEADERS):
            return True
    return False


def find_work_dir(
    docs_root: Path, name: str
) -> tuple[Path | None, str | None]:
    """Locate <docs-root>/<type>/<name>/ across the three work types."""
    if not name:
        return None, None
    for work_type in WORK_TYPES:
        candidate = docs_root / work_type / name
        if candidate.is_dir():
            return candidate, work_type
    return None, None


def load_work_dir_info(path: Path, work_type: str) -> WorkDirInfo:
    """Load all metadata we care about from a work directory."""
    plan_text = ""
    progress_text = ""
    plan_path = path / "plan.md"
    progress_path = path / "progress.md"
    if plan_path.is_file():
        plan_text = plan_path.read_text(encoding="utf-8")
    if progress_path.is_file():
        progress_text = progress_path.read_text(encoding="utf-8")

    raw = parse_status(plan_text)
    normalized = normalize_status(raw)
    has_succ, latest = find_latest_successor(progress_text)
    iter_log = has_iteration_log(progress_text)

    return WorkDirInfo(
        name=path.name,
        path=path,
        work_type=work_type,
        status_raw=raw,
        status_normalized=normalized,
        has_successors=has_succ,
        latest_successor=latest,
        iteration_log_found=iter_log,
    )


def _verb_in_prompt(prompt: str, verbs: tuple[str, ...]) -> bool:
    """True if any verb (case-insensitive substring) appears in prompt."""
    if not prompt:
        return False
    lower = prompt.lower()
    return any(v in lower for v in verbs)


def detect_triggers(prompt: str) -> TriggerInfo:
    """Scan prompt for the four classes of routing verbs."""
    return TriggerInfo(
        has_read=_verb_in_prompt(prompt, READ_VERBS),
        has_followup=_verb_in_prompt(prompt, FOLLOWUP_VERBS),
        has_iteration=_verb_in_prompt(prompt, ITERATION_VERBS),
        has_resume=_verb_in_prompt(prompt, RESUME_VERBS),
    )


def decide_route(
    work: WorkDirInfo | None, triggers: TriggerInfo
) -> RouteResult:
    """Combine work-dir metadata + prompt triggers into a routing decision."""
    result = RouteResult(route="Fresh", work_dir_info=work, triggers=triggers)

    if work is None:
        if triggers.has_read or triggers.has_followup or triggers.has_iteration:
            result.route = "AskUser"
            result.recommended_next_doc = "mode-selection.md"
            result.reasoning.append(
                "User prompt has a routing verb but no matching work directory "
                "was found — confirm with user which work item to read or extend."
            )
            return result
        result.recommended_next_doc = "(none — proceed with standard Step 1-9)"
        result.reasoning.append(
            "No matching work directory; default to Fresh standard flow."
        )
        return result

    if work.has_successors and work.latest_successor:
        result.reasoning.append(
            f"Work item has a Successors back-link; latest successor: "
            f"{work.latest_successor}. Resolve routing against the latest "
            "successor first, NOT the original."
        )

    status = work.status_normalized
    result.reasoning.append(
        f"Matched work directory: {work.name} (type={work.work_type}, "
        f"status_raw='{work.status_raw}', status_normalized={status})"
    )

    has_iter_signal = (
        triggers.has_iteration
        or triggers.has_resume
        or triggers.has_followup
    )

    if status == "Unknown":
        result.route = "AskUser"
        result.recommended_next_doc = "mode-selection.md"
        result.reasoning.append(
            "Status is Unknown (free-form text not in enum). Ask the user "
            "to confirm the work item's lifecycle stage before routing."
        )
        return result

    if triggers.has_iteration and triggers.has_followup:
        result.route = "AskUser"
        result.recommended_next_doc = "mode-selection.md"
        result.reasoning.append(
            "Prompt contains BOTH iteration verbs and follow-up verbs; ask "
            "the user to clarify Iteration vs Follow-up."
        )
        return result

    if status == "Closed":
        if triggers.has_followup:
            result.route = "Followup"
            result.recommended_next_doc = "followup-mode.md"
            result.reasoning.append(
                "Closed work item + explicit follow-up verb → Follow-up Mode."
            )
            return result
        if triggers.has_iteration:
            result.route = "AskUser"
            result.recommended_next_doc = "mode-selection.md"
            result.reasoning.append(
                "Closed work item + iteration/fix verb is ambiguous (the work "
                "may already be shipped). Ask the user: Iteration "
                "(reopen / hotfix branch?) vs Follow-up (-vN successor) vs "
                "Independent fresh fix."
            )
            return result
        if triggers.has_read and not has_iter_signal:
            result.route = "Reference"
            result.recommended_next_doc = "reference-mode.md"
            result.reasoning.append(
                "Closed work item + reading verb, no modify intent → "
                "Reference Mode."
            )
            return result
        result.route = "AskUser"
        result.recommended_next_doc = "mode-selection.md"
        result.reasoning.append(
            "Closed work item but no explicit verb; ask the 3-option "
            "question (Follow-up / Reference / Independent)."
        )
        return result

    if status == "Done":
        if triggers.has_followup:
            result.route = "AskUser"
            result.recommended_next_doc = "mode-selection.md"
            result.reasoning.append(
                "Status=Done + follow-up verb is unusual (Follow-up is for "
                "Closed work). Ask the user whether to close the current "
                "round first then start a -vN successor, or treat this as "
                "an iteration."
            )
            return result
        if triggers.has_iteration or triggers.has_resume:
            result.route = "Iteration"
            result.recommended_next_doc = "iteration-mode.md"
            note = (
                "Done work item + iteration / fix / resume verb → Iteration Mode."
            )
            if triggers.has_read:
                note += (
                    " Prompt also has reading verb; treat reading as "
                    "background context, then run the iteration loop."
                )
            result.reasoning.append(note)
            return result
        if triggers.has_read:
            result.route = "Reference"
            result.recommended_next_doc = "reference-mode.md"
            result.reasoning.append(
                "Done work item + reading verb only → Reference Mode "
                "(read-only). If user later asks to modify, promote to "
                "Iteration Mode."
            )
            return result
        result.route = "AskUser"
        result.recommended_next_doc = "mode-selection.md"
        result.reasoning.append(
            "Done work item but no explicit verb; confirm with user."
        )
        return result

    if status in ("Planning", "InProgress"):
        if triggers.has_resume or triggers.has_iteration:
            result.route = "Resume"
            result.recommended_next_doc = "(SKILL.md Resuming Previous Work)"
            result.reasoning.append(
                f"Open work item ({status}) + continue / fix verb → "
                "Resume the original Step 1-9 from the last incomplete step."
            )
            return result
        if triggers.has_read:
            result.route = "Reference"
            result.recommended_next_doc = "reference-mode.md"
            result.reasoning.append(
                f"Open work item ({status}) + reading verb only → "
                "Reference Mode (in-progress citation)."
            )
            return result
        result.route = "AskUser"
        result.recommended_next_doc = "mode-selection.md"
        result.reasoning.append(
            f"Open work item ({status}) but no explicit verb; confirm intent."
        )
        return result

    result.route = "AskUser"
    result.recommended_next_doc = "mode-selection.md"
    result.reasoning.append(
        "Unhandled combination; default to AskUser to stay safe."
    )
    return result


def format_result(result: RouteResult) -> str:
    """Render the RouteResult as machine + human readable text."""
    lines: list[str] = [f"ROUTE={result.route}"]
    if result.work_dir_info is not None:
        info = result.work_dir_info
        lines.append(f"WORK_DIR={info.path}")
        lines.append(f"WORK_DIR_NAME={info.name}")
        lines.append(f"WORK_TYPE={info.work_type}")
        lines.append(f"STATUS_NORMALIZED={info.status_normalized}")
        lines.append(f"STATUS_RAW={info.status_raw}")
        lines.append(f"HAS_SUCCESSORS={'true' if info.has_successors else 'false'}")
        lines.append(f"LATEST_SUCCESSOR={info.latest_successor or ''}")
        lines.append(
            f"ITERATION_LOG_FOUND={'true' if info.iteration_log_found else 'false'}"
        )
    else:
        lines.append("WORK_DIR=")
        lines.append("WORK_DIR_NAME=")
        lines.append("WORK_TYPE=")
        lines.append("STATUS_NORMALIZED=")
        lines.append("STATUS_RAW=")
        lines.append("HAS_SUCCESSORS=false")
        lines.append("LATEST_SUCCESSOR=")
        lines.append("ITERATION_LOG_FOUND=false")
    triggers_str = ",".join(result.triggers.labels) or "none"
    lines.append(f"TRIGGERS_DETECTED={triggers_str}")
    lines.append(f"RECOMMENDED_NEXT_DOC={result.recommended_next_doc}")
    lines.append("REASONING:")
    for bullet in result.reasoning:
        lines.append(f"  - {bullet}")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Routing helper for fullstack-impl skill",
    )
    parser.add_argument(
        "--workspace-root",
        required=True,
        help="Workspace root containing fullstack.json",
    )
    parser.add_argument(
        "--work-dir-name",
        default="",
        help=(
            "Name of the work directory the user is referencing "
            "(without the type/ prefix). Empty means no specific match."
        ),
    )
    parser.add_argument(
        "--prompt",
        default="",
        help="Inline user prompt text for verb detection",
    )
    parser.add_argument(
        "--prompt-file",
        default="",
        help="Path to a file containing the user prompt (overrides --prompt)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    workspace_root = Path(args.workspace_root).resolve()
    if not workspace_root.is_dir():
        print(f"ERROR: workspace root not a directory: {workspace_root}", file=sys.stderr)
        return 1

    workspace = check_workspace(workspace_root)
    if workspace["WORKSPACE_VALID"] != "true":
        print(f"WORKSPACE_VALID={workspace['WORKSPACE_VALID']}")
        print(f"MISSING={workspace['MISSING']}")
        print(
            "ERROR: workspace not initialized; run check_workspace.py for details",
            file=sys.stderr,
        )
        return 2

    docs_dir_name = workspace["DOCS_DIR"] or "ai-documents"
    docs_root = workspace_root / docs_dir_name
    if not docs_root.is_dir():
        print(f"ERROR: docs directory not found: {docs_root}", file=sys.stderr)
        return 2

    prompt = args.prompt
    if args.prompt_file:
        prompt_path = Path(args.prompt_file)
        if not prompt_path.is_file():
            print(f"ERROR: prompt file not found: {prompt_path}", file=sys.stderr)
            return 1
        prompt = prompt_path.read_text(encoding="utf-8")

    work_dir_path, work_type = find_work_dir(docs_root, args.work_dir_name)
    work_info: WorkDirInfo | None = None
    if work_dir_path is not None and work_type is not None:
        work_info = load_work_dir_info(work_dir_path, work_type)

    triggers = detect_triggers(prompt)
    result = decide_route(work_info, triggers)

    print(format_result(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
