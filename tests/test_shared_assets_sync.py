"""Verify bundled copies of shared assets stay in sync with canonical source.

The repo holds canonical copies of cross-skill assets under
`mythril_agent_skills/shared/`. Each consumer skill bundles a
byte-identical copy under its own `scripts/` or `references/` directory
(so skills installed individually remain self-contained).

This test fails if any bundled copy has drifted from its canonical
source. To fix drift, run:

    python3 scripts/sync-shared-assets.py
"""

from __future__ import annotations

import filecmp
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_sync_module():
    """Load scripts/sync-shared-assets.py as a fresh module each time.

    The script's filename uses a hyphen, so it cannot be imported via
    `import sync-shared-assets`. We load it by file path.
    """
    spec_path = SCRIPTS_DIR / "sync-shared-assets.py"
    spec = importlib.util.spec_from_file_location("_sync_shared_assets", spec_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["_sync_shared_assets"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sync_module():
    return _load_sync_module()


def test_sync_script_exists():
    assert (SCRIPTS_DIR / "sync-shared-assets.py").is_file(), (
        "scripts/sync-shared-assets.py is missing — needed to keep "
        "bundled mermaid assets in sync with the canonical source"
    )


def test_canonical_sources_exist(sync_module):
    """Every SyncSpec must point at a source file that actually exists."""
    for spec in sync_module.specs():
        assert spec.source.is_file(), (
            f"canonical source missing: {spec.source}"
        )


def test_at_least_one_consumer_per_spec(sync_module):
    """Each SyncSpec must have at least one consumer target."""
    for spec in sync_module.specs():
        assert len(spec.targets) >= 1, (
            f"SyncSpec for {spec.description} has no targets — remove "
            f"it from scripts/sync-shared-assets.py if no consumers"
        )


def test_no_drift(sync_module):
    """Every bundled copy must be byte-identical to its canonical source.

    Fix drift by running: python3 scripts/sync-shared-assets.py
    """
    drift: list[str] = []
    for spec in sync_module.specs():
        for target in spec.targets:
            if not target.is_file():
                drift.append(
                    f"  - MISSING: {target.relative_to(REPO_ROOT)} "
                    f"(should be a copy of {spec.source.relative_to(REPO_ROOT)})"
                )
                continue
            if not filecmp.cmp(spec.source, target, shallow=False):
                drift.append(
                    f"  - DRIFTED: {target.relative_to(REPO_ROOT)} "
                    f"differs from {spec.source.relative_to(REPO_ROOT)}"
                )
    assert not drift, (
        "Bundled shared assets have drifted from the canonical source. "
        "Run `python3 scripts/sync-shared-assets.py` to fix:\n"
        + "\n".join(drift)
    )
