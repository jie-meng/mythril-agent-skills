"""Shared fixtures for skill script tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parent.parent / "mythril_agent_skills" / "skills"


def _add_scripts_to_path(skill_name: str) -> Path:
    """Add a skill's scripts/ directory to sys.path and return it."""
    scripts_dir = SKILLS_DIR / skill_name / "scripts"
    path_str = str(scripts_dir)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
    return scripts_dir


@pytest.fixture(scope="session", autouse=True)
def _setup_skill_paths() -> None:
    """Add all skill script directories to sys.path once per session."""
    for skill_dir in SKILLS_DIR.iterdir():
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.is_dir():
            _add_scripts_to_path(skill_dir.name)
