"""Tests for jira skill scripts.

Covers pure formatter functions (no API/network calls):
- format_adf_to_text: Atlassian Document Format → plain text
- format_issue_markdown: issue JSON → markdown
- format_search_results_markdown: search response → markdown table
- parse_issue_input: URL parsing (URL branch only)
"""

from __future__ import annotations

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
        assert "print('hi')" in result

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


class TestParseIssueInputUrl:
    """Test parse_issue_input for URL inputs only (bare keys call get_base_url)."""

    @pytest.fixture(autouse=True)
    def _import(self):
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
        assert base == "https://mysite.atlassian.net/jira"
        assert key == "PROJ-456"

    def test_issues_url(self):
        base, key = self.parse(
            "https://mysite.atlassian.net/issues/PROJ-789"
        )
        assert base == "https://mysite.atlassian.net"
        assert key == "PROJ-789"
