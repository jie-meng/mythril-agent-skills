"""Tests for figma skill scripts.

Covers pure functions (no API/network calls):
- figma_fetch: rgba_to_hex, format_paint, simplify_node, render_node_markdown,
               render_file_overview, parse_figma_url, collect_variable_ids,
               build_name_refs, variable_names, format_styles,
               format_bound_variables, render_outline, render_nodes
- figma_export: safe_filename, build_render_params, plan_outputs,
                parse_image_refs, sniff_image_ext
- figma_common: normalize_node_id, parse_figma_ref, collect_targets,
                build_query, rate_limit_message
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

    def test_child_headings_include_ids(self):
        node_data = {
            "id": "1:2",
            "name": "Section",
            "type": "SECTION",
            "children": [
                {"id": "3:4", "name": "Login", "type": "FRAME"},
                {"name": "No id", "type": "FRAME"},
            ],
        }
        md = self.func(node_data, "F")
        assert "### [FRAME] Login (id: 3:4)" in md
        assert "### [FRAME] No id\n" in md + "\n"
        assert "(id: None)" not in md


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

    def test_pages_include_ids(self):
        data = {
            "name": "F",
            "document": {"children": [{"id": "0:1", "name": "Screens"}]},
            "components": {},
            "styles": {},
        }
        assert "  - Screens (id: 0:1)" in self.func(data)

    def test_empty_file(self):
        data = {"name": "Empty", "document": {"children": []}, "components": {}, "styles": {}}
        md = self.func(data)
        assert "Empty" in md
        assert "**Pages** (0)" in md


class TestParseFigmaUrl:
    """Test parse_figma_url (re-exported by figma_fetch)."""

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

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            self.func("https://example.com/design/ABC/T")


# ── figma_common ───────────────────────────────────────────────────────────────


class TestNormalizeNodeId:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_common import normalize_node_id
        self.func = normalize_node_id

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("1-2", "1:2"),
            ("1:2", "1:2"),
            ("10%3A20", "10:20"),
            (" 690-7680 ", "690:7680"),
            ("I1-2;3-4", "I1:2;3:4"),
            ("I1:2;3:4;5:6", "I1:2;3:4;5:6"),
        ],
    )
    def test_valid(self, raw, expected):
        assert self.func(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        ["690-7680 fig:shelf", "690-7680figshelf", "1", "abc", "1-2#x", ""],
    )
    def test_invalid_raises(self, raw):
        with pytest.raises(ValueError, match="Invalid node id"):
            self.func(raw)


class TestParseFigmaRef:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_common import parse_figma_ref
        self.func = parse_figma_ref

    def test_branch_url_uses_branch_key(self):
        ref = self.func(
            "https://www.figma.com/design/MAIN123/branch/BR456/Title?node-id=1-2"
        )
        assert ref.file_key == "BR456"
        assert ref.branch_of == "MAIN123"
        assert ref.node_id == "1:2"

    @pytest.mark.parametrize("kind", ["design", "file", "proto", "board", "slides"])
    def test_supported_kinds(self, kind):
        ref = self.func(f"https://www.figma.com/{kind}/KEY1/T?node-id=3-4")
        assert ref.file_key == "KEY1"
        assert ref.node_id == "3:4"

    def test_fragment_and_extra_params_ignored(self):
        ref = self.func(
            "https://www.figma.com/design/KEY/T?t=abc&node-id=690-7680&m=dev#frag"
        )
        assert ref.node_id == "690:7680"

    def test_node_id_underscore_param(self):
        assert self.func("https://figma.com/file/KEY/T?node_id=1%3A2").node_id == "1:2"

    def test_no_scheme(self):
        assert self.func("figma.com/design/KEY/T").file_key == "KEY"

    def test_label_glued_after_url_rejected(self):
        """The failure from the field: a loop appended a label to the URL."""
        with pytest.raises(ValueError, match="whitespace"):
            self.func("https://www.figma.com/design/KEY/T?node-id=690-7680 fig:shelf")

    def test_label_glued_without_space_rejected(self):
        with pytest.raises(ValueError, match="Invalid node id"):
            self.func("https://www.figma.com/design/KEY/T?node-id=690-7680figshelf")

    def test_non_figma_host_rejected(self):
        with pytest.raises(ValueError, match="figma.com"):
            self.func("https://evilfigma.com/design/KEY/T")

    def test_unknown_kind_rejected(self):
        with pytest.raises(ValueError, match="file key"):
            self.func("https://www.figma.com/community/file/123")


class TestCollectTargets:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_common import collect_targets
        self.func = collect_targets

    def test_multiple_urls_and_ids_deduped(self):
        key, ids = self.func(
            [
                "https://www.figma.com/design/KEY/T?node-id=1-2",
                "https://www.figma.com/design/KEY/T?node-id=3-4",
                "https://www.figma.com/design/KEY/T?node-id=1-2",
            ],
            "5-6, 3:4,",
        )
        assert key == "KEY"
        assert ids == ["1:2", "3:4", "5:6"]

    def test_no_node(self):
        assert self.func(["https://www.figma.com/design/KEY/T"], None) == ("KEY", [])

    def test_mixed_files_rejected(self):
        with pytest.raises(ValueError, match="same Figma file"):
            self.func(
                [
                    "https://www.figma.com/design/A1/T?node-id=1-2",
                    "https://www.figma.com/design/B2/T?node-id=1-2",
                ],
                None,
            )

    def test_bad_extra_id_rejected(self):
        with pytest.raises(ValueError):
            self.func(["https://www.figma.com/design/KEY/T"], "1-2 shelf")


class TestBuildQuery:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_common import build_query
        self.func = build_query

    def test_drops_none_and_formats_bools(self):
        q = self.func({"ids": "1:2,3:4", "a": None, "b": True, "c": False, "s": 2})
        assert q == "ids=1:2,3:4&b=true&c=false&s=2"

    def test_instance_ids_keep_separators(self):
        assert self.func({"ids": "I1:2;3:4"}) == "ids=I1:2;3:4"


class TestRateLimitMessage:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_common import rate_limit_message
        self.func = rate_limit_message

    def test_low_limit_lowercase_headers(self):
        msg = self.func(
            {"x-figma-rate-limit-type": "low", "retry-after": "3600"}, "/v1/images/K"
        )
        assert "PER MONTH" in msg
        assert "3600s" in msg

    def test_high_limit(self):
        msg = self.func(
            {"X-Figma-Rate-Limit-Type": "high", "Retry-After": "30"}, "/v1/files/K"
        )
        assert "per-minute" in msg
        assert "Wait 30 seconds" in msg


# ── figma_fetch (multi-node, metadata) ────────────────────────────────────────


class TestRenderNodes:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_fetch import render_nodes
        self.func = render_nodes

    def test_renders_each_and_counts_missing(self):
        data = {
            "name": "File",
            "nodes": {
                "1:2": {"document": {"id": "1:2", "name": "A", "type": "FRAME"}},
                "3:4": None,
            },
        }
        md, missing = self.func(data, ["1:2", "3:4"], 3)
        assert "**Node**: A" in md
        assert missing == 1


class TestRenderFileMeta:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_fetch import render_file_meta
        self.func = render_file_meta

    def test_fields(self):
        md = self.func(
            {
                "file": {
                    "name": "App",
                    "editorType": "figma",
                    "last_touched_at": "2026-01-01T00:00:00Z",
                    "last_touched_by": {"handle": "Ann"},
                    "role": "viewer",
                }
            },
            "KEY",
        )
        assert "**File**: App" in md
        assert "**Editor**: figma" in md
        assert "**Last edited by**: Ann" in md
        assert "--pages" in md


class TestComplexStroke:
    def test_complex_stroke_rendered(self):
        from figma_fetch import render_node_markdown, simplify_node

        node = {
            "id": "1:2",
            "name": "Line",
            "type": "VECTOR",
            "strokes": [{"type": "SOLID", "color": {"r": 0, "g": 0, "b": 0}}],
            "strokeWeight": 2,
            "complexStrokeProperties": {"type": "BRUSH"},
        }
        simplified = simplify_node(node)
        assert simplified["complexStroke"] == "BRUSH"
        assert "Complex stroke: BRUSH" in render_node_markdown(simplified, "F")


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


class TestBuildRenderParams:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_export import build_render_params
        self.func = build_render_params

    def test_batch_ids_joined(self):
        params = self.func(["1:2", "3:4"], "png", 2.0)
        assert params["ids"] == "1:2,3:4"
        assert "svg_include_id" not in params

    def test_svg_options(self):
        params = self.func(["1:2"], "svg", 1.0, svg_outline_text=False)
        assert params["svg_include_id"] is True
        assert params["svg_outline_text"] is False

    def test_optional_render_flags(self):
        params = self.func(
            ["1:2"], "png", 1, version="9", contents_only=False, use_absolute_bounds=True
        )
        assert params["version"] == "9"
        assert params["contents_only"] is False
        assert params["use_absolute_bounds"] is True


class TestPlanOutputs:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_export import plan_outputs
        self.func = plan_outputs

    def test_single_output(self, tmp_path):
        out = tmp_path / "a.png"
        assert self.func(["1:2"], "png", output=str(out)) == {"1:2": out}

    def test_default_names_in_out_dir(self, tmp_path):
        plan = self.func(["1:2", "I3:4;5:6"], "png", out_dir=str(tmp_path))
        assert plan["1:2"] == tmp_path / "figma_1-2.png"
        assert plan["I3:4;5:6"] == tmp_path / "figma_I3-4_5-6.png"

    def test_custom_names(self, tmp_path):
        plan = self.func(
            ["1:2", "3:4"], "svg", out_dir=str(tmp_path), names=["shelf", "d list"]
        )
        assert plan["1:2"].name == "shelf.svg"
        assert plan["3:4"].name == "d_list.svg"

    def test_output_with_many_nodes_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="--out-dir"):
            self.func(["1:2", "3:4"], "png", output=str(tmp_path / "x.png"))

    def test_names_count_mismatch_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="one name per node"):
            self.func(["1:2", "3:4"], "png", out_dir=str(tmp_path), names=["a"])

    def test_duplicate_names_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="Duplicate"):
            self.func(["1:2", "3:4"], "png", out_dir=str(tmp_path), names=["a", "a"])


# ── figma_fetch (names: styles, components, variables; outline) ───────────────


class TestCollectVariableIds:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_fetch import collect_variable_ids
        self.func = collect_variable_ids

    def test_single_alias(self):
        assert self.func({"type": "VARIABLE_ALIAS", "id": "V:1"}) == ["V:1"]

    def test_list_and_nested_dict_deduped(self):
        value = {
            "a": [{"type": "VARIABLE_ALIAS", "id": "V:1"}],
            "b": {"type": "VARIABLE_ALIAS", "id": "V:1"},
            "c": {"type": "VARIABLE_ALIAS", "id": "V:2"},
        }
        assert self.func(value) == ["V:1", "V:2"]

    def test_non_alias(self):
        assert self.func({"type": "OTHER"}) == []
        assert self.func("x") == []


class TestSimplifyNodeRefs:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_fetch import simplify_node
        self.func = simplify_node

    def test_keeps_styles_and_variable_ids(self):
        node = {
            "id": "1:2",
            "name": "Btn",
            "type": "FRAME",
            "styles": {"fill": "S:1"},
            "boundVariables": {
                "fills": [{"type": "VARIABLE_ALIAS", "id": "V:1"}],
                "itemSpacing": {"type": "VARIABLE_ALIAS", "id": "V:2"},
            },
        }
        out = self.func(node)
        assert out["styles"] == {"fill": "S:1"}
        assert out["boundVariables"] == {"fills": ["V:1"], "itemSpacing": ["V:2"]}


class TestBuildNameRefs:
    def test_styles_components_and_sets(self):
        from figma_fetch import build_name_refs

        entry = {
            "styles": {"S:1": {"name": "Brand/Primary", "styleType": "FILL"}},
            "components": {"C:1": {"name": "Button/Primary"}},
            "componentSets": {"CS:1": {"name": "Button"}},
        }
        refs = build_name_refs(entry)
        assert refs["styles"] == {"S:1": "Brand/Primary"}
        assert refs["components"] == {"C:1": "Button/Primary", "CS:1": "Button"}

    def test_empty_entry(self):
        from figma_fetch import build_name_refs

        assert build_name_refs({}) == {"styles": {}, "components": {}}

    def test_variant_prefixed_with_set_name(self):
        from figma_fetch import build_name_refs

        entry = {
            "components": {
                "C:1": {"name": "Dark Mode=Off", "componentSetId": "CS:1"},
                "C:2": {"name": "Dark Mode=On", "componentSetId": "CS:gone"},
            },
            "componentSets": {"CS:1": {"name": "Search Bar/Pro"}},
        }
        comps = build_name_refs(entry)["components"]
        assert comps["C:1"] == "Search Bar/Pro (Dark Mode=Off)"
        assert comps["C:2"] == "Dark Mode=On"


class TestVariableNames:
    def test_prefixes_collection(self):
        from figma_fetch import variable_names

        data = {
            "meta": {
                "variables": {
                    "V:1": {"name": "primary/500", "variableCollectionId": "VC:1"},
                    "V:2": {"name": "gap", "variableCollectionId": "VC:missing"},
                },
                "variableCollections": {"VC:1": {"name": "Colors"}},
            }
        }
        assert variable_names(data) == {"V:1": "Colors/primary/500", "V:2": "gap"}


class TestFormatStylesAndVariables:
    def test_format_styles_resolves_and_falls_back(self):
        from figma_fetch import format_styles

        out = format_styles({"fill": "S:1", "text": "S:9"}, {"S:1": "Brand"})
        assert out == "fill=Brand, text=S:9"

    def test_format_styles_dedupes_same_style(self):
        from figma_fetch import format_styles

        out = format_styles({"fills": "S:1", "fill": "S:1"}, {"S:1": "Brand"})
        assert out == "fill=Brand"

    def test_bound_variables_without_names(self):
        from figma_fetch import format_bound_variables

        out = format_bound_variables({"fills": ["V:1"], "gap": ["V:2"]}, {})
        assert out == "fills, gap"

    def test_bound_variables_with_names(self):
        from figma_fetch import format_bound_variables

        out = format_bound_variables(
            {"fills": ["V:1"], "gap": ["V:2", "V:3"]}, {"V:1": "C/p", "V:2": "S/4"}
        )
        assert out == "fills=C/p, gap=S/4 + ?"

    def test_legacy_list_input(self):
        from figma_fetch import format_bound_variables

        assert format_bound_variables(["fills"], {"V:1": "x"}) == "fills"


class TestRenderWithRefs:
    def test_component_style_variable_names_rendered(self):
        from figma_fetch import render_node_markdown

        node = {
            "id": "1:2",
            "name": "Root",
            "type": "FRAME",
            "children": [
                {
                    "id": "3:4",
                    "name": "Btn",
                    "type": "INSTANCE",
                    "componentId": "C:1",
                    "styles": {"fill": "S:1"},
                    "boundVariables": {"fills": ["V:1"]},
                }
            ],
        }
        refs = {
            "styles": {"S:1": "Brand/Primary"},
            "components": {"C:1": "Button/Primary"},
            "variables": {"V:1": "Colors/primary"},
        }
        md = render_node_markdown(node, "F", refs)
        assert "- Component: Button/Primary (id: C:1)" in md
        assert "- Styles: fill=Brand/Primary" in md
        assert "- Variables: fills=Colors/primary" in md

    def test_without_refs_keeps_ids(self):
        from figma_fetch import render_node_markdown

        node = {"id": "1:2", "name": "X", "type": "INSTANCE", "componentId": "C:1"}
        md = render_node_markdown(node, "F")
        assert "- Component ID: C:1" in md


class TestRenderOutline:
    def test_tree_with_ids_sizes_and_truncation(self):
        from figma_fetch import render_outline

        node = {
            "id": "1:2",
            "name": "Section",
            "type": "SECTION",
            "size": {"width": 1000.0, "height": 800.5},
            "children": [
                {"id": "3:4", "name": "Login", "type": "FRAME",
                 "_children_truncated": 7},
            ],
        }
        lines = render_outline(node)
        assert lines[0] == "- [SECTION] Section (id: 1:2) 1000×800.5"
        assert lines[1] == "  - [FRAME] Login (id: 3:4)"
        assert "7 children" in lines[2]

    def test_long_text_names_truncated(self):
        from figma_fetch import OUTLINE_NAME_MAX, render_outline

        node = {"id": "1:2", "name": "Note:\n" + "x" * 300, "type": "TEXT"}
        line = render_outline(node)[0]
        name = line.split("] ", 1)[1].rsplit(" (id:", 1)[0]
        assert len(name) == OUTLINE_NAME_MAX
        assert name.endswith("…")
        assert "\n" not in line

    def test_render_nodes_outline_mode(self):
        from figma_fetch import render_nodes

        data = {
            "name": "File",
            "nodes": {
                "1:2": {
                    "document": {
                        "id": "1:2",
                        "name": "A",
                        "type": "FRAME",
                        "children": [{"id": "5:6", "name": "B", "type": "TEXT"}],
                    }
                }
            },
        }
        md, missing = render_nodes(data, ["1:2"], 3, outline=True)
        assert "## Figma Layer Outline" in md
        assert "  - [TEXT] B (id: 5:6)" in md
        assert "### Layout" not in md
        assert missing == 0

    def test_render_nodes_resolves_styles_from_entry(self):
        from figma_fetch import render_nodes

        data = {
            "name": "File",
            "nodes": {
                "1:2": {
                    "document": {
                        "id": "1:2",
                        "name": "A",
                        "type": "TEXT",
                        "styles": {"text": "S:1"},
                    },
                    "styles": {"S:1": {"name": "Heading/H1"}},
                }
            },
        }
        md, _ = render_nodes(data, ["1:2"], 3)
        assert "- Styles: text=Heading/H1" in md


# ── figma_export (image fills) ────────────────────────────────────────────────


class TestParseImageRefs:
    @pytest.fixture(autouse=True)
    def _import(self):
        from figma_export import parse_image_refs
        self.func = parse_image_refs

    def test_splits_and_dedupes(self):
        assert self.func("abcdef0123, ABCDEF0123,abcdef0123") == [
            "abcdef0123",
            "ABCDEF0123",
        ]

    def test_rejects_non_hex(self):
        with pytest.raises(ValueError, match="Not an imageRef"):
            self.func("abcdef0123,../etc")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            self.func(" , ")


class TestSniffImageExt:
    @pytest.mark.parametrize(
        "head,ext",
        [
            (b"\xff\xd8\xff\xe0rest", "jpg"),
            (b"GIF89a....", "gif"),
            (b"RIFF\x00\x00\x00\x00WEBPVP8", "webp"),
            (b"  <svg xmlns", "svg"),
            (b"\x89PNG\r\n\x1a\n", "png"),
            (b"", "png"),
        ],
    )
    def test_detects(self, head, ext):
        from figma_export import sniff_image_ext

        assert sniff_image_ext(head) == ext
