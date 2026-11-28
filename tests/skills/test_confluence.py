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

    def test_code_macro_becomes_fenced_block(self):
        html = (
            '<ac:structured-macro ac:name="code" ac:schema-version="1">'
            '<ac:parameter ac:name="language">python</ac:parameter>'
            "<ac:plain-text-body><![CDATA[if a < b:\n\n\n    print('<li>x</li>')]]>"
            "</ac:plain-text-body></ac:structured-macro>"
        )
        result = self.strip(html)
        assert "```python\nif a < b:\n\n\n    print('<li>x</li>')\n```" in result

    def test_code_macro_without_cdata_keeps_text(self):
        html = '<ac:structured-macro ac:name="code">some content</ac:structured-macro>'
        assert "```\nsome content\n```" in self.strip(html)

    def test_other_macro_keeps_body_with_marker(self):
        html = (
            '<ac:structured-macro ac:name="info"><ac:parameter ac:name="title">T'
            "</ac:parameter><ac:rich-text-body><p>Heads up</p></ac:rich-text-body>"
            "</ac:structured-macro>"
        )
        result = self.strip(html)
        assert "[info]" in result
        assert "Heads up" in result
        assert "T" not in result.replace("[info]", "")

    def test_attached_image_becomes_reference(self):
        html = '<ac:image ac:height="250"><ri:attachment ri:filename="shot 1.png" /></ac:image>'
        assert "![shot 1.png](attachment:shot 1.png)" in self.strip(html)

    def test_url_image_becomes_markdown_image(self):
        html = '<ac:image><ri:url ri:value="https://example.com/a.png" /></ac:image>'
        assert "![](https://example.com/a.png)" in self.strip(html)

    def test_paragraphs_are_separated(self):
        assert self.strip("<p>one</p><p>two</p>") == "one\n\ntwo"

    def test_page_link_keeps_title(self):
        html = '<ac:link><ri:page ri:content-title="Design Doc" /></ac:link>'
        assert "[page: Design Doc]" in self.strip(html)

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
    def _import(self, monkeypatch):
        monkeypatch.delenv("CONFLUENCE_BASE_URL", raising=False)
        monkeypatch.delenv("ATLASSIAN_BASE_URL", raising=False)
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

    def test_untrusted_host_refused(self):
        with pytest.raises(SystemExit):
            self.parse("https://evil.example.com/wiki/spaces/T/pages/1")

    def test_configured_host_uses_configured_base(self, monkeypatch):
        monkeypatch.setenv("CONFLUENCE_BASE_URL", "https://wiki.corp.com/confluence/")
        base, page_id = self.parse("https://wiki.corp.com/confluence/spaces/T/pages/42")
        assert base == "https://wiki.corp.com/confluence"
        assert page_id == "42"


class TestResolveUrlBase:
    @pytest.fixture(autouse=True)
    def _import(self):
        from confluence_api import resolve_url_base
        self.fn = resolve_url_base

    def test_cloud_site_without_config(self):
        assert self.fn("https://acme.atlassian.net/wiki/x", None) == "https://acme.atlassian.net"

    def test_other_host_without_config_refused(self):
        with pytest.raises(ValueError, match="Refusing to send credentials"):
            self.fn("https://evil.com/wiki/spaces/T/pages/1", None)

    def test_lookalike_host_refused(self):
        with pytest.raises(ValueError):
            self.fn("https://atlassian.net.evil.com/wiki/pages/1", None)

    def test_userinfo_not_trusted(self):
        with pytest.raises(ValueError):
            self.fn("https://acme.atlassian.net@evil.com/wiki/pages/1", None)

    def test_http_refused(self):
        with pytest.raises(ValueError, match="non-https"):
            self.fn("http://acme.atlassian.net/wiki/pages/1", None)

    def test_http_allowed_only_when_configured_exactly(self):
        assert self.fn("http://wiki.lan/pages/1", "http://wiki.lan") == "http://wiki.lan"

    def test_configured_self_hosted_blocks_cloud_sites(self):
        with pytest.raises(ValueError):
            self.fn("https://acme.atlassian.net/wiki/pages/1", "https://wiki.corp.com")

    def test_configured_cloud_allows_other_cloud_site(self):
        base = self.fn("https://other.atlassian.net/wiki/pages/1", "https://acme.atlassian.net")
        assert base == "https://other.atlassian.net"


class TestAttachmentHelpers:
    def test_select_all_images_by_default(self):
        from confluence_api import select_attachments
        results = [
            {"title": "a.png", "mediaType": "image/png"},
            {"title": "b.pdf", "mediaType": "application/pdf"},
        ]
        picked, missing = select_attachments(results, [])
        assert [a["title"] for a in picked] == ["a.png"]
        assert missing == []

    def test_select_by_name_case_insensitive_and_missing(self):
        from confluence_api import select_attachments
        results = [{"title": "Shot.PNG", "mediaType": "image/png"}]
        picked, missing = select_attachments(results, ["shot.png", "nope.png"])
        assert picked == results
        assert missing == ["nope.png"]

    def test_safe_attachment_name_strips_directories(self):
        from confluence_api import safe_attachment_name
        assert safe_attachment_name("../../etc/passwd") == "passwd"
        assert safe_attachment_name('a:b?.png') == "a_b_.png"
        assert safe_attachment_name("..") == "attachment"

    def test_download_url_is_site_relative(self):
        from confluence_api import attachment_download_url
        att = {"id": "1", "downloadLink": "/download/attachments/9/a.png?api=v2"}
        assert (
            attachment_download_url("https://acme.atlassian.net", att)
            == "https://acme.atlassian.net/wiki/download/attachments/9/a.png?api=v2"
        )

    def test_download_url_rejects_absolute_link(self):
        from confluence_api import attachment_download_url
        for link in ("https://evil.com/a.png", "//evil.com/a.png", ""):
            with pytest.raises(ValueError):
                attachment_download_url("https://acme.atlassian.net", {"downloadLink": link})

    def test_cache_dir_ends_with_skill(self):
        from confluence_api import skill_cache_dir
        path = skill_cache_dir()
        assert path.parts[-2:] == ("mythril-skills-cache", "confluence")


class TestCursor:
    def test_next_cursor_and_note(self):
        from confluence_api import cursor_note, next_cursor
        data = {"_links": {"next": "/wiki/api/v2/pages?cursor=abc%3D&limit=25"}}
        assert next_cursor(data) == "abc="
        assert "--cursor 'abc='" in cursor_note(data)

    def test_no_next(self):
        from confluence_api import cursor_note, next_cursor
        assert next_cursor({}) is None
        assert cursor_note({"_links": {}}) == ""
