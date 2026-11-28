"""Tests for jira skill scripts.

Covers pure formatter functions (no API/network calls):
- format_adf_to_text: Atlassian Document Format → plain text
- format_issue_markdown: issue JSON → markdown
- format_search_results_markdown: search response → markdown table
- parse_issue_input: URL parsing (URL branch only)
- _auth_header: Basic auth header construction
"""

from __future__ import annotations

import base64

import pytest


class TestFormatAdfToText:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jira_api import format_adf_to_text
        self.fmt = format_adf_to_text

    def test_none_returns_empty(self):
        assert self.fmt(None) == ""

    def test_plain_string(self):
        assert self.fmt("hello") == "hello"

    def test_text_node(self):
        node = {"type": "text", "text": "Hello world"}
        assert self.fmt(node) == "Hello world"

    def test_paragraph(self):
        node = {
            "type": "paragraph",
            "content": [{"type": "text", "text": "Line one"}],
        }
        assert self.fmt(node).strip() == "Line one"

    def test_heading(self):
        node = {
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Title"}],
        }
        result = self.fmt(node)
        assert result.startswith("## ")
        assert "Title" in result

    def test_bullet_list(self):
        node = {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Item A"}],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Item B"}],
                        }
                    ],
                },
            ],
        }
        result = self.fmt(node)
        assert "- Item A" in result
        assert "- Item B" in result

    def test_ordered_list(self):
        node = {
            "type": "orderedList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "First"}],
                        }
                    ],
                },
            ],
        }
        result = self.fmt(node)
        assert "1. First" in result

    def test_code_block(self):
        node = {
            "type": "codeBlock",
            "attrs": {"language": "python"},
            "content": [{"type": "text", "text": "print('hi')"}],
        }
        result = self.fmt(node)
        assert "```python" in result
        assert "print('hi')\n```" in result

    def test_link_mark_keeps_url(self):
        node = {"type": "paragraph", "content": [
            {"type": "text", "text": "see PR",
             "marks": [{"type": "link", "attrs": {"href": "https://gh/pr/1"}}]},
        ]}
        assert self.fmt(node) == "[see PR](https://gh/pr/1)\n"

    def test_link_mark_equal_to_text_not_duplicated(self):
        node = {"type": "text", "text": "https://x.io",
                "marks": [{"type": "link", "attrs": {"href": "https://x.io"}}]}
        assert self.fmt(node) == "https://x.io"

    def test_inline_and_block_cards_keep_url(self):
        node = {"type": "paragraph", "content": [
            {"type": "text", "text": "design: "},
            {"type": "inlineCard", "attrs": {"url": "https://figma.com/x"}},
        ]}
        assert "design: https://figma.com/x" in self.fmt(node)
        assert self.fmt({"type": "blockCard", "attrs": {"url": "https://a.b"}}) == "https://a.b\n"

    def test_code_and_strong_marks(self):
        node = {"type": "text", "text": "x", "marks": [{"type": "code"}]}
        assert self.fmt(node) == "`x`"
        node = {"type": "text", "text": "b", "marks": [{"type": "strong"}]}
        assert self.fmt(node) == "**b**"

    def test_media_with_alt_is_attachment_reference(self):
        node = {"type": "mediaSingle", "content": [
            {"type": "media", "attrs": {"id": "abc", "type": "file", "alt": "shot.png"}},
        ]}
        assert self.fmt(node) == "![shot.png](attachment:shot.png)\n"

    def test_media_group_lists_every_item(self):
        node = {"type": "mediaGroup", "content": [
            {"type": "media", "attrs": {"id": "a"}},
            {"type": "media", "attrs": {"id": "b"}},
        ]}
        assert self.fmt(node) == "[media: a]\n[media: b]\n"

    def test_status_emoji_date(self):
        assert self.fmt({"type": "status", "attrs": {"text": "DONE"}}) == "[DONE]"
        assert self.fmt({"type": "emoji", "attrs": {"shortName": ":x:", "text": "X"}}) == "X"
        assert self.fmt({"type": "date", "attrs": {"timestamp": "86400000"}}) == "1970-01-02"

    def test_mention(self):
        node = {"type": "mention", "attrs": {"text": "john"}}
        assert self.fmt(node) == "@john"

    def test_hard_break(self):
        assert self.fmt({"type": "hardBreak"}) == "\n"

    def test_list_of_nodes(self):
        nodes = [
            {"type": "text", "text": "A"},
            {"type": "text", "text": "B"},
        ]
        assert self.fmt(nodes) == "AB"


class TestFormatIssueMarkdown:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jira_api import format_issue_markdown
        self.fmt = format_issue_markdown

    def _issue(self, **overrides) -> dict:
        base = {
            "key": "PROJ-123",
            "self": "https://mysite.atlassian.net/rest/api/3/issue/10001",
            "fields": {
                "summary": "Fix login bug",
                "status": {"name": "In Progress"},
                "priority": {"name": "High"},
                "issuetype": {"name": "Bug"},
                "assignee": {"displayName": "Alice"},
                "reporter": {"displayName": "Bob"},
                "labels": ["backend"],
                "components": [{"name": "auth"}],
                "fixVersions": [],
                "created": "2025-01-01T00:00:00Z",
                "updated": "2025-01-02T00:00:00Z",
                "description": None,
                "subtasks": [],
                "issuelinks": [],
            },
        }
        base["fields"].update(overrides)
        return base

    def test_basic_format(self):
        md = self.fmt(self._issue())
        assert "## PROJ-123: Fix login bug" in md
        assert "In Progress" in md
        assert "High" in md
        assert "Bug" in md
        assert "Alice" in md
        assert "backend" in md
        assert "auth" in md

    def test_url_included(self):
        md = self.fmt(self._issue())
        assert "https://mysite.atlassian.net/browse/PROJ-123" in md

    def test_unassigned(self):
        md = self.fmt(self._issue(assignee=None))
        assert "Unassigned" in md

    def test_with_subtasks(self):
        subtasks = [
            {
                "key": "PROJ-124",
                "fields": {"summary": "Sub task", "status": {"name": "Done"}},
            }
        ]
        md = self.fmt(self._issue(subtasks=subtasks))
        assert "PROJ-124" in md
        assert "Sub task" in md
        assert "Done" in md

    def test_with_description(self):
        desc = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Detailed description here."}],
                }
            ],
        }
        md = self.fmt(self._issue(description=desc))
        assert "### Description" in md
        assert "Detailed description here." in md


class TestFormatSearchResultsMarkdown:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jira_api import format_search_results_markdown
        self.fmt = format_search_results_markdown

    def test_empty_results(self):
        md = self.fmt({"issues": [], "total": 0})
        assert "No issues found" in md

    def test_with_results(self):
        data = {
            "issues": [
                {
                    "key": "PROJ-1",
                    "fields": {
                        "issuetype": {"name": "Task"},
                        "priority": {"name": "Medium"},
                        "status": {"name": "Open"},
                        "assignee": {"displayName": "Carol"},
                        "summary": "Do something important",
                    },
                }
            ],
            "total": 1,
        }
        md = self.fmt(data)
        assert "PROJ-1" in md
        assert "Task" in md
        assert "Carol" in md

    def test_long_summary_truncated(self):
        long_summary = "A" * 100
        data = {
            "issues": [
                {
                    "key": "X-1",
                    "fields": {
                        "issuetype": {"name": "Bug"},
                        "priority": {"name": "Low"},
                        "status": {"name": "Open"},
                        "assignee": None,
                        "summary": long_summary,
                    },
                }
            ],
            "total": 1,
        }
        md = self.fmt(data)
        assert "..." in md

    def test_enhanced_search_without_total(self):
        data = {
            "issues": [
                {
                    "key": "PROJ-2",
                    "fields": {
                        "issuetype": {"name": "Bug"},
                        "priority": {"name": "High"},
                        "status": {"name": "Open"},
                        "assignee": None,
                        "summary": "No total field",
                    },
                }
            ],
            "isLast": False,
            "nextPageToken": "CAEaAggB",
        }
        md = self.fmt(data)
        assert "Search Results (1 issue)" in md
        assert "Next Page Token" in md


class TestParseIssueInputUrl:
    """Test parse_issue_input for URL inputs only (bare keys call get_base_url)."""

    @pytest.fixture(autouse=True)
    def _import(self, monkeypatch):
        monkeypatch.delenv("JIRA_BASE_URL", raising=False)
        monkeypatch.delenv("ATLASSIAN_BASE_URL", raising=False)
        from jira_api import parse_issue_input
        self.parse = parse_issue_input

    def test_browse_url(self):
        base, key = self.parse(
            "https://mysite.atlassian.net/browse/PROJ-123"
        )
        assert base == "https://mysite.atlassian.net"
        assert key == "PROJ-123"

    def test_jira_browse_url(self):
        base, key = self.parse(
            "https://mysite.atlassian.net/jira/browse/PROJ-456"
        )
        # Jira Cloud serves the REST API at the site root, not under /jira.
        assert base == "https://mysite.atlassian.net"
        assert key == "PROJ-456"

    def test_issues_url(self):
        base, key = self.parse(
            "https://mysite.atlassian.net/issues/PROJ-789"
        )
        assert base == "https://mysite.atlassian.net"
        assert key == "PROJ-789"

    def test_software_project_issue_url(self):
        base, key = self.parse(
            "https://mysite.atlassian.net/jira/software/c/projects/PROJ/issues/PROJ-123"
        )
        assert base == "https://mysite.atlassian.net"
        assert key == "PROJ-123"

    def test_board_selected_issue_url(self):
        base, key = self.parse(
            "https://mysite.atlassian.net/jira/software/projects/PROJ/boards/1"
            "?selectedIssue=PROJ-77"
        )
        assert base == "https://mysite.atlassian.net"
        assert key == "PROJ-77"

    def test_untrusted_host_refused(self):
        with pytest.raises(SystemExit):
            self.parse("https://evil.example.com/browse/PROJ-1")

    def test_http_refused(self):
        with pytest.raises(SystemExit):
            self.parse("http://mysite.atlassian.net/browse/PROJ-1")

    def test_configured_custom_domain(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.corp.com")
        base, key = self.parse("https://jira.corp.com/browse/PROJ-5")
        assert base == "https://jira.corp.com"
        assert key == "PROJ-5"

    def test_configured_custom_domain_blocks_other_hosts(self, monkeypatch):
        monkeypatch.setenv("JIRA_BASE_URL", "https://jira.corp.com")
        with pytest.raises(SystemExit):
            self.parse("https://mysite.atlassian.net/browse/PROJ-5")


class TestResolveUrlBase:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jira_api import resolve_url_base
        self.fn = resolve_url_base

    def test_lookalike_and_userinfo_refused(self):
        for url in (
            "https://atlassian.net.evil.com/browse/A-1",
            "https://ok.atlassian.net@evil.com/browse/A-1",
        ):
            with pytest.raises(ValueError):
                self.fn(url, None)

    def test_cloud_config_allows_other_cloud_site(self):
        assert (
            self.fn("https://b.atlassian.net/browse/A-1", "https://a.atlassian.net")
            == "https://b.atlassian.net"
        )


class TestIssueKeyFromUrl:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jira_api import issue_key_from_url
        self.fn = issue_key_from_url

    def test_service_desk_queue(self):
        url = "https://s.atlassian.net/jira/servicedesk/projects/SD/queues/custom/1/SD-12"
        assert self.fn(url) == "SD-12"

    def test_no_key(self):
        assert self.fn("https://s.atlassian.net/jira/your-work") is None

    def test_selected_issue_wins(self):
        url = "https://s.atlassian.net/browse/AB-1?selectedIssue=BC-2"
        assert self.fn(url) == "BC-2"


class TestAuthHeader:
    """Tests for jira_api._auth_header (Basic auth for Jira Cloud)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from jira_api import _auth_header
        self.build = _auth_header

    def test_basic_auth_uses_email_and_token(self, monkeypatch):
        monkeypatch.setenv("ATLASSIAN_USER_EMAIL", "dev@example.com")
        encoded = base64.b64encode(b"dev@example.com:secret").decode()
        assert self.build("secret") == f"Basic {encoded}"

    def test_missing_email_exits(self, monkeypatch):
        monkeypatch.delenv("ATLASSIAN_USER_EMAIL", raising=False)
        with pytest.raises(SystemExit):
            self.build("secret")


class TestMarkdownToAdf:
    @pytest.fixture(autouse=True)
    def _import(self):
        from jira_api import markdown_to_adf, format_adf_to_text
        self.fn = markdown_to_adf
        self.back = format_adf_to_text

    def test_plain_text_single_paragraph(self):
        doc = self.fn("hello")
        assert doc == {"version": 1, "type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "hello"}]}]}

    def test_empty_text(self):
        assert self.fn("")["content"] == [{"type": "paragraph", "content": []}]

    def test_paragraphs_and_hard_breaks(self):
        content = self.fn("a\nb\n\nc")["content"]
        assert [n["type"] for n in content] == ["paragraph", "paragraph"]
        assert content[0]["content"][1] == {"type": "hardBreak"}

    def test_heading(self):
        node = self.fn("## Steps ##")["content"][0]
        assert node == {"type": "heading", "attrs": {"level": 2},
                        "content": [{"type": "text", "text": "Steps"}]}

    def test_hash_without_space_is_text(self):
        assert self.fn("#tag")["content"][0]["type"] == "paragraph"

    def test_nested_bullet_list(self):
        node = self.fn("- a\n  - b\n- c")["content"][0]
        assert node["type"] == "bulletList"
        assert len(node["content"]) == 2
        nested = node["content"][0]["content"][1]
        assert nested["type"] == "bulletList"
        assert nested["content"][0]["content"][0]["content"][0]["text"] == "b"

    def test_ordered_list_start(self):
        node = self.fn("3. x\n4. y")["content"][0]
        assert node["type"] == "orderedList"
        assert node["attrs"] == {"order": 3}
        assert len(node["content"]) == 2

    def test_list_items_separated_by_blank_line_stay_one_list(self):
        content = self.fn("- a\n\n- b")["content"]
        assert len(content) == 1
        assert len(content[0]["content"]) == 2

    def test_fenced_code_block_keeps_blank_lines_and_markdown(self):
        node = self.fn("```bash\necho *a*\n\n# not heading\n```")["content"][0]
        assert node == {"type": "codeBlock", "attrs": {"language": "bash"},
                        "content": [{"type": "text", "text": "echo *a*\n\n# not heading"}]}

    def test_inline_marks(self):
        nodes = self.fn("a [l](https://x.io) `c` **b** *e* https://y.io/p.")["content"][0]["content"]
        marks = {n["text"]: n.get("marks") for n in nodes}
        assert marks["l"] == [{"type": "link", "attrs": {"href": "https://x.io"}}]
        assert marks["c"] == [{"type": "code"}]
        assert marks["b"] == [{"type": "strong"}]
        assert marks["e"] == [{"type": "em"}]
        assert marks["https://y.io/p"] == [{"type": "link", "attrs": {"href": "https://y.io/p"}}]
        assert nodes[-1] == {"type": "text", "text": "."}

    def test_snake_case_and_multiplication_not_emphasis(self):
        nodes = self.fn("snake_case_name and 2 * 3 * 4")["content"][0]["content"]
        assert nodes == [{"type": "text", "text": "snake_case_name and 2 * 3 * 4"}]

    def test_blockquote_and_rule(self):
        content = self.fn("> q1\n> # h\n\n---")["content"]
        assert content[0]["type"] == "blockquote"
        assert [b["type"] for b in content[0]["content"]] == ["paragraph", "paragraph"]
        assert content[1] == {"type": "rule"}

    def test_no_empty_text_nodes(self):
        import json
        doc = self.fn("**b**\n\n- `x`\n\n[l](https://a.b)")
        assert '"text": ""' not in json.dumps(doc)

    def test_round_trip_keeps_structure(self):
        md = "# T\n\n- a\n- b [l](https://x.io)\n\n```py\nx = 1\n```"
        text = self.back(self.fn(md))
        assert "# T" in text
        assert "- b [l](https://x.io)" in text
        assert "```py\nx = 1\n```" in text


class TestJiraAttachmentHelpers:
    def test_select_images_by_default(self):
        from jira_api import select_attachments
        atts = [{"filename": "a.png", "mimeType": "image/png"},
                {"filename": "log.txt", "mimeType": "text/plain"}]
        picked, missing = select_attachments(atts, [])
        assert [a["filename"] for a in picked] == ["a.png"]
        assert missing == []

    def test_select_by_name(self):
        from jira_api import select_attachments
        atts = [{"filename": "Log.TXT", "mimeType": "text/plain"}]
        picked, missing = select_attachments(atts, ["log.txt", "x.png"])
        assert picked == atts
        assert missing == ["x.png"]

    def test_content_url_built_from_id(self):
        from jira_api import attachment_content_url
        assert (attachment_content_url("https://s.atlassian.net", "10001")
                == "https://s.atlassian.net/rest/api/3/attachment/content/10001?redirect=false")
        for bad in ("../x", "1?a=b", ""):
            with pytest.raises(ValueError):
                attachment_content_url("https://s.atlassian.net", bad)

    def test_safe_attachment_name(self):
        from jira_api import safe_attachment_name
        assert safe_attachment_name("..\\..\\evil.png") == "evil.png"
        assert safe_attachment_name("") == "attachment"

    def test_cache_dir(self):
        from jira_api import skill_cache_dir
        assert skill_cache_dir().parts[-2:] == ("mythril-skills-cache", "jira")

    def test_issue_markdown_lists_attachments(self):
        from jira_api import format_issue_markdown
        md = format_issue_markdown({"key": "A-1", "fields": {"attachment": [
            {"id": "7", "filename": "s.png", "mimeType": "image/png", "size": 10}]}})
        assert "### Attachments" in md
        assert "s.png (image/png, 10 bytes, id: 7)" in md
