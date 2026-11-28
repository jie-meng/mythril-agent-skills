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

    def test_url_with_view_id_in_query_uses_page_id(self):
        view_id = "41ab74688528809ea85c000cc3f0eb49"
        url = f"https://app.notion.com/p/Setup-Cloudinary-access-{HEX_ID}?v={view_id}&source=copy_link"
        assert self.parse(url) == HEX_ID

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


class TestAddTitleProperty:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import add_title_property

        self.fn = add_title_property

    SCHEMA = {"Name": "title", "Status": "status"}

    def test_sets_schema_title_property(self):
        out = self.fn({"Status": {"status": {"name": "Todo"}}}, self.SCHEMA, "Fix it")
        assert out["Name"] == {"title": [{"text": {"content": "Fix it"}}]}
        assert out["Status"] == {"status": {"name": "Todo"}}

    def test_explicit_property_wins(self):
        given = {"Name": {"title": [{"text": {"content": "Explicit"}}]}}
        assert self.fn(given, self.SCHEMA, "From flag") == given

    def test_no_title_or_no_title_property(self):
        assert self.fn({}, self.SCHEMA, "") == {}
        assert self.fn({}, {"Status": "status"}, "Fix it") == {}

    def test_custom_title_property_name(self):
        out = self.fn({}, {"Ticket": "title"}, "Fix it")
        assert list(out) == ["Ticket"]


class TestBuildCommentBody:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import MARKDOWN_VERSION, build_comment_body

        self.fn = build_comment_body
        self.version = MARKDOWN_VERSION

    def test_plain_comment(self):
        assert self.fn(HEX_ID, "Hi") == {
            "parent": {"page_id": HEX_ID},
            "markdown": "Hi",
            "markdown_version": self.version,
        }

    def test_custom_display_name(self):
        body = self.fn(HEX_ID, "Hi", "Alex")
        assert body["display_name"] == {"type": "custom", "custom": {"name": "Alex"}}


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

    def test_multi_select_splits_commas(self):
        assert self.fn("multi_select", "Bug, UI,") == {
            "multi_select": [{"name": "Bug"}, {"name": "UI"}]
        }

    def test_multi_select_empty_clears(self):
        assert self.fn("multi_select", "") == {"multi_select": []}

    def test_relation_accepts_ids_and_urls(self):
        url = "https://app.notion.com/p/Sprint-1-" + "a" * 32
        out = self.fn("relation", f"{'b' * 32}, {url}")
        assert out == {"relation": [{"id": "b" * 32}, {"id": "a" * 32}]}

    def test_relation_rejects_non_id(self):
        with pytest.raises(ValueError):
            self.fn("relation", "Sprint 1")

    def test_people(self):
        uid = "12345678-1234-1234-1234-123456789abc"
        assert self.fn("people", uid) == {
            "people": [{"object": "user", "id": uid.replace("-", "")}]
        }

    def test_people_rejects_name(self):
        with pytest.raises(ValueError):
            self.fn("people", "Alice")

    def test_title_email_phone(self):
        assert self.fn("title", "T") == {"title": [{"text": {"content": "T"}}]}
        assert self.fn("email", "a@b.co") == {"email": "a@b.co"}
        assert self.fn("phone_number", "+65 1") == {"phone_number": "+65 1"}


class TestExtractId:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import extract_id

        self.fn = extract_id

    def test_none_when_absent(self):
        assert self.fn("not an id") is None

    def test_ignores_view_query_param(self):
        url = f"https://app.notion.com/p/{'a' * 32}?v={'b' * 32}"
        assert self.fn(url) == "a" * 32


class TestParsePropertyArg:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import parse_property_arg

        self.fn = parse_property_arg

    def test_with_type(self):
        assert self.fn("Tags=Bug,UI:multi_select") == ("Tags", "Bug,UI", "multi_select")

    def test_without_type(self):
        assert self.fn("Status=In Progress") == ("Status", "In Progress", None)

    def test_colon_in_value_is_kept(self):
        assert self.fn("Link=https://x.com/a") == ("Link", "https://x.com/a", None)
        assert self.fn("Link=https://x.com:url") == ("Link", "https://x.com", "url")

    def test_value_may_contain_equals(self):
        assert self.fn("Expr=a=b:rich_text") == ("Expr", "a=b", "rich_text")

    def test_missing_equals(self):
        with pytest.raises(ValueError):
            self.fn("Status")

    def test_missing_name(self):
        with pytest.raises(ValueError):
            self.fn("=x")


class TestBuildProperties:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import build_properties, schema_property_types

        self.build = build_properties
        self.types = schema_property_types

    def test_schema_types_from_data_source_and_page(self):
        obj = {"properties": {"Status": {"type": "status"}, "Tags": {"type": "multi_select"}}}
        assert self.types(obj) == {"Status": "status", "Tags": "multi_select"}

    def test_resolves_type_from_schema(self):
        out = self.build(
            [("Status", "Todo", None), ("Tags", "Bug", None)],
            {"Status": "status", "Tags": "multi_select"},
        )
        assert out == {
            "Status": {"status": {"name": "Todo"}},
            "Tags": {"multi_select": [{"name": "Bug"}]},
        }

    def test_explicit_type_wins(self):
        out = self.build([("Epic", "Auth", "select")], {"Epic": "rich_text"})
        assert out == {"Epic": {"select": {"name": "Auth"}}}

    def test_unknown_property(self):
        with pytest.raises(ValueError, match="Known: Status"):
            self.build([("Nope", "x", None)], {"Status": "status"})

    def test_unsupported_schema_type(self):
        with pytest.raises(ValueError, match="unsupported"):
            self.build([("F", "x", None)], {"F": "formula"})


class TestFormatSchema:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import format_schema

        self.fmt = format_schema

    def test_empty(self):
        assert "No properties" in self.fmt({})

    def test_rows(self):
        out = self.fmt(
            {
                "title": [{"plain_text": "Board"}],
                "properties": {
                    "Status": {
                        "type": "status",
                        "status": {"options": [{"name": "Todo"}, {"name": "Done"}]},
                    },
                    "Sprint": {"type": "relation", "relation": {"data_source_id": "ds9"}},
                    "Assign": {"type": "people", "people": {}},
                },
            }
        )
        assert "Board" in out
        assert "| Status | status | Todo, Done |" in out
        assert "| Sprint | relation | ds9 |" in out
        assert "| Assign | people |  |" in out


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


class TestFormatPageProperties:
    @pytest.fixture(autouse=True)
    def _import(self):
        from notion_api import format_page_markdown, format_property_value

        self.fmt = format_page_markdown
        self.val = format_property_value

    def test_values(self):
        assert self.val({"type": "status", "status": {"name": "Todo"}}) == "Todo"
        assert self.val({"type": "multi_select", "multi_select": [{"name": "A"}, {"name": "B"}]}) == "A, B"
        assert self.val({"type": "relation", "relation": [{"id": "r1"}]}) == "r1"
        assert self.val({"type": "people", "people": [{"id": "u1", "name": "Ann"}, {"id": "u2"}]}) == "Ann (u1), u2"
        assert self.val({"type": "date", "date": {"start": "2026-01-01", "end": "2026-01-02"}}) == "2026-01-01 → 2026-01-02"
        assert self.val({"type": "select", "select": None}) == ""
        assert self.val({"type": "number", "number": 3}) == "3"
        assert self.val({"type": "formula", "formula": {"type": "string", "string": "x"}}) == "x"

    def test_page_shows_parent_and_properties(self):
        page = {
            "id": "p1",
            "parent": {"type": "data_source_id", "data_source_id": "ds1"},
            "properties": {
                "Name": {"type": "title", "title": [{"plain_text": "Card"}]},
                "Status": {"type": "status", "status": {"name": "Todo"}},
                "Notes": {"type": "rich_text", "rich_text": [{"plain_text": "a|b"}]},
            },
        }
        out = self.fmt(page, {"markdown": "body"})
        assert "- **Parent**: data_source_id: ds1" in out
        assert "| Status | status | Todo |" in out
        assert "a\\|b" in out
        assert "| Name |" not in out


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


class TestPeekUrl:
    """A page opened in peek mode keeps the database id in the path."""

    def test_p_query_param_wins(self):
        from notion_api import extract_id
        url = (
            "https://www.notion.so/ws/" + "a" * 32 + "?v=" + "b" * 32
            + "&p=" + "c" * 32 + "&pm=s"
        )
        assert extract_id(url) == "c" * 32

    def test_dashed_p_param(self):
        from notion_api import extract_id
        dashed = "12345678-1234-1234-1234-123456789abc"
        url = "https://www.notion.so/ws/" + "a" * 32 + "?p=" + dashed
        assert extract_id(url) == dashed.replace("-", "")

    def test_invalid_p_param_ignored(self):
        from notion_api import extract_id
        url = "https://www.notion.so/ws/Page-" + "a" * 32 + "?p=nope"
        assert extract_id(url) == "a" * 32


class TestItemMarkdown:
    def test_no_h1_when_title_property_set(self):
        from notion_api import item_markdown
        props = {"Name": {"title": [{"text": {"content": "Fix"}}]}}
        assert item_markdown("Fix", "body", props, {"Name": "title"}) == "body"

    def test_h1_when_no_title_property(self):
        from notion_api import item_markdown
        assert item_markdown("Fix", "body", {}, {}) == "# Fix\n\nbody"


class TestReadMarkdownArg:
    def test_inline_markdown(self):
        from notion_api import read_markdown_arg
        assert read_markdown_arg("## A", None) == "## A"
        assert read_markdown_arg(None, None) == ""

    def test_file_keeps_real_newlines(self, tmp_path):
        from notion_api import read_markdown_arg
        f = tmp_path / "doc.md"
        f.write_text("## Overview\n\nDetails\n", encoding="utf-8")
        assert read_markdown_arg("", str(f)) == "## Overview\n\nDetails\n"

    def test_both_given_is_error(self, tmp_path):
        from notion_api import read_markdown_arg
        with pytest.raises(ValueError):
            read_markdown_arg("x", str(tmp_path / "a.md"))

    def test_missing_file_is_error(self, tmp_path):
        from notion_api import read_markdown_arg
        with pytest.raises(ValueError, match="cannot read"):
            read_markdown_arg("", str(tmp_path / "missing.md"))
