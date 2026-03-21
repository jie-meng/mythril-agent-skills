"""Tests for confluence skill scripts.

Covers pure formatter functions (no API/network calls):
- _strip_html: HTML → plain text/markdown
- format_page_markdown: page JSON → markdown
- format_pages_table: page list → markdown table
- format_spaces_table: space list → markdown table
- format_search_results: CQL results → markdown table
- format_comments_markdown: comments → markdown
- parse_page_input: URL branch only
"""

from __future__ import annotations

import pytest


class TestStripHtml:
    @pytest.fixture(autouse=True)
    def _import(self):
        from confluence_api import _strip_html
        self.strip = _strip_html

    def test_plain_text(self):
        assert self.strip("Hello world") == "Hello world"

    def test_br_tag(self):
        assert "Hello\nworld" in self.strip("Hello<br/>world")

    def test_headings(self):
        result = self.strip("<h2>Title</h2>")
        assert result.startswith("## Title")

    def test_list_items(self):
        result = self.strip("<li>Item one</li><li>Item two</li>")
        assert "- Item one" in result
        assert "- Item two" in result

    def test_code_inline(self):
        assert "`code`" in self.strip("<code>code</code>")

    def test_bold(self):
        assert "**bold**" in self.strip("<strong>bold</strong>")

    def test_italic(self):
        assert "*italic*" in self.strip("<em>italic</em>")

    def test_links(self):
        html = '<a href="https://example.com">Click</a>'
        result = self.strip(html)
        assert "[Click](https://example.com)" in result

    def test_structured_macro_replaced(self):
        html = '<ac:structured-macro ac:name="code">some content</ac:structured-macro>'
        result = self.strip(html)
        assert "[macro]" in result

    def test_remaining_tags_stripped(self):
        result = self.strip("<div><span>text</span></div>")
        assert "<" not in result
        assert "text" in result

    def test_html_entities_unescaped(self):
        assert "&" in self.strip("&amp;")
        assert "<" in self.strip("&lt;")


class TestFormatPageMarkdown:
    @pytest.fixture(autouse=True)
    def _import(self):
        from confluence_api import format_page_markdown
        self.fmt = format_page_markdown

    def _page(self, **overrides) -> dict:
        base = {
            "id": "12345",
            "title": "Test Page",
            "status": "current",
            "spaceId": "SPACE1",
            "authorId": "user123",
            "createdAt": "2025-01-01T00:00:00Z",
            "version": {"number": 3, "createdAt": "2025-01-02T00:00:00Z", "message": ""},
            "_links": {"webui": "/spaces/TEAM/pages/12345", "base": "https://site.atlassian.net/wiki"},
        }
        base.update(overrides)
        return base

    def test_basic_format(self):
        md = self.fmt(self._page())
        assert "## Test Page" in md
        assert "12345" in md
        assert "SPACE1" in md
        assert "current" in md
        assert "Version**: 3" in md

    def test_url_included(self):
        md = self.fmt(self._page())
        assert "https://site.atlassian.net/wiki/spaces/TEAM/pages/12345" in md

    def test_with_body_content(self):
        page = self._page(body={"storage": {"value": "<p>Page content here</p>"}})
        md = self.fmt(page)
        assert "### Content" in md
        assert "Page content here" in md

    def test_with_labels(self):
        page = self._page(labels={"results": [{"name": "docs"}, {"name": "api"}]})
        md = self.fmt(page)
        assert "docs" in md
        assert "api" in md

    def test_with_parent(self):
        page = self._page(parentId="99999")
        md = self.fmt(page)
        assert "99999" in md

    def test_version_message(self):
        page = self._page(version={"number": 5, "createdAt": "2025-01-05", "message": "Updated specs"})
        md = self.fmt(page)
        assert "Updated specs" in md


class TestFormatPagesTable:
    @pytest.fixture(autouse=True)
    def _import(self):
        from confluence_api import format_pages_table
        self.fmt = format_pages_table

    def test_empty_list(self):
        md = self.fmt([])
        assert "No pages found" in md

    def test_with_pages(self):
        pages = [
            {
                "id": "1",
                "title": "First Page",
                "spaceId": "SP",
                "status": "current",
                "version": {"number": 2, "createdAt": "2025-03-01T00:00:00Z"},
            }
        ]
        md = self.fmt(pages)
        assert "First Page" in md
        assert "2025-03-01" in md

    def test_long_title_truncated(self):
        pages = [
            {
                "id": "2",
                "title": "A" * 60,
                "spaceId": "SP",
                "status": "current",
                "version": {},
            }
        ]
        md = self.fmt(pages)
        assert "..." in md


class TestFormatSpacesTable:
    @pytest.fixture(autouse=True)
    def _import(self):
        from confluence_api import format_spaces_table
        self.fmt = format_spaces_table

    def test_empty(self):
        md = self.fmt([])
        assert "No spaces found" in md

    def test_with_spaces(self):
        spaces = [
            {"id": "1", "key": "DEV", "name": "Development", "type": "global", "status": "current"},
        ]
        md = self.fmt(spaces)
        assert "DEV" in md
        assert "Development" in md
        assert "global" in md


class TestFormatSearchResults:
    @pytest.fixture(autouse=True)
    def _import(self):
        from confluence_api import format_search_results
        self.fmt = format_search_results

    def test_empty(self):
        md = self.fmt({"results": [], "totalSize": 0})
        assert "No results found" in md

    def test_with_results(self):
        data = {
            "results": [
                {
                    "content": {
                        "type": "page",
                        "id": "100",
                        "title": "API Docs",
                    },
                    "title": "API Docs",
                    "lastModified": "2025-02-15T00:00:00Z",
                }
            ],
            "totalSize": 1,
        }
        md = self.fmt(data)
        assert "API Docs" in md
        assert "page" in md


class TestFormatCommentsMarkdown:
    @pytest.fixture(autouse=True)
    def _import(self):
        from confluence_api import format_comments_markdown
        self.fmt = format_comments_markdown

    def test_empty(self):
        md = self.fmt([])
        assert "No comments" in md

    def test_with_comments(self):
        comments = [
            {
                "id": "c1",
                "authorId": "user1",
                "createdAt": "2025-01-01T00:00:00Z",
                "version": {},
                "body": {"storage": {"value": "<p>Great work!</p>"}},
            }
        ]
        md = self.fmt(comments)
        assert "Great work!" in md
        assert "user1" in md


class TestParsePageInputUrl:
    """Test parse_page_input for URL inputs only (bare IDs call get_base_url)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from confluence_api import parse_page_input
        self.parse = parse_page_input

    def test_full_url(self):
        base, page_id = self.parse(
            "https://mysite.atlassian.net/wiki/spaces/TEAM/pages/12345/Title"
        )
        assert base == "https://mysite.atlassian.net"
        assert page_id == "12345"

    def test_url_without_title(self):
        base, page_id = self.parse(
            "https://mysite.atlassian.net/wiki/spaces/TEAM/pages/67890"
        )
        assert base == "https://mysite.atlassian.net"
        assert page_id == "67890"
