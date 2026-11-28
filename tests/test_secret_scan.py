"""Tests for the shared secret_scan gate (fullstack-brief, fullstack-issue-create).

Fake secrets are assembled at runtime so this file itself never holds a
literal that looks like a real credential.
"""

from __future__ import annotations

import random
import string
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED = REPO_ROOT / "mythril_agent_skills" / "shared" / "secrets"
SKILLS_DIR = REPO_ROOT / "mythril_agent_skills" / "skills"
sys.path.insert(0, str(SHARED))

import secret_scan  # noqa: E402

CONSUMERS = ("fullstack-brief", "fullstack-issue-create")

_rng = random.Random(1234)


def _rand(n: int, alphabet: str = string.ascii_letters + string.digits) -> str:
    return "".join(_rng.choice(alphabet) for _ in range(n))


GH = "gh" + "p_" + _rand(36)
AWS = "AK" + "IA" + _rand(16, string.ascii_uppercase + string.digits)
ANT = "sk-" + "ant-" + _rand(40)
JWT = "ey" + "J" + _rand(20) + ".ey" + "J" + _rand(20) + "." + _rand(20)


def _rules(text: str) -> list[str]:
    return [f.rule for f in secret_scan.scan_text(text)]


class TestScanText:
    """Tests for secret_scan.scan_text."""

    @pytest.mark.parametrize(
        ("text", "rule"),
        [
            (f"token used: {GH}", "github-token"),
            (f"aws id {AWS} here", "aws-access-key-id"),
            (f"key={ANT}", "anthropic-key"),
            (f"cookie {JWT}", "jwt"),
            ("-----BEGIN RSA " + "PRIVATE KEY-----", "private-key"),
            ("Authorization: Bearer " + _rand(30), "authorization-header"),
            ("postgres://admin:" + _rand(12) + "@db.internal:5432/app", "url-credentials"),
            ("DB_PASSWORD=" + _rand(14), "credential-assignment"),
            ('"client_secret": "' + _rand(24) + '"', "credential-assignment"),
        ],
    )
    def test_detects(self, text: str, rule: str):
        assert rule in _rules(text)

    def test_high_entropy_blob_without_prefix(self):
        assert _rules("blob " + _rand(48)) == ["high-entropy-string"]

    def test_one_finding_per_value(self):
        assert _rules(f"key={ANT}") == ["anthropic-key"]

    @pytest.mark.parametrize(
        "text",
        [
            "commit 3f2c1e9a0b8d7c6e5f4a3b2c1d0e9f8a7b6c5d4e",  # git SHA
            "path mythril_agent_skills/skills/fullstack-init/scripts/workspace_init.py",
            "password=<your-password>",
            "API_KEY=${API_KEY}",
            "secret: xxxxxxxx",
            "password: [REDACTED]",
            "`.env` defines `DATABASE_URL`, `REDIS_URL`",
            "testUserCanLoginWithValidCredentialsAndRememberMe",
            "2026-10-11 14:30:01 ERROR brownout during 4G burst, vbat=3.31V",
        ],
    )
    def test_ignores_non_secrets(self, text: str):
        assert _rules(text) == []

    def test_allow_marker_skips_line(self):
        assert _rules(f"{GH}  <!-- secret-scan: allow -->") == []

    def test_reports_line_numbers(self):
        findings = secret_scan.scan_text(f"ok\nok\nleak {GH}\n")
        assert [f.line for f in findings] == [3]


class TestMask:
    """Findings must identify a value without revealing it."""

    def test_mask_hides_value(self):
        masked = secret_scan.mask(GH)
        assert GH not in masked
        assert masked.startswith(GH[:4])
        assert f"[{len(GH)} chars]" in masked

    def test_short_values_show_no_prefix(self):
        assert secret_scan.mask("abcdefg") == "…[7 chars]"

    def test_excerpt_never_contains_secret(self):
        for finding in secret_scan.scan_text(f"a {GH} b {ANT} c {JWT}"):
            assert GH not in finding.excerpt
            assert ANT not in finding.excerpt


class TestShannonEntropy:
    def test_uniform_is_zero(self):
        assert secret_scan.shannon_entropy("aaaa") == 0.0

    def test_empty_is_zero(self):
        assert secret_scan.shannon_entropy("") == 0.0

    def test_two_symbols_is_one_bit(self):
        assert secret_scan.shannon_entropy("abab") == pytest.approx(1.0)


class TestCli:
    """Exit codes and output of the bundled copies."""

    @pytest.fixture(params=CONSUMERS)
    def script(self, request) -> Path:
        return SKILLS_DIR / request.param / "scripts" / "secret_scan.py"

    def _run(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *args], capture_output=True, text=True
        )

    def test_clean_dir_passes(self, script: Path, tmp_path: Path):
        (tmp_path / "README.md").write_text("# Issue\n\nNo secrets.\n")
        result = self._run(script, str(tmp_path))
        assert result.returncode == 0
        assert "STATUS=PASS" in result.stdout

    def test_finding_fails_without_echoing_secret(self, script: Path, tmp_path: Path):
        log = tmp_path / "log"
        log.mkdir()
        (log / "capture.log").write_text(f"boot ok\nAuthorization: Bearer {GH}\n")
        result = self._run(script, str(tmp_path))
        assert result.returncode == 1
        assert "STATUS=FAIL" in result.stdout
        assert "capture.log:2" in result.stdout
        assert GH not in result.stdout + result.stderr

    def test_binary_file_skipped(self, script: Path, tmp_path: Path):
        (tmp_path / "dump.bin").write_bytes(b"\0\1\2" + GH.encode())
        result = self._run(script, str(tmp_path))
        assert result.returncode == 0
        assert "SKIPPED=" in result.stdout

    def test_missing_path_is_usage_error(self, script: Path, tmp_path: Path):
        assert self._run(script, str(tmp_path / "nope")).returncode == 2

    def test_no_args_is_usage_error(self, script: Path):
        assert self._run(script).returncode == 2


@pytest.mark.parametrize("skill", CONSUMERS)
def test_consumer_skill_runs_the_gate(skill: str):
    """Each consumer's SKILL.md must invoke its bundled scanner as a gate."""
    text = (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "SKILL_PATH/scripts/secret_scan.py" in text
    assert "STATUS=FAIL" in text
