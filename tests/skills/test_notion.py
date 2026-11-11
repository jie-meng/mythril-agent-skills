"""Tests for notion skill scripts.

Covers pure helpers and formatters only (no API/network calls):
- parse_page_input: bare IDs, UUIDs, full Notion URLs
- build_headers, with_title, build_property_value
- formatters: page markdown, search, query, data sources, comments, user, check
- token link constant and missing-token guidance
- skills_check.check_notion: token-set and token-missing branches
"""

from __future__ import annotations

from pathlib import Path

import pytest

TOKEN_URL = "https://www.notion.so/developers/tokens"
HEX_ID = "1234567890abcdef1234567890abcdef"
UUID_ID = "12345678-90ab-cdef-1234-567890abcdef"


class TestParsePageInput:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import parse_page_input

        self.parse = parse_page_input

    def test_bare_hex_id(self):
        assert self.parse(HEX_ID) == HEX_ID

    def test_bare_uuid_is_normalized(self):
        assert self.parse(UUID_ID) == HEX_ID

    def test_notion_so_url(self):
        assert self.parse(f"https://www.notion.so/My-Page-{HEX_ID}") == HEX_ID

    def test_notion_so_url_with_query(self):
        assert self.parse(f"https://www.notion.so/My-Page-{HEX_ID}?pvs=4") == HEX_ID

    def test_app_notion_url(self):
        assert self.parse(f"https://app.notion.com/p/{UUID_ID}") == HEX_ID

    def test_invalid_input_exits(self, capsys):
        with pytest.raises(SystemExit):
            self.parse("not-an-id")
        assert "cannot find a Notion ID" in capsys.readouterr().err


class TestBuildHeaders:
    def test_three_headers_and_pinned_version(self):
        from notion_api import API_VERSION, build_headers

        headers = build_headers("abc")
        assert headers["Authorization"] == "Bearer abc"
        assert headers["Notion-Version"] == API_VERSION == "2026-03-11"
        assert headers["Content-Type"] == "application/json"


class TestTokenGuidance:
    def test_token_url_is_official(self):
        from notion_api import TOKEN_HELP, TOKEN_URL

        assert TOKEN_URL == "https://www.notion.so/developers/tokens"
        assert TOKEN_URL in TOKEN_HELP
        assert "NOTION_API_KEY" in TOKEN_HELP

    def test_get_token_missing_prints_link(self, monkeypatch, capsys):
        import notion_api

        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        with pytest.raises(SystemExit):
            notion_api.get_token()
        err = capsys.readouterr().err
        assert "NOTION_API_KEY not set" in err
        assert "https://www.notion.so/developers/tokens" in err

    def test_get_token_never_returns_empty(self, monkeypatch):
        import notion_api

        monkeypatch.setenv("NOTION_API_KEY", "placeholder-value")
        assert notion_api.get_token() == "placeholder-value"


class TestWithTitle:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import with_title

        self.fn = with_title

    def test_prepends_h1(self):
        assert self.fn("Title", "Body") == "# Title\n\nBody"

    def test_keeps_existing_h1(self):
        assert self.fn("Ignored", "# Real\n\nBody") == "# Real\n\nBody"

    def test_no_title(self):
        assert self.fn("", "Body") == "Body"


class TestBuildPropertyValue:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import build_property_value

        self.fn = build_property_value

    def test_select(self):
        assert self.fn("select", "Done") == {"select": {"name": "Done"}}

    def test_status(self):
        assert self.fn("status", "In Progress") == {"status": {"name": "In Progress"}}

    def test_rich_text(self):
        assert self.fn("rich_text", "note") == {
            "rich_text": [{"text": {"content": "note"}}]
        }

    def test_checkbox_true_and_false(self):
        assert self.fn("checkbox", "true") == {"checkbox": True}
        assert self.fn("checkbox", "no") == {"checkbox": False}

    def test_number(self):
        assert self.fn("number", "3.5") == {"number": 3.5}

    def test_url_and_date(self):
        assert self.fn("url", "https://example.com") == {"url": "https://example.com"}
        assert self.fn("date", "2026-11-11") == {"date": {"start": "2026-11-11"}}

    def test_unsupported_type(self):
        with pytest.raises(ValueError):
            self.fn("unknown", "x")


class TestFormatPageMarkdown:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import format_page_markdown

        self.fmt = format_page_markdown

    def _page(self):
        return {
            "id": "p1",
            "url": "https://notion.so/p1",
            "created_time": "2026-01-01T00:00:00Z",
            "last_edited_time": "2026-01-02T00:00:00Z",
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "My Page"}],
                }
            },
        }

    def test_basic(self):
        md = {
            "markdown": "# My Page\n\nHello",
            "truncated": False,
            "unknown_block_ids": [],
            "warnings": [],
        }
        out = self.fmt(self._page(), md)
        assert "## My Page" in out
        assert "Hello" in out
        assert "https://notion.so/p1" in out
        assert "### Content" in out

    def test_truncated_unknown_and_warnings(self):
        md = {
            "markdown": "x",
            "truncated": True,
            "unknown_block_ids": ["b1"],
            "warnings": [{"code": "deprecated_tag", "message": "old tag"}],
        }
        out = self.fmt({}, md)
        assert "truncated" in out
        assert "1 block(s)" in out
        assert "deprecated_tag" in out
        assert "(untitled)" in out


class TestFormatSearchResults:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import format_search_results

        self.fmt = format_search_results

    def test_empty(self):
        assert "No results found" in self.fmt({"results": []})

    def test_rows_and_cursor_note(self):
        data = {
            "results": [
                {
                    "object": "page",
                    "id": "p1",
                    "url": "u1",
                    "properties": {
                        "Name": {"type": "title", "title": [{"plain_text": "Doc"}]}
                    },
                }
            ],
            "has_more": True,
            "next_cursor": "cur1",
        }
        out = self.fmt(data)
        assert "Doc" in out
        assert "cur1" in out
        assert "More results available" in out


class TestFormatQueryResults:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import format_query_results

        self.fmt = format_query_results

    def test_empty(self):
        assert "No items found" in self.fmt({"results": []})

    def test_rows(self):
        out = self.fmt(
            {
                "results": [
                    {
                        "id": "i1",
                        "url": "u1",
                        "properties": {
                            "Name": {
                                "type": "title",
                                "title": [{"text": {"content": "Fix login"}}],
                            }
                        },
                    }
                ]
            }
        )
        assert "Fix login" in out
        assert "i1" in out


class TestFormatDataSources:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import format_data_sources

        self.fmt = format_data_sources

    def test_empty(self):
        assert "No data sources found" in self.fmt({"data_sources": []})

    def test_rows(self):
        out = self.fmt(
            {"data_sources": [{"id": "ds1", "name": "Tasks"}, {"id": "ds2"}]}
        )
        assert "Tasks" in out
        assert "ds1" in out
        assert "(unnamed)" in out


class TestFormatComments:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import format_comments

        self.fmt = format_comments

    def test_empty(self):
        assert "No comments" in self.fmt([])

    def test_rows(self):
        out = self.fmt(
            [
                {
                    "created_by": {"id": "u1"},
                    "created_time": "2026-01-01",
                    "rich_text": [{"plain_text": "Looks good!"}],
                }
            ]
        )
        assert "Looks good!" in out
        assert "u1" in out


class TestFormatUserAndCheck:
    def test_no_details(self):
        from notion_api import format_user

        assert format_user({}) == "(no user details returned)"

    def test_fields(self):
        from notion_api import format_user

        out = format_user({"name": "Ada", "id": "u1", "type": "person"})
        assert "Name: Ada" in out
        assert "ID: u1" in out

    def test_check_result_has_version_and_token_env(self):
        from notion_api import format_check_result

        out = format_check_result({"name": "Ada"})
        assert "OK:" in out
        assert "2026-03-11" in out
        assert "NOTION_API_KEY" in out
        assert "Ada" in out


class TestSkillsCheckNotion:
    def test_registered_and_token_set_branch(self, monkeypatch, capsys):
        monkeypatch.setenv("NOTION_API_KEY", "placeholder-token-1234")
        from mythril_agent_skills.cli import skills_check

        assert skills_check.SKILL_NOTION == "notion"
        assert skills_check.SKILL_NOTION in skills_check.CHECKABLE_SKILLS
        assert skills_check.check_notion(Path("/tmp/unused")) is True
        assert "NOTION_API_KEY" in capsys.readouterr().out

    def test_missing_token_prints_official_link(self, monkeypatch, capsys):
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        from mythril_agent_skills.cli import skills_check

        monkeypatch.setattr(skills_check, "_prompt_value", lambda *a, **k: None)
        assert skills_check.check_notion(Path("/tmp/unused")) is False
        out = capsys.readouterr().out
        assert "https://www.notion.so/developers/tokens" in out
        assert "New token" in out
        assert "Notion API" in out
