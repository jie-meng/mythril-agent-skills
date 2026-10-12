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
import hashlib
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SKILLS_ROOT = REPO_ROOT / "mythril_agent_skills" / "skills"


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


def _declared_asset_names(sync_module) -> set[str]:
    """Every file name any SyncSpec declares, as source or bundled target."""
    names: set[str] = set()
    for spec in sync_module.specs():
        names.add(spec.source.name)
        names.update(target.name for target in spec.targets)
    return names


def _skill_of(path: Path) -> str:
    return path.relative_to(SKILLS_ROOT).parts[0]


def _cross_skill_duplicates() -> dict[str, list[Path]]:
    """Group skill-bundled files by content hash, keeping cross-skill groups.

    Empty files and `__init__.py` are skipped: a package marker carries
    nothing that can drift, so treating it as a shared asset would be noise.
    """
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in SKILLS_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.relative_to(SKILLS_ROOT).parts:
            continue
        if path.suffix not in (".py", ".md"):
            continue
        if path.name == "__init__.py" or path.stat().st_size == 0:
            continue
        groups[hashlib.sha256(path.read_bytes()).hexdigest()].append(path)

    return {
        digest: paths
        for digest, paths in groups.items()
        if len(paths) > 1 and len({_skill_of(p) for p in paths}) > 1
    }


def test_no_undeclared_duplicates(sync_module):
    """A cross-skill byte-identical copy must be a declared shared asset.

    The drift check above guards exactly what `specs()` declares, so a copy
    nobody declared passes it forever. That is how the fourth
    `check_workspace.py` arrived: a new skill was created by copying an
    existing one, and the guard had nothing to compare it against. This test
    treats duplication itself as the signal, so the next copy is caught at
    the moment it lands rather than when the two sides finally diverge.
    """
    declared = _declared_asset_names(sync_module)
    undeclared: list[str] = []
    for digest, paths in sorted(_cross_skill_duplicates().items()):
        stray = sorted({p.name for p in paths} - declared)
        if not stray:
            continue
        undeclared.append(
            f"  - {', '.join(stray)} ({len(paths)} copies, sha256 {digest[:12]}):\n"
            + "\n".join(
                f"      {p.relative_to(REPO_ROOT)}" for p in sorted(paths)
            )
        )

    assert not undeclared, (
        "These files are byte-identical across skills but no SyncSpec "
        "declares them, so editing one leaves the others stale with nothing "
        "to notice. Register them in scripts/sync-shared-assets.py, or remove "
        "the duplicate:\n" + "\n".join(undeclared)
    )
