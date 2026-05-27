#!/usr/bin/env python3
"""Validate the screens[] and transitions[] in a user-journey workspace.

Enforces the rules documented in references/SCREENS-RULES.md:

  1.  screen.id is unique
  2.  transitions.to_screen resolves
  3.  transitions.from_element exists in the screen's layout, in
      side-key-rail keys, in screen.hardware[], or is "any"
  4.  step.screen_refs[] all resolve
  5.  orphan screens (warning)
  6.  dead-end non-terminal screens (info)
  7.  at most one is_default: true per screen
  8.  interactive elements should have an id (warning)
  9.  device-specific elements present when kind suggests them
      (e.g. atm-screen without side-key-rail / hardware / chrome → warning)
  10. screen count gate — in --strict mode, a journey with N stages must
      have at least max(N*2, 8) screens; otherwise it's a "stage map only"
      and the Flow view will be empty/thin

Exit codes:
  0 — all rules pass (warnings/infos still printed)
  1 — at least one ERROR
  2 — workspace structure invalid (missing journey.json)

Output format (stable, parsed by AI):

    STATUS=PASS|FAIL
    SCHEMA_VERSION=<n>
    SCREENS_CHECKED=<n>
    TRANSITIONS_CHECKED=<n>
    ERROR:   <message>
    WARNING: <message>
    INFO:    <message>

Usage:
  python3 validate_screens.py <workspace-path>            # warnings + errors
  python3 validate_screens.py <workspace-path> --strict   # promote certain
                                                           # warnings to errors
                                                           # (screen-count gate)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Pure helpers (testable; no I/O)
# ---------------------------------------------------------------------------

CONTAINER_TYPES = {"stack", "grid", "row"}

# Device kinds where we expect at least one device-specific element
# (side-key-rail or hardware-slot) or chrome="panel". Modeling these
# as a plain stack/grid of buttons usually means the AI defaulted to
# mobile thinking — flag it.
DEVICE_KINDS_REQUIRING_HARDWARE_HINT = {"atm-screen", "kiosk-screen"}


def collect_element_ids(layout: dict | None) -> set[str]:
    """Walk a layout tree and collect all element ids (containers + leaves +
    side-key-rail keys)."""
    ids: set[str] = set()
    if not isinstance(layout, dict):
        return ids
    _walk_collect_ids(layout, ids)
    return ids


def _walk_collect_ids(node: dict, out: set[str]) -> None:
    if not isinstance(node, dict):
        return
    el_id = node.get("id")
    if isinstance(el_id, str) and el_id:
        out.add(el_id)
    el_type = node.get("type")
    if el_type in CONTAINER_TYPES:
        for child in node.get("elements", []) or []:
            _walk_collect_ids(child, out)
    elif el_type == "side-key-rail":
        for key in node.get("keys", []) or []:
            if isinstance(key, dict):
                kid = key.get("id")
                if isinstance(kid, str) and kid:
                    out.add(kid)


def collect_hardware_ids(screen: dict | None) -> set[str]:
    """Collect ids from screen.hardware[] (chrome bezel slots)."""
    ids: set[str] = set()
    if not isinstance(screen, dict):
        return ids
    for slot in screen.get("hardware", []) or []:
        if not isinstance(slot, dict):
            continue
        sid = slot.get("id")
        if isinstance(sid, str) and sid:
            ids.add(sid)
    return ids


def collect_elements(layout: dict | None) -> list[dict]:
    """Walk a layout tree and collect every leaf-or-container element node,
    plus each side-key-rail key as a synthetic element with type='side-key'."""
    elements: list[dict] = []
    if not isinstance(layout, dict):
        return elements
    _walk_collect(layout, elements)
    return elements


def _walk_collect(node: dict, out: list[dict]) -> None:
    if not isinstance(node, dict):
        return
    out.append(node)
    el_type = node.get("type")
    if el_type in CONTAINER_TYPES:
        for child in node.get("elements", []) or []:
            _walk_collect(child, out)
    elif el_type == "side-key-rail":
        for key in node.get("keys", []) or []:
            if isinstance(key, dict):
                # Treat the key as a synthetic element node so the
                # "interactive-without-id" check still applies.
                out.append({**key, "type": "side-key"})


def find_interactive_without_id(layout: dict | None) -> list[str]:
    """Return type names of interactive elements that have no id."""
    bad: list[str] = []
    for node in collect_elements(layout):
        if node.get("interactive") and not (isinstance(node.get("id"), str) and node.get("id")):
            bad.append(str(node.get("type", "<unknown>")))
    return bad


def screen_has_device_specific_elements(screen: dict) -> bool:
    """True if the screen uses chrome=panel, has hardware[], or contains at
    least one side-key-rail or hardware-slot element in its layout."""
    if not isinstance(screen, dict):
        return False
    if screen.get("chrome") == "panel":
        return True
    if screen.get("hardware"):
        return True
    for node in collect_elements(screen.get("layout")):
        if node.get("type") in {"side-key-rail", "hardware-slot"}:
            return True
    return False


def compute_min_screen_count(stages: list[dict]) -> int:
    """Suggested floor for screens[] given a stage count.

    Rule of thumb: every stage needs at least 2 UI moments to show
    real interaction, and the whole journey needs at least 8 to be
    worth opening in Flow view at all. Both bounds are intentional
    minimums — most journeys deserve more.
    """
    n_stages = len([s for s in stages if isinstance(s, dict)])
    return max(n_stages * 2, 8)


def validate_screens(
    screens: list[dict] | None,
    stages: list[dict] | None,
    strict: bool = False,
) -> dict:
    """Run all screen-rules.

    Returns a dict with keys errors/warnings/info, each a list[str].
    Pure: takes parsed JSON, returns lists.

    When `strict` is True, certain warnings escalate to errors:
      - screen count below `compute_min_screen_count(stages)`
    """
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    screens = screens or []
    stages = stages or []

    # Build screen index + element-id sets (layout elements + side-key-rail
    # keys + hardware[] slots are all valid from_element references).
    screen_ids: dict[str, dict] = {}
    element_ids_per_screen: dict[str, set[str]] = {}
    duplicates: set[str] = set()

    for screen in screens:
        if not isinstance(screen, dict):
            errors.append(f"screen entry is not an object: {screen!r}")
            continue
        sid = screen.get("id")
        if not isinstance(sid, str) or not sid:
            errors.append(f"screen missing 'id': {screen!r}")
            continue
        if sid in screen_ids:
            duplicates.add(sid)
            errors.append(f"duplicate screen id '{sid}'")
            continue
        screen_ids[sid] = screen
        addressable = collect_element_ids(screen.get("layout"))
        addressable.update(collect_hardware_ids(screen))
        element_ids_per_screen[sid] = addressable

    # Build a count of inbound references: from step.screen_refs and from
    # any transitions.to_screen (we only flag a screen with ZERO inbound and
    # not used by any step as truly orphan).
    inbound_by_step: dict[str, int] = {sid: 0 for sid in screen_ids}
    inbound_by_transition: dict[str, int] = {sid: 0 for sid in screen_ids}

    for stage in stages:
        if not isinstance(stage, dict):
            continue
        for step in stage.get("steps", []) or []:
            if not isinstance(step, dict):
                continue
            refs = step.get("screen_refs", []) or []
            if not isinstance(refs, list):
                errors.append(
                    f"stage '{stage.get('id', '?')}' step '{step.get('id', '?')}' "
                    f"screen_refs is not a list"
                )
                continue
            for idx, ref in enumerate(refs):
                if not isinstance(ref, str) or not ref:
                    errors.append(
                        f"stage '{stage.get('id', '?')}' step '{step.get('id', '?')}' "
                        f"screen_refs[{idx}] is not a non-empty string"
                    )
                    continue
                if ref not in screen_ids:
                    errors.append(
                        f"stage '{stage.get('id', '?')}' step '{step.get('id', '?')}' "
                        f"screen_refs[{idx}]='{ref}' does not exist in screens[]"
                    )
                else:
                    inbound_by_step[ref] += 1

    # Per-screen checks: transitions resolve, is_default uniqueness, interactive ids,
    # outbound counts.
    transitions_checked = 0
    outbound_count: dict[str, int] = {sid: 0 for sid in screen_ids}

    for sid, screen in screen_ids.items():
        layout = screen.get("layout")
        if not isinstance(layout, dict):
            errors.append(f"screen '{sid}' has no layout object")
        else:
            for bad_type in find_interactive_without_id(layout):
                warnings.append(
                    f"screen '{sid}' has interactive element of type "
                    f"'{bad_type}' without id — no transition can reference it"
                )

        transitions = screen.get("transitions", []) or []
        if not isinstance(transitions, list):
            errors.append(f"screen '{sid}' transitions is not a list")
            continue

        default_count = 0
        for idx, tx in enumerate(transitions):
            transitions_checked += 1
            if not isinstance(tx, dict):
                errors.append(f"screen '{sid}' transition #{idx + 1} is not an object")
                continue

            to_screen = tx.get("to_screen")
            if not isinstance(to_screen, str) or not to_screen:
                errors.append(
                    f"screen '{sid}' transition #{idx + 1} missing/blank to_screen"
                )
            elif to_screen not in screen_ids:
                errors.append(
                    f"screen '{sid}' transition #{idx + 1} to_screen='{to_screen}' "
                    f"does not exist in screens[]"
                )
            else:
                inbound_by_transition[to_screen] += 1

            from_element = tx.get("from_element")
            if not isinstance(from_element, str) or not from_element:
                errors.append(
                    f"screen '{sid}' transition #{idx + 1} missing/blank from_element"
                )
            elif from_element != "any":
                if from_element not in element_ids_per_screen.get(sid, set()):
                    errors.append(
                        f"screen '{sid}' transition #{idx + 1} from_element="
                        f"'{from_element}' has no element with that id in this "
                        f"screen's layout"
                    )

            trigger = tx.get("trigger")
            if not isinstance(trigger, str) or not trigger:
                errors.append(
                    f"screen '{sid}' transition #{idx + 1} missing trigger"
                )

            if tx.get("is_default") is True:
                default_count += 1

            outbound_count[sid] += 1

        if default_count > 1:
            errors.append(
                f"screen '{sid}' has {default_count} transitions with "
                f"is_default=true — only one main path is allowed per screen"
            )

    # Orphans + dead-ends
    for sid in screen_ids:
        total_inbound = inbound_by_step.get(sid, 0) + inbound_by_transition.get(sid, 0)
        if total_inbound == 0 and not screen_ids[sid].get("orphan_ok"):
            warnings.append(
                f"screen '{sid}' has no incoming references — no step references "
                f"it AND no transition points at it"
            )
        if outbound_count.get(sid, 0) == 0:
            # Only worth flagging if it's referenced from a non-final step.
            referenced_in: list[tuple[str, str, int]] = []
            for stage in stages:
                if not isinstance(stage, dict):
                    continue
                for step_idx, step in enumerate(stage.get("steps", []) or [], 1):
                    if isinstance(step, dict) and sid in (step.get("screen_refs") or []):
                        referenced_in.append((stage.get("id", "?"), step.get("id", "?"), step_idx))
            if referenced_in:
                # Find the rightmost (stage, step) reference and decide if it
                # looks like a "middle" or "last" position.
                last = referenced_in[-1]
                stage_id_for_last = last[0]
                last_stage = next(
                    (st for st in stages if isinstance(st, dict) and st.get("id") == stage_id_for_last),
                    None,
                )
                step_count_in_stage = len(
                    (last_stage.get("steps") or []) if isinstance(last_stage, dict) else []
                )
                is_last_step_of_last_stage = (
                    last_stage is stages[-1] if stages else False
                ) and last[2] == step_count_in_stage
                if not is_last_step_of_last_stage:
                    info.append(
                        f"screen '{sid}' has no outgoing transitions but appears "
                        f"in step {last[2]} of {step_count_in_stage} in stage "
                        f"'{stage_id_for_last}' — likely needs at least one transition out"
                    )

    # Device-aware modeling check: if a journey has any atm-screen / kiosk-screen
    # screens but NONE of them use any device-specific element (no chrome, no
    # hardware-slot, no side-key-rail anywhere), it's almost certainly modeled
    # as mobile screens with the wrong kind tag. We check per kind, journey-wide,
    # to avoid false positives on legitimate touch-only kiosk screens (e.g. a
    # product picker between a scan and a payment screen).
    for kind in DEVICE_KINDS_REQUIRING_HARDWARE_HINT:
        same_kind = [
            (sid, screen) for sid, screen in screen_ids.items()
            if screen.get("kind") == kind
        ]
        if not same_kind:
            continue
        if not any(screen_has_device_specific_elements(screen) for _, screen in same_kind):
            ids = ", ".join(f"'{sid}'" for sid, _ in same_kind)
            warnings.append(
                f"{len(same_kind)} screen(s) of kind='{kind}' ({ids}) but NONE "
                f"use side-key-rail / hardware-slot / chrome='panel' — these "
                f"are most likely modeled as mobile screens. At least one "
                f"transactional screen (main menu, hardware-interaction) "
                f"should use chrome='panel' + hardware[]. See "
                f"references/WIREFRAMES.md 'Device-aware modeling'."
            )

    # Screen-count gate: in strict mode, enforce a floor so authors don't
    # ship "stage map only" workspaces where Flow view is empty / thin.
    # Skip entirely when both stages and screens are empty (brand-new
    # workspace, nothing to evaluate yet).
    real_screen_count = len([s for s in screens if isinstance(s, dict)])
    real_stage_count  = len([s for s in stages  if isinstance(s, dict)])
    if real_screen_count > 0 or real_stage_count > 0:
        min_screens = compute_min_screen_count(stages)
        if real_screen_count < min_screens:
            msg = (
                f"only {real_screen_count} screens defined for {real_stage_count} stages "
                f"— Flow view will be sparse. Recommended floor is max(stages*2, 8) "
                f"= {min_screens}."
            )
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)

    return {
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "transitions_checked": transitions_checked,
    }


# ---------------------------------------------------------------------------
# Filesystem entry point
# ---------------------------------------------------------------------------

def validate_workspace(workspace: Path, strict: bool = False) -> dict:
    journey_path = workspace / "journey.json"
    if not journey_path.exists():
        return {
            "structure_ok": False,
            "errors": [f"missing journey.json in {workspace}"],
            "warnings": [],
            "info": [],
            "schema_version": "",
            "screens_checked": 0,
            "transitions_checked": 0,
        }
    try:
        data = json.loads(journey_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "structure_ok": False,
            "errors": [f"journey.json is invalid JSON: {exc}"],
            "warnings": [],
            "info": [],
            "schema_version": "",
            "screens_checked": 0,
            "transitions_checked": 0,
        }

    schema_version = str(data.get("schema_version") or "")
    screens = data.get("screens") or []
    stages = data.get("stages") or []
    report = validate_screens(screens, stages, strict=strict)
    return {
        "structure_ok": True,
        "errors": report["errors"],
        "warnings": report["warnings"],
        "info": report["info"],
        "schema_version": schema_version,
        "screens_checked": len(screens),
        "transitions_checked": report["transitions_checked"],
    }


def print_report(report: dict) -> int:
    status = "FAIL" if report["errors"] or not report.get("structure_ok") else "PASS"
    print(f"STATUS={status}")
    print(f"SCHEMA_VERSION={report.get('schema_version', '')}")
    print(f"SCREENS_CHECKED={report.get('screens_checked', 0)}")
    print(f"TRANSITIONS_CHECKED={report.get('transitions_checked', 0)}")
    for msg in report.get("errors", []):
        print(f"ERROR:   {msg}")
    for msg in report.get("warnings", []):
        print(f"WARNING: {msg}")
    for msg in report.get("info", []):
        print(f"INFO:    {msg}")
    if not report.get("structure_ok"):
        return 2
    return 1 if report.get("errors") else 0


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate screens[] and transitions[] in a user-journey workspace.",
    )
    parser.add_argument("path", help="path to the workspace directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="promote the screen-count gate from warning to error",
    )
    return parser.parse_args(argv if argv is None else list(argv))


def main() -> None:
    args = parse_args()
    report = validate_workspace(
        Path(args.path).expanduser().resolve(),
        strict=args.strict,
    )
    sys.exit(print_report(report))


if __name__ == "__main__":
    main()
