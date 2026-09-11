"""Verify the derived plugin marketplaces stay in sync with the canonical one.

``.claude-plugin/marketplace.json`` is the canonical, hand-edited catalog.
WorkBuddy AI and CodeBuddy Code read the same catalog format from
``.workbuddy-plugin/marketplace.json``, which is **generated** by
``scripts/sync-marketplaces.py`` (every field copied verbatim, minus the
Claude-specific ``$schema`` key).

This test fails if a derived catalog has drifted from the canonical source.
To fix drift, run:

    python3 scripts/sync-marketplaces.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
CANONICAL = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def _load_sync_module():
    """Load scripts/sync-marketplaces.py by path (the filename has a hyphen)."""
    spec_path = SCRIPTS_DIR / "sync-marketplaces.py"
    spec = importlib.util.spec_from_file_location("_sync_marketplaces", spec_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_sync_marketplaces"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sync_module():
    return _load_sync_module()


def test_sync_script_exists():
    assert (SCRIPTS_DIR / "sync-marketplaces.py").is_file(), (
        "scripts/sync-marketplaces.py is missing — needed to keep the "
        "WorkBuddy/CodeBuddy catalogs in sync with the canonical Claude one"
    )


def test_canonical_catalog_exists(sync_module):
    assert CANONICAL.is_file(), f"canonical catalog missing: {CANONICAL}"


def test_at_least_one_derived_target(sync_module):
    assert len(sync_module.targets()) >= 1, (
        "no derived marketplace targets configured — add the WorkBuddy "
        "catalog to DERIVED in scripts/sync-marketplaces.py"
    )


def test_no_drift(sync_module):
    """Every derived catalog must match what the generator would write."""
    expected = sync_module.render()
    drift: list[str] = []

    for label, target in sync_module.targets():
        if not target.is_file():
            drift.append(f"  - MISSING: {target.relative_to(REPO_ROOT)}  ({label})")
            continue
        if target.read_text(encoding="utf-8") != expected:
            drift.append(f"  - DRIFTED: {target.relative_to(REPO_ROOT)}  ({label})")

    assert not drift, (
        "Derived marketplace catalogs have drifted from "
        ".claude-plugin/marketplace.json. Run "
        "`python3 scripts/sync-marketplaces.py` to fix:\n" + "\n".join(drift)
    )


def test_workbuddy_catalog_is_valid_and_complete():
    """The WorkBuddy catalog must be valid JSON with every canonical plugin."""
    workbuddy = REPO_ROOT / ".workbuddy-plugin" / "marketplace.json"
    assert workbuddy.is_file(), "missing .workbuddy-plugin/marketplace.json"

    data = json.loads(workbuddy.read_text(encoding="utf-8"))
    canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))

    assert data["name"] == canonical["name"]
    assert [p["name"] for p in data["plugins"]] == [
        p["name"] for p in canonical["plugins"]
    ]
    # The Claude-only schema pointer must not leak into the derived catalog.
    assert "$schema" not in data
