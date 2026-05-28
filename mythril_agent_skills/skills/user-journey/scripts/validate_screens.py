#!/usr/bin/env python3
"""Validate the screens[] and top-level arrows[] in a user-journey workspace.

Enforces the rules documented in references/SCREENS-RULES.md (v3 canvas
schema):

  1.  screen.id is unique
  2.  every arrow.to resolves to a screen
  3.  every arrow.from resolves — `<screen-id>` (whole-screen anchor) or
      `<screen-id>#<element-id>` (anchored at a specific element / side-key
      rail key / hardware slot)
  4.  step.screen_refs[] all resolve
  5.  orphan screens (warning) — no step refs them AND no arrow points at them
  6.  dead-end non-terminal screens (info) — no outgoing arrows, but the
      screen sits in the middle of a flow
  7.  at most one is_default = true arrow per SOURCE screen
  8.  interactive elements should have an id (warning)
  9.  device-aware modeling — any atm-screen / kiosk-screen journey that
      lacks chrome / side-key-rail / hardware anywhere of that kind warns
  10. screen-count floor — in --strict mode, a journey with N stages must
      have at least max(N*2, 8) screens
  11. design-pattern smells — flat-stack / no-hierarchy / monotonous /
      overstuffed (advisory warnings)
  12. arrow bundle-spam — ≥ 3 element-anchored kind=default arrows from
      one screen to the same target should be merged via via_elements[]

Exit codes:
  0 — all rules pass (warnings/infos still printed)
  1 — at least one ERROR
  2 — workspace structure invalid (missing journey.json)

Output format (stable, parsed by AI):

    STATUS=PASS|FAIL
    SCHEMA_VERSION=<n>
    SCREENS_CHECKED=<n>
    ARROWS_CHECKED=<n>
    ERROR:   <message>
    WARNING: <message>
    INFO:    <message>

Usage:
  python3 validate_screens.py <workspace-path>            # warnings + errors
  python3 validate_screens.py <workspace-path> --strict   # promote certain
                                                           # warnings to errors
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Pure helpers (testable; no I/O)
# ---------------------------------------------------------------------------

CONTAINER_TYPES = {"stack", "grid", "row", "section", "list"}

# A "structural" element groups other elements visually. A screen with
# many children but ZERO structural elements is the design-pattern
# anti-pattern we want to catch ("flat element soup").
STRUCTURAL_TYPES = {
    "app-bar", "header", "section", "section-header",
    "footer-bar", "tab-bar",
    "step-indicator", "alert", "empty-state",
    "card", "key-value-list",
}

# Atomic (non-grouping) primitives — multiple of these in a row
# without any structural break is a smell.
ATOMIC_TYPES = {
    "text", "button", "keypad-button", "icon-button",
    "form-field", "search-bar", "list-item", "chip",
    "toast", "progress", "divider", "badge", "spacer",
    "image-placeholder", "key-value", "stat-tile", "avatar",
}

# Device kinds where we expect at least one device-specific element
# (side-key-rail or hardware-slot) or chrome="panel". Modeling these
# as a plain stack/grid of buttons usually means the AI defaulted to
# mobile thinking — flag it.
DEVICE_KINDS_REQUIRING_HARDWARE_HINT = {"atm-screen", "kiosk-screen"}

# Density thresholds — tuned to match what looks bad visually.
MAX_FLAT_CHILDREN     = 8   # children in root stack with no structural elements
MAX_SECTION_CHILDREN  = 6   # immediate children in a single section
MIN_PRIMITIVE_VARIETY = 2   # at least 2 different atomic primitive types when body > 4
MONOTONY_THRESHOLD    = 0.8 # >= 80% of atomic elements being the same type = monotonous


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
    elif el_type == "tab-bar":
        for item in node.get("items", []) or []:
            if isinstance(item, dict):
                iid = item.get("id")
                if isinstance(iid, str) and iid:
                    out.add(iid)
    elif el_type == "key-value-list":
        for item in node.get("items", []) or []:
            if isinstance(item, dict):
                iid = item.get("id")
                if isinstance(iid, str) and iid:
                    out.add(iid)
    elif el_type in {"footer-bar", "app-bar"}:
        for action in node.get("actions", []) or []:
            if isinstance(action, dict):
                aid = action.get("id")
                if isinstance(aid, str) and aid:
                    out.add(aid)
    if el_type in {"empty-state", "alert", "section"}:
        action = node.get("action")
        if isinstance(action, dict):
            aid = action.get("id")
            if isinstance(aid, str) and aid:
                out.add(aid)


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
                out.append({**key, "type": "side-key"})
    elif el_type == "tab-bar":
        for item in node.get("items", []) or []:
            if isinstance(item, dict):
                out.append({**item, "type": "tab-item"})
    elif el_type == "key-value-list":
        for item in node.get("items", []) or []:
            if isinstance(item, dict):
                out.append({**item, "type": "key-value"})
    elif el_type in {"footer-bar", "app-bar"}:
        for action in node.get("actions", []) or []:
            if isinstance(action, dict):
                out.append({**action, "type": "action"})
    elif el_type in {"empty-state", "alert"}:
        action = node.get("action")
        if isinstance(action, dict):
            out.append({**action, "type": "action"})


def find_interactive_without_id(layout: dict | None) -> list[str]:
    """Return type names of interactive elements that have no id."""
    bad: list[str] = []
    for node in collect_elements(layout):
        if node.get("interactive") and not (isinstance(node.get("id"), str) and node.get("id")):
            bad.append(str(node.get("type", "<unknown>")))
    return bad


def assess_design_pattern_sense(screen: dict) -> list[str]:
    """Inspect a screen's layout for flat-element-soup smells.

    Returns a list of warning messages (one per smell), each starting
    with a `[smell-name]` tag. Pure: takes a screen dict, returns a
    list. The smells we look for:

      [flat-stack]     root is a stack/grid with > MAX_FLAT_CHILDREN
                       direct children AND no structural element
                       (app-bar, section, header, tab-bar, ...)
                       — almost always means "I dumped atoms into one
                       stack" rather than composing patterns.
      [no-hierarchy]   screen body has > 4 atomic elements and no
                       structural element anywhere — no app-bar, no
                       header, no section, no tab-bar. Reviewer has
                       no anchor to read the screen.
      [monotonous]     ≥ MONOTONY_THRESHOLD of the atomic elements
                       are the same primitive type (e.g. 9 buttons
                       in a row, 8 text lines in a stack).
      [overstuffed]    some section has > MAX_SECTION_CHILDREN
                       immediate children — should be split.

    These warnings are advisory — they fire on lo-fi screens that
    work but lack design-pattern sense. They do NOT fail the build.
    """
    msgs: list[str] = []
    if not isinstance(screen, dict):
        return msgs
    sid = screen.get("id", "?")
    layout = screen.get("layout")
    if not isinstance(layout, dict):
        return msgs

    all_elements = collect_elements(layout)
    structural = [e for e in all_elements if e.get("type") in STRUCTURAL_TYPES]
    atomic = [e for e in all_elements if e.get("type") in ATOMIC_TYPES]

    # [flat-stack] — root is a stack/grid with many children and no
    # structural element among them.
    root_type = layout.get("type")
    if root_type in {"stack", "grid"}:
        direct_children = layout.get("elements", []) or []
        n_direct = len([c for c in direct_children if isinstance(c, dict)])
        direct_structural = sum(
            1 for c in direct_children
            if isinstance(c, dict) and c.get("type") in STRUCTURAL_TYPES
        )
        if n_direct > MAX_FLAT_CHILDREN and direct_structural == 0:
            msgs.append(
                f"[flat-stack] screen '{sid}' root {root_type} has {n_direct} "
                f"direct children and no app-bar/section/header — group into "
                f"2-4 sections instead of one big stack. See WIREFRAMES.md "
                f"'Composition recipes'."
            )

    # [no-hierarchy] — many atomic elements but no structural anchor.
    if len(atomic) > 4 and not structural:
        msgs.append(
            f"[no-hierarchy] screen '{sid}' has {len(atomic)} atomic "
            f"elements but no app-bar, header, section, or tab-bar — add "
            f"at least one structural primitive so the screen reads as "
            f"a screen, not a pile of widgets."
        )

    # [monotonous] — most of the body is the same primitive.
    if len(atomic) >= 5:
        counts: dict[str, int] = {}
        for e in atomic:
            t = str(e.get("type", "?"))
            counts[t] = counts.get(t, 0) + 1
        dominant_type, dominant_count = max(counts.items(), key=lambda kv: kv[1])
        ratio = dominant_count / len(atomic)
        if ratio >= MONOTONY_THRESHOLD and dominant_type not in {"keypad-button", "key-value", "list-item"}:
            msgs.append(
                f"[monotonous] screen '{sid}' is {int(ratio*100)}% '{dominant_type}' "
                f"elements ({dominant_count}/{len(atomic)}) — mix at least one "
                f"other primitive (section, alert, stat-tile, divider, ...) "
                f"to break the rhythm."
            )

    # [overstuffed] — any section with too many immediate children.
    for elem in all_elements:
        if elem.get("type") == "section":
            n = len([c for c in elem.get("elements", []) or [] if isinstance(c, dict)])
            if n > MAX_SECTION_CHILDREN:
                section_label = elem.get("title") or elem.get("id") or "?"
                msgs.append(
                    f"[overstuffed] screen '{sid}' section '{section_label}' "
                    f"has {n} immediate children — split into 2 sections "
                    f"(max {MAX_SECTION_CHILDREN})."
                )

    return msgs


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
    worth opening on the canvas at all.
    """
    n_stages = len([s for s in stages if isinstance(s, dict)])
    return max(n_stages * 2, 8)


def parse_arrow_from(value: str) -> tuple[str, str | None]:
    """Parse an arrow `from` field into (screen_id, element_id_or_None).

    Accepts both `<screen-id>` and `<screen-id>#<element-id>` forms.
    Empty or non-string input returns ("", None).
    """
    if not isinstance(value, str) or not value:
        return "", None
    if "#" not in value:
        return value, None
    screen_id, _, element_id = value.partition("#")
    element_id = element_id.strip() or None
    return screen_id, element_id


VALID_ARROW_KINDS = {"default", "success", "error", "cancel"}
VALID_ARROW_TRIGGERS = {
    "tap", "long-press", "swipe", "input",
    "insert-card", "timeout", "auto",
}
VALID_SCREEN_STATES = {"default", "loading", "success", "error", "warning"}

# Rule 12 — [bundle-spam] threshold. Three+ element-anchored arrows from
# one screen to the same target with kind=default is almost always the
# "one arrow per amount preset" anti-pattern. Two would be fine
# (e.g. "confirm" + "skip" both leading to the next screen is a
# legitimate split); three is where it stops being expressive and
# starts being noise.
BUNDLE_SPAM_THRESHOLD = 3


def _bundle_spam_warnings(arrows: list[dict], screen_ids: dict[str, dict]) -> list[str]:
    """Detect groups of N parallel kind=default arrows from screen A to
    screen B that all anchor at distinct elements on A. The recommended
    fix is to merge them into one arrow with `via_elements[]`.

    Pure: arrows + screen index in, list of warning strings out.
    """
    msgs: list[str] = []
    # Bucket: (from_screen, to_screen) -> list of (idx, element_id)
    buckets: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for idx, arrow in enumerate(arrows, start=1):
        if not isinstance(arrow, dict):
            continue
        if arrow.get("do_not_consolidate") is True:
            continue
        kind = arrow.get("kind") or "default"
        if kind != "default":
            continue
        if isinstance(arrow.get("via_elements"), list) and arrow.get("via_elements"):
            # Already bundled — author did the right thing.
            continue
        from_value = arrow.get("from", "")
        to_value = arrow.get("to", "")
        from_screen, from_element = parse_arrow_from(from_value)
        to_screen, _ = parse_arrow_from(to_value if isinstance(to_value, str) else "")
        if not from_screen or not to_screen:
            continue
        if from_screen not in screen_ids or to_screen not in screen_ids:
            continue
        if not from_element:
            continue  # whole-screen anchors aren't part of the spam case
        if from_screen == to_screen:
            continue  # self-loops are intentional
        buckets.setdefault((from_screen, to_screen), []).append((idx, from_element))

    for (from_screen, to_screen), members in buckets.items():
        n = len(members)
        if n < BUNDLE_SPAM_THRESHOLD:
            continue
        elements_preview = ", ".join(repr(e) for _, e in members[:4])
        if n > 4:
            elements_preview += ", ..."
        msgs.append(
            f"[bundle-spam] {n} arrows go from screen '{from_screen}' to "
            f"screen '{to_screen}' all with kind='default', anchored at "
            f"distinct elements ({elements_preview}) — collapse into ONE "
            f"arrow with via_elements=[{elements_preview}] for canvas "
            f"legibility. Renderer auto-merges them on screen, but the "
            f"JSON stays cleaner if you bundle them explicitly. See "
            f"SCHEMA.md 'via_elements' and SKILL.md 'Arrow modeling'."
        )
    return msgs


def validate_screens(
    screens: list[dict] | None,
    stages: list[dict] | None,
    arrows: list[dict] | None = None,
    strict: bool = False,
) -> dict:
    """Run all screen + arrow rules.

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
    arrows = arrows or []

    # Build screen index + element-id sets (layout elements + side-key-rail
    # keys + hardware[] slots are all valid <screen>#<element> references).
    screen_ids: dict[str, dict] = {}
    element_ids_per_screen: dict[str, set[str]] = {}

    for screen in screens:
        if not isinstance(screen, dict):
            errors.append(f"screen entry is not an object: {screen!r}")
            continue
        sid = screen.get("id")
        if not isinstance(sid, str) or not sid:
            errors.append(f"screen missing 'id': {screen!r}")
            continue
        if sid in screen_ids:
            errors.append(f"duplicate screen id '{sid}'")
            continue
        screen_ids[sid] = screen
        addressable = collect_element_ids(screen.get("layout"))
        addressable.update(collect_hardware_ids(screen))
        element_ids_per_screen[sid] = addressable

        # state sanity
        state = screen.get("state")
        if state is not None and state not in VALID_SCREEN_STATES:
            errors.append(
                f"screen '{sid}' has invalid state='{state}' — must be one of "
                f"{sorted(VALID_SCREEN_STATES)}"
            )

        # position sanity
        pos = screen.get("position")
        if pos is not None:
            if not isinstance(pos, dict) or "x" not in pos or "y" not in pos:
                errors.append(
                    f"screen '{sid}' position must be {{x, y}} object, got {pos!r}"
                )

        # interactive-without-id warnings come from layout walking
        layout = screen.get("layout")
        if isinstance(layout, dict):
            for bad_type in find_interactive_without_id(layout):
                warnings.append(
                    f"screen '{sid}' has interactive element of type "
                    f"'{bad_type}' without id — no arrow can reference it"
                )
            # Design-pattern smells (flat stack, no hierarchy,
            # monotonous, overstuffed sections).
            for msg in assess_design_pattern_sense(screen):
                warnings.append(msg)
        else:
            errors.append(f"screen '{sid}' has no layout object")

    # Build inbound counts (from step refs + arrows) and outbound counts
    inbound_by_step: dict[str, int] = {sid: 0 for sid in screen_ids}
    inbound_by_arrow: dict[str, int] = {sid: 0 for sid in screen_ids}
    outbound_by_screen: dict[str, int] = {sid: 0 for sid in screen_ids}
    default_count_by_screen: dict[str, int] = {sid: 0 for sid in screen_ids}

    # Step -> screen refs
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

    # Arrows
    arrows_checked = 0
    seen_arrow_ids: set[str] = set()
    for idx, arrow in enumerate(arrows, start=1):
        arrows_checked += 1
        if not isinstance(arrow, dict):
            errors.append(f"arrow #{idx} is not an object")
            continue
        aid = arrow.get("id")
        if isinstance(aid, str) and aid:
            if aid in seen_arrow_ids:
                errors.append(f"arrow #{idx} duplicate id '{aid}'")
            seen_arrow_ids.add(aid)

        # `from` parsing
        from_screen, from_element = parse_arrow_from(arrow.get("from", ""))
        if not from_screen:
            errors.append(f"arrow #{idx} missing/blank 'from'")
        elif from_screen not in screen_ids:
            errors.append(
                f"arrow #{idx} from='{arrow.get('from')}' — screen "
                f"'{from_screen}' does not exist in screens[]"
            )
        elif from_element is not None:
            if from_element not in element_ids_per_screen.get(from_screen, set()):
                errors.append(
                    f"arrow #{idx} from='{arrow.get('from')}' — element "
                    f"'{from_element}' not found in screen '{from_screen}'"
                )

        # `to` parsing
        to_value = arrow.get("to")
        if not isinstance(to_value, str) or not to_value:
            errors.append(f"arrow #{idx} missing/blank 'to'")
        else:
            # `to` may or may not include `#<el>`; renderer treats both
            # as "land on the whole screen". We tolerate the `#` form but
            # only validate the screen part.
            to_screen, _ = parse_arrow_from(to_value)
            if to_screen not in screen_ids:
                errors.append(
                    f"arrow #{idx} to='{to_value}' does not exist in screens[]"
                )
            else:
                inbound_by_arrow[to_screen] += 1

        # kind / trigger sanity
        kind = arrow.get("kind")
        if kind is not None and kind not in VALID_ARROW_KINDS:
            errors.append(
                f"arrow #{idx} has invalid kind='{kind}' — must be one of "
                f"{sorted(VALID_ARROW_KINDS)}"
            )
        trigger = arrow.get("trigger")
        if trigger is not None and trigger not in VALID_ARROW_TRIGGERS:
            errors.append(
                f"arrow #{idx} has invalid trigger='{trigger}' — must be one of "
                f"{sorted(VALID_ARROW_TRIGGERS)}"
            )

        # via_elements[] validation. When present, `from` MUST be a
        # whole-screen anchor (no `#element`) and every listed element
        # id MUST resolve on the source screen.
        via = arrow.get("via_elements")
        if via is not None:
            if not isinstance(via, list):
                errors.append(
                    f"arrow #{idx} via_elements must be a list of element ids, "
                    f"got {type(via).__name__}"
                )
            elif not via:
                errors.append(
                    f"arrow #{idx} via_elements is an empty list — either "
                    f"drop the field or list at least one element id"
                )
            else:
                if from_element is not None:
                    errors.append(
                        f"arrow #{idx} from='{arrow.get('from')}' has both an "
                        f"explicit '#{from_element}' anchor AND via_elements[] — "
                        f"use whole-screen 'from' (e.g. '{from_screen}') and put "
                        f"all element ids in via_elements"
                    )
                if from_screen and from_screen in screen_ids:
                    valid_ids = element_ids_per_screen.get(from_screen, set())
                    for v_idx, vid in enumerate(via):
                        if not isinstance(vid, str) or not vid:
                            errors.append(
                                f"arrow #{idx} via_elements[{v_idx}] is not a "
                                f"non-empty string"
                            )
                            continue
                        if vid not in valid_ids:
                            errors.append(
                                f"arrow #{idx} via_elements[{v_idx}]='{vid}' "
                                f"not found in screen '{from_screen}'"
                            )

        # outbound counts + default uniqueness
        if from_screen and from_screen in screen_ids:
            outbound_by_screen[from_screen] += 1
            if arrow.get("is_default") is True:
                default_count_by_screen[from_screen] += 1

    # Rule 7 — at most one is_default per source screen
    for sid, n in default_count_by_screen.items():
        if n > 1:
            errors.append(
                f"{n} arrows out of screen '{sid}' have is_default=true — "
                f"only one main path is allowed per source screen"
            )

    # Rule 12 — [bundle-spam] N parallel default arrows from one screen
    # to the same target. Symptom of authoring "one arrow per button"
    # for screens like amount-presets or chip-pickers. Renderer
    # auto-collapses at draw time (see arrows.js consolidateArrows), but
    # we still nag the author so the JSON itself stays clean.
    warnings.extend(
        _bundle_spam_warnings(arrows, screen_ids)
    )

    # Rule 5 — orphans + Rule 6 — dead-end mid-flow screens
    for sid, screen in screen_ids.items():
        total_inbound = inbound_by_step.get(sid, 0) + inbound_by_arrow.get(sid, 0)
        if total_inbound == 0 and not screen.get("orphan_ok"):
            warnings.append(
                f"screen '{sid}' has no incoming references — no step references "
                f"it AND no arrow points at it"
            )
        if outbound_by_screen.get(sid, 0) == 0:
            referenced_in: list[tuple[str, str, int]] = []
            for stage in stages:
                if not isinstance(stage, dict):
                    continue
                for step_idx, step in enumerate(stage.get("steps", []) or [], 1):
                    if isinstance(step, dict) and sid in (step.get("screen_refs") or []):
                        referenced_in.append((stage.get("id", "?"), step.get("id", "?"), step_idx))
            if referenced_in:
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
                        f"screen '{sid}' has no outgoing arrows but appears "
                        f"in step {last[2]} of {step_count_in_stage} in stage "
                        f"'{stage_id_for_last}' — likely needs at least one arrow out"
                    )

    # Rule 9 — device-aware modeling check (journey-wide per kind)
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

    # Rule 10 — screen-count gate (warn / strict-error)
    real_screen_count = len([s for s in screens if isinstance(s, dict)])
    real_stage_count  = len([s for s in stages  if isinstance(s, dict)])
    if real_screen_count > 0 or real_stage_count > 0:
        min_screens = compute_min_screen_count(stages)
        if real_screen_count < min_screens:
            msg = (
                f"only {real_screen_count} screens defined for {real_stage_count} stages "
                f"— canvas will be sparse. Recommended floor is max(stages*2, 8) "
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
        "arrows_checked": arrows_checked,
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
            "arrows_checked": 0,
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
            "arrows_checked": 0,
        }

    schema_version = str(data.get("schema_version") or "")
    screens = data.get("screens") or []
    stages = data.get("stages") or []
    arrows = data.get("arrows") or []
    report = validate_screens(screens, stages, arrows, strict=strict)
    return {
        "structure_ok": True,
        "errors": report["errors"],
        "warnings": report["warnings"],
        "info": report["info"],
        "schema_version": schema_version,
        "screens_checked": len(screens),
        "arrows_checked": report["arrows_checked"],
    }


def print_report(report: dict) -> int:
    status = "FAIL" if report["errors"] or not report.get("structure_ok") else "PASS"
    print(f"STATUS={status}")
    print(f"SCHEMA_VERSION={report.get('schema_version', '')}")
    print(f"SCREENS_CHECKED={report.get('screens_checked', 0)}")
    print(f"ARROWS_CHECKED={report.get('arrows_checked', 0)}")
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
        description="Validate screens[] and arrows[] in a user-journey workspace.",
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
