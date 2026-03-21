"""Tests for figma skill scripts.

Covers pure functions (no API/network calls):
- figma_fetch: rgba_to_hex, format_paint, simplify_node, render_node_markdown,
               render_file_overview, parse_figma_url
- figma_export: safe_filename
"""

from __future__ import annotations

import pytest


# ── figma_fetch ────────────────────────────────────────────────────────────────


class TestRgbaToHex:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_fetch import rgba_to_hex
        self.func = rgba_to_hex

    def test_black(self):
        assert self.func({"r": 0, "g": 0, "b": 0}) == "#000000"

    def test_white(self):
        assert self.func({"r": 1, "g": 1, "b": 1}) == "#FFFFFF"

    def test_red(self):
        assert self.func({"r": 1, "g": 0, "b": 0}) == "#FF0000"

    def test_partial_values(self):
        result = self.func({"r": 0.5, "g": 0.5, "b": 0.5})
        assert result == "#808080"

    def test_missing_keys_default_zero(self):
        assert self.func({}) == "#000000"


class TestFormatPaint:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_fetch import format_paint
        self.func = format_paint

    def test_solid_opaque(self):
        paint = {"type": "SOLID", "color": {"r": 1, "g": 0, "b": 0, "a": 1}}
        assert self.func(paint) == "#FF0000"

    def test_solid_with_alpha(self):
        paint = {
            "type": "SOLID",
            "color": {"r": 1, "g": 0, "b": 0, "a": 0.5},
            "opacity": 1.0,
        }
        result = self.func(paint)
        assert "#FF0000" in result
        assert "opacity" in result

    def test_invisible_returns_none(self):
        paint = {"type": "SOLID", "visible": False}
        assert self.func(paint) is None

    def test_gradient(self):
        paint = {
            "type": "GRADIENT_LINEAR",
            "gradientStops": [
                {"color": {"r": 1, "g": 0, "b": 0}, "position": 0.0},
                {"color": {"r": 0, "g": 0, "b": 1}, "position": 1.0},
            ],
        }
        result = self.func(paint)
        assert "GRADIENT_LINEAR" in result
        assert "#FF0000" in result

    def test_image_fill(self):
        paint = {"type": "IMAGE", "imageRef": "abc123", "scaleMode": "FILL"}
        result = self.func(paint)
        assert "image fill" in result
        assert "abc123" in result

    def test_unknown_type(self):
        paint = {"type": "SOME_NEW_TYPE"}
        assert self.func(paint) == "some new type"


class TestSimplifyNode:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_fetch import simplify_node
        self.func = simplify_node

    def test_none_returns_none(self):
        assert self.func(None) is None

    def test_invisible_returns_none(self):
        assert self.func({"visible": False, "id": "1", "name": "x"}) is None

    def test_basic_frame(self):
        node = {
            "id": "1:2",
            "name": "Header",
            "type": "FRAME",
            "visible": True,
            "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 50},
        }
        result = self.func(node)
        assert result["id"] == "1:2"
        assert result["name"] == "Header"
        assert result["type"] == "FRAME"
        assert result["size"] == {"width": 100, "height": 50}

    def test_text_node(self):
        node = {
            "id": "3:4",
            "name": "Label",
            "type": "TEXT",
            "visible": True,
            "characters": "Hello World",
            "style": {
                "fontFamily": "Inter",
                "fontSize": 16,
                "fontWeight": 400,
            },
        }
        result = self.func(node)
        assert result["characters"] == "Hello World"
        assert result["typography"]["fontFamily"] == "Inter"
        assert result["typography"]["fontSize"] == 16

    def test_long_text_truncated(self):
        node = {
            "id": "1",
            "name": "Long",
            "type": "TEXT",
            "visible": True,
            "characters": "A" * 300,
            "style": {"fontFamily": "Arial", "fontSize": 12, "fontWeight": 400},
        }
        result = self.func(node)
        assert len(result["characters"]) == 201  # 200 + "…"
        assert result["characters"].endswith("…")

    def test_max_depth_truncates_children(self):
        child = {"id": "c", "name": "child", "type": "FRAME", "visible": True}
        node = {
            "id": "p",
            "name": "parent",
            "type": "FRAME",
            "visible": True,
            "children": [child],
        }
        result = self.func(node, depth=5, max_depth=5)
        assert result.get("_children_truncated") == 1
        assert "children" not in result

    def test_auto_layout_properties(self):
        node = {
            "id": "1",
            "name": "Stack",
            "type": "FRAME",
            "visible": True,
            "layoutMode": "VERTICAL",
            "itemSpacing": 8,
            "paddingTop": 16,
            "paddingRight": 16,
            "paddingBottom": 16,
            "paddingLeft": 16,
            "primaryAxisAlignItems": "CENTER",
            "counterAxisAlignItems": "MIN",
        }
        result = self.func(node)
        assert result["layoutMode"] == "VERTICAL"
        assert result["itemSpacing"] == 8
        assert result["paddingTop"] == 16


class TestRenderNodeMarkdown:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_fetch import render_node_markdown
        self.func = render_node_markdown

    def test_basic_render(self):
        node_data = {
            "id": "1:2",
            "name": "Button",
            "type": "COMPONENT",
            "size": {"width": 120, "height": 40},
        }
        md = self.func(node_data, "MyDesign")
        assert "## Figma Design Specs" in md
        assert "**File**: MyDesign" in md
        assert "Button" in md
        assert "120" in md


class TestRenderFileOverview:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_fetch import render_file_overview
        self.func = render_file_overview

    def test_basic_overview(self):
        data = {
            "name": "TestFile",
            "document": {"children": [{"name": "Page 1"}, {"name": "Page 2"}]},
            "components": {"c1": {"name": "Button"}},
            "styles": {},
        }
        md = self.func(data)
        assert "TestFile" in md
        assert "Page 1" in md
        assert "Page 2" in md
        assert "Button" in md
        assert "**Components**: 1" in md

    def test_empty_file(self):
        data = {"name": "Empty", "document": {"children": []}, "components": {}, "styles": {}}
        md = self.func(data)
        assert "Empty" in md
        assert "**Pages** (0)" in md


class TestParseFigmaUrl:
    """Test parse_figma_url for valid URLs (invalid URLs call sys.exit)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_fetch import parse_figma_url
        self.func = parse_figma_url

    def test_design_url_with_node(self):
        url = "https://www.figma.com/design/ABC123/Title?node-id=1-2"
        key, node = self.func(url)
        assert key == "ABC123"
        assert node == "1:2"

    def test_file_url_no_node(self):
        url = "https://www.figma.com/file/XYZ789/Title"
        key, node = self.func(url)
        assert key == "XYZ789"
        assert node is None

    def test_encoded_node_id(self):
        url = "https://www.figma.com/design/KEY/T?node-id=10%3A20"
        key, node = self.func(url)
        assert node == "10:20"


# ── figma_export ───────────────────────────────────────────────────────────────


class TestSafeFilename:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_export import safe_filename
        self.func = safe_filename

    def test_normal_name(self):
        assert self.func("Button Primary") == "Button_Primary"

    def test_special_characters_removed(self):
        result = self.func("Icon / Settings @ 2x")
        assert "/" not in result
        assert "@" not in result

    def test_empty_returns_default(self):
        assert self.func("") == "figma_export"

    def test_only_special_chars_returns_default(self):
        assert self.func("@#$%") == "figma_export"

    def test_whitespace_collapsed(self):
        result = self.func("  Hello   World  ")
        assert "  " not in result
