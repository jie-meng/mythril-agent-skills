"""Tests for jenkins skill scripts.

Covers pure helpers and formatters only (no API/network calls):
- job_path: bare names, folder nesting, quoting, invalid segments
- build_url_path: build number / lastBuild suffix
- get_env: full, partial, and missing environment
- formatters: duration, timestamp, color status, jobs/job/build/stages markdown
- parse_params and parameter_names
- exit-code mapping
- skills_check.check_jenkins: env-set and env-missing branches
"""

from __future__ import annotations

from pathlib import Path

import pytest

TOKEN_URL = "https://www.jenkins.io/doc/book/managing/security/#api-tokens"


class TestJobPath:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jenkins_api import job_path

        self.fn = job_path

    def test_bare_name(self):
        assert self.fn("deploy") == "/job/deploy"

    def test_folder_nesting(self):
        assert self.fn("team/services/deploy") == "/job/team/job/services/job/deploy"

    def test_quotes_spaces(self):
        assert self.fn("my job") == "/job/my%20job"

    def test_strips_whitespace(self):
        assert self.fn(" deploy ") == "/job/deploy"

    def test_empty_name_exits(self, capsys):
        with pytest.raises(SystemExit):
            self.fn("")
        assert "Empty job name" in capsys.readouterr().err

    def test_dot_dot_segment_exits(self, capsys):
        with pytest.raises(SystemExit):
            self.fn("a/../../b")
        assert "Invalid job path segment" in capsys.readouterr().err


class TestBuildUrlPath:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jenkins_api import build_url_path

        self.fn = build_url_path

    def test_build_number(self):
        assert self.fn("deploy", 42) == "/job/deploy/42"

    def test_last_build_default(self):
        assert self.fn("deploy", None) == "/job/deploy/lastBuild"

    def test_folder_with_build(self):
        assert self.fn("team/deploy", 7) == "/job/team/job/deploy/7"


class TestGetEnv:
    def test_all_set(self, monkeypatch):
        import jenkins_api

        monkeypatch.setenv("JENKINS_URL", "https://ci.example.com:8443/")
        monkeypatch.setenv("JENKINS_USER", "alice")
        monkeypatch.setenv("JENKINS_API_TOKEN", "token-1234")
        base_url, user, token = jenkins_api.get_env()
        assert base_url == "https://ci.example.com:8443"  # trailing slash stripped
        assert user == "alice"
        assert token == "token-1234"

    def test_missing_vars_reported(self, monkeypatch, capsys):
        import jenkins_api

        for var in ("JENKINS_URL", "JENKINS_USER", "JENKINS_API_TOKEN"):
            monkeypatch.delenv(var, raising=False)
        with pytest.raises(SystemExit):
            jenkins_api.get_env()
        err = capsys.readouterr().err
        assert "JENKINS_URL" in err
        assert "JENKINS_USER" in err
        assert "JENKINS_API_TOKEN" in err

    def test_missing_one_var_named(self, monkeypatch, capsys):
        import jenkins_api

        monkeypatch.setenv("JENKINS_URL", "https://ci.example.com")
        monkeypatch.setenv("JENKINS_USER", "alice")
        monkeypatch.delenv("JENKINS_API_TOKEN", raising=False)
        with pytest.raises(SystemExit):
            jenkins_api.get_env()
        err = capsys.readouterr().err
        assert "variable(s): JENKINS_API_TOKEN" in err


class TestTokenGuidance:
    def test_token_url_is_official(self):
        from jenkins_api import TOKEN_HELP, TOKEN_URL

        assert TOKEN_URL == "https://www.jenkins.io/doc/book/managing/security/#api-tokens"
        assert TOKEN_URL in TOKEN_HELP
        assert "JENKINS_API_TOKEN" in TOKEN_HELP
        assert "Add new Token" in TOKEN_HELP


class TestSSLErrorGuidance:
    def test_cert_failure_prints_ca_guidance(self, monkeypatch, capsys):
        import ssl

        import jenkins_api

        def _raise(req, timeout=None, context=None):
            raise ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED: boom")

        monkeypatch.setattr(jenkins_api.urllib.request, "urlopen", _raise)
        monkeypatch.setenv("JENKINS_URL", "https://ci.example.com")
        monkeypatch.setenv("JENKINS_USER", "alice")
        monkeypatch.setenv("JENKINS_API_TOKEN", "token-1234")
        with pytest.raises(SystemExit):
            jenkins_api._request("GET", "https://ci.example.com/api/json")
        err = capsys.readouterr().err
        assert "TLS verification failed" in err
        assert "SSL_CERT_FILE" in err
        assert "SSL_NO_VERIFY" in err


class TestFormatters:
    def test_format_duration(self):
        from jenkins_api import format_duration

        assert format_duration(None) == "-"
        assert format_duration(45000) == "45s"
        assert format_duration(204000) == "3m 24s"
        assert format_duration(7500000) == "2h 05m"
        assert format_duration(108000000) == "1d 6h"

    def test_format_timestamp(self):
        from jenkins_api import format_timestamp

        assert format_timestamp(None) == "-"
        out = format_timestamp(1760000000000)  # 2025-10-09, epoch sanity
        assert out.startswith("2025-")

    def test_color_to_status(self):
        from jenkins_api import color_to_status

        assert color_to_status("blue") == "SUCCESS"
        assert color_to_status("red") == "FAILURE"
        assert color_to_status("yellow") == "UNSTABLE"
        assert color_to_status("aborted") == "ABORTED"
        assert color_to_status("notbuilt") == "NOT BUILT"
        assert color_to_status("disabled") == "DISABLED"
        assert color_to_status("blue_anime") == "SUCCESS (running)"
        assert color_to_status("red_anime") == "FAILURE (running)"
        assert color_to_status(None) == "NEVER BUILT"
        assert color_to_status("weird") == "WEIRD"

    def test_result_exit_codes(self):
        from jenkins_api import RESULT_EXIT_CODES

        assert RESULT_EXIT_CODES == {
            "SUCCESS": 0,
            "FAILURE": 1,
            "UNSTABLE": 2,
            "ABORTED": 3,
            "NOT_BUILT": 4,
        }


class TestParseParams:
    def test_basic(self):
        from jenkins_api import parse_params

        assert parse_params(["SERVER_VERSION=latest", "TARGET=a,b"]) == {
            "SERVER_VERSION": "latest",
            "TARGET": "a,b",
        }

    def test_value_may_contain_equals(self):
        from jenkins_api import parse_params

        assert parse_params(["TOKEN=a=b"]) == {"TOKEN": "a=b"}

    def test_none_and_empty(self):
        from jenkins_api import parse_params

        assert parse_params(None) == {}
        assert parse_params([]) == {}

    def test_missing_equals_exits(self, capsys):
        from jenkins_api import parse_params

        with pytest.raises(SystemExit):
            parse_params(["oops"])
        assert "name=value" in capsys.readouterr().err


class TestParameterNames:
    def test_extracts_from_property(self):
        from jenkins_api import parameter_names

        info = {
            "property": [
                {"_class": "hudson.model.JobProperty"},
                {
                    "_class": "hudson.model.ParametersDefinitionProperty",
                    "parameterDefinitions": [{"name": "V1"}, {"name": "V2"}],
                },
            ]
        }
        assert parameter_names(info) == ["V1", "V2"]

    def test_no_parameters(self):
        from jenkins_api import parameter_names

        assert parameter_names({"property": []}) == []
        assert parameter_names({}) == []


class TestFormatJobsMarkdown:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jenkins_api import format_jobs_markdown

        self.fmt = format_jobs_markdown

    def test_empty(self):
        assert "No jobs found" in self.fmt({"jobs": []}, None)

    def test_rows(self):
        data = {
            "jobs": [
                {"name": "build", "color": "blue", "lastBuild": {"number": 5, "result": "SUCCESS"}},
                {"name": "deploy", "color": "red_anime", "lastBuild": {"number": 9}},
                {"name": "never", "color": None, "lastBuild": None},
            ]
        }
        out = self.fmt(data, None)
        assert "#5 SUCCESS" in out
        assert "FAILURE (running)" in out
        assert "NEVER BUILT" in out
        assert "| deploy |" in out

    def test_folder_label(self):
        out = self.fmt({"jobs": []}, "team/services")
        assert "team/services" in out


class TestFormatJobMarkdown:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jenkins_api import format_job_markdown

        self.fmt = format_job_markdown

    def _info(self):
        return {
            "displayName": "deploy-dev",
            "color": "blue",
            "inQueue": False,
            "url": "https://ci.example.com/job/deploy-dev/",
            "lastBuild": {"number": 9, "result": "SUCCESS"},
            "healthReport": [{"score": 90, "description": "No recent failures"}],
            "property": [
                {
                    "_class": "hudson.model.ParametersDefinitionProperty",
                    "parameterDefinitions": [
                        {
                            "name": "SERVER_VERSION",
                            "type": "StringParameterDefinition",
                            "defaultParameterValue": {"value": "latest"},
                            "description": "Image tag",
                        }
                    ],
                }
            ],
        }

    def test_full(self):
        out = self.fmt(self._info())
        assert "## deploy-dev" in out
        assert "SUCCESS" in out
        assert "90/100" in out
        assert "#9" in out
        assert "SERVER_VERSION" in out
        assert "latest" in out

    def test_minimal(self):
        out = self.fmt({"displayName": "x"})
        assert "## x" in out
        assert "NEVER BUILT" in out


class TestFormatBuildMarkdown:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jenkins_api import format_build_markdown

        self.fmt = format_build_markdown

    def test_finished_with_params(self):
        build = {
            "number": 42,
            "building": False,
            "result": "SUCCESS",
            "timestamp": 1760000000000,
            "duration": 204000,
            "url": "https://ci.example.com/job/deploy/42/",
            "actions": [
                {"_class": "hudson.model.ParametersAction", "parameters": [{"name": "V", "value": "latest"}]}
            ],
        }
        out = self.fmt(build, job="deploy")
        assert "#42 — SUCCESS" in out
        assert "SUCCESS" in out
        assert "3m 24s" in out
        assert "V = latest" in out

    def test_running(self):
        build = {"number": 7, "building": True, "result": None}
        out = self.fmt(build, job="deploy")
        assert "BUILDING" in out
        assert "IN PROGRESS" in out


class TestFormatStagesMarkdown:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jenkins_api import format_stages_markdown

        self.fmt = format_stages_markdown

    def test_empty(self):
        out = self.fmt({"stages": []}, "deploy", 3)
        assert "may not be a Pipeline" in out

    def test_rows(self):
        data = {
            "stages": [
                {"name": "Build", "status": "SUCCESS", "durationMillis": 45000},
                {"name": "Deploy", "status": "IN_PROGRESS", "durationMillis": 1000},
                {"name": "Skipped step", "status": "SKIPPED", "durationMillis": 0},
            ]
        }
        out = self.fmt(data, "deploy", 3)
        assert "IN PROGRESS" in out
        assert "45s" in out
        assert "Build" in out
        assert "Deploy" in out


class TestSkillsCheckJenkins:
    def test_registered(self):
        from mythril_agent_skills.cli import skills_check

        assert skills_check.SKILL_JENKINS == "jenkins"
        assert skills_check.SKILL_JENKINS in skills_check.CHECKABLE_SKILLS

    def test_env_set_branch(self, monkeypatch, capsys):
        monkeypatch.setenv("JENKINS_URL", "https://ci.example.com:8443")
        monkeypatch.setenv("JENKINS_USER", "alice")
        monkeypatch.setenv("JENKINS_API_TOKEN", "placeholder-token-1234")
        from mythril_agent_skills.cli import skills_check

        assert skills_check.check_jenkins(Path("/tmp/unused")) is True
        out = capsys.readouterr().out
        assert "JENKINS_API_TOKEN" in out
        assert "JENKINS_URL" in out

    def test_missing_token_prints_official_link(self, monkeypatch, capsys):
        for var in ("JENKINS_URL", "JENKINS_USER", "JENKINS_API_TOKEN"):
            monkeypatch.delenv(var, raising=False)
        from mythril_agent_skills.cli import skills_check

        monkeypatch.setattr(skills_check, "_prompt_value", lambda *a, **k: None)
        assert skills_check.check_jenkins(Path("/tmp/unused")) is False
        out = capsys.readouterr().out
        assert TOKEN_URL in out
        assert "Add new Token" in out
