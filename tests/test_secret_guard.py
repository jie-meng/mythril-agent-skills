"""Tests for the shared secret_guard credential-redaction asset."""

from __future__ import annotations

import base64
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "mythril_agent_skills" / "skills"
SHARED = REPO_ROOT / "mythril_agent_skills" / "shared" / "secrets"
sys.path.insert(0, str(SHARED))

import secret_guard  # noqa: E402

FAKE = "tok_FAKE_0123456789abcdef"


class TestSecretVariants:
    """Tests for secret_guard.secret_variants."""

    def test_includes_raw_and_url_encoded(self):
        variants = secret_guard.secret_variants("ab/cd+ef=gh")
        assert "ab/cd+ef=gh" in variants
        assert "ab%2Fcd%2Bef%3Dgh" in variants

    def test_short_values_ignored(self):
        assert secret_guard.secret_variants("short") == set()

    def test_strips_whitespace(self):
        assert FAKE in secret_guard.secret_variants(f"  {FAKE}\n")


class TestBasicAuthVariants:
    """Tests for secret_guard.basic_auth_variants."""

    def test_encodes_user_and_secret(self):
        expected = base64.b64encode(f"me@x.com:{FAKE}".encode()).decode()
        assert expected in secret_guard.basic_auth_variants("me@x.com", FAKE)

    def test_missing_user_returns_empty(self):
        assert secret_guard.basic_auth_variants("", FAKE) == set()


class TestRedactText:
    """Tests for secret_guard.redact_text."""

    def test_replaces_every_occurrence(self):
        text = f"Bearer {FAKE} and again {FAKE}"
        assert secret_guard.redact_text(text, {FAKE}) == (
            "Bearer [REDACTED] and again [REDACTED]"
        )

    def test_longest_secret_first(self):
        text = f"{FAKE}XYZ"
        out = secret_guard.redact_text(text, {FAKE, f"{FAKE}XYZ"})
        assert out == "[REDACTED]"

    def test_no_secrets_unchanged(self):
        assert secret_guard.redact_text("hello", set()) == "hello"


class TestFindLeaks:
    """Tests for secret_guard.find_leaks."""

    def test_detects_misordered_argument(self):
        named = {"method": "GET", "path": FAKE}
        assert secret_guard.find_leaks(named, {FAKE}) == ["path"]

    def test_detects_secret_inside_url(self):
        named = {"url": f"https://x/{FAKE}/y"}
        assert secret_guard.find_leaks(named, {FAKE}) == ["url"]

    def test_ignores_clean_and_non_string_args(self):
        named = {"path": "/users/me", "params": {"x": FAKE}, "n": 3}
        assert secret_guard.find_leaks(named, {FAKE}) == []


# Each consumer script: (skill, module, getter call, env vars to set).
CONSUMERS = [
    ("notion", "notion_api", "get_token()", {"NOTION_API_KEY": FAKE}),
    ("jira", "jira_api", "get_token()", {"ATLASSIAN_API_TOKEN": FAKE}),
    ("confluence", "confluence_api", "get_token()", {"ATLASSIAN_API_TOKEN": FAKE}),
    ("figma", "figma_fetch", "get_token()", {"FIGMA_ACCESS_TOKEN": FAKE}),
    ("figma", "figma_export", "get_token()", {"FIGMA_ACCESS_TOKEN": FAKE}),
    ("glm-vision-fallback", "vision_fallback", "get_api_key()", {"ZAI_API_KEY": FAKE}),
    (
        "jenkins",
        "jenkins_api",
        "get_env()[2]",
        {
            "JENKINS_URL": "https://ci.example.com",
            "JENKINS_USER": "bot",
            "JENKINS_API_TOKEN": FAKE,
        },
    ),
]


@pytest.mark.parametrize(
    "skill,module,getter,env", CONSUMERS, ids=[c[1] for c in CONSUMERS]
)
def test_consumer_never_prints_token(
    skill: str, module: str, getter: str, env: dict[str, str]
) -> None:
    """Printing the token or raising with it in the message must be redacted."""
    code = (
        f"import {module} as m\n"
        f"t = m.{getter}\n"
        "print('stdout', t, 'Bearer ' + t)\n"
        "print('stderr', t, file=__import__('sys').stderr)\n"
        "raise RuntimeError('boom ' + t)\n"
    )
    clean_env = {
        k: v
        for k, v in os.environ.items()
        if not any(s in k for s in ("TOKEN", "API_KEY", "JENKINS", "ATLASSIAN"))
    }
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=SKILLS_DIR / skill / "scripts",
        env={**clean_env, **env},
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout + result.stderr
    assert FAKE not in output
    assert "[REDACTED]" in result.stdout
    assert "boom [REDACTED]" in result.stderr


def test_notion_misordered_request_refused_without_echo() -> None:
    """Swapping path and token must fail before any request, without the value."""
    code = (
        "import notion_api as n\n"
        "t = n.get_token()\n"
        "n.notion_request('GET', t, '/users/me')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=SKILLS_DIR / "notion" / "scripts",
        env={**os.environ, "NOTION_API_KEY": FAKE},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "credential value was passed as argument(s) path" in result.stderr
    assert FAKE not in result.stdout + result.stderr
