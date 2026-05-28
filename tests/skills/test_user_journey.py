"""Tests for user-journey skill scripts.

Covers the pure / deterministic functions in:
    - init_workspace.py (slug + template + design parsing helpers)
    - validate_sync.py  (mermaid extraction + JSON structure validation +
                         drift comparison)

Functions that touch the filesystem are tested with pytest's tmp_path
fixture — never against the real workspace template directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# init_workspace.slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    @pytest.fixture(autouse=True)
    def _import(self):
        from init_workspace import slugify
        self.func = slugify

    def test_basic(self):
        assert self.func("Hello World") == "hello-world"

    def test_chinese_falls_back(self):
        assert self.func("用户旅程") == "untitled"

    def test_strips_punctuation(self):
        assert self.func("Foo & Bar / Baz!") == "foo-bar-baz"

    def test_collapses_separators(self):
        assert self.func("foo   bar___baz") == "foo-bar-baz"

    def test_empty_input(self):
        assert self.func("") == "untitled"
        assert self.func("   ") == "untitled"

    def test_underscores_become_hyphens(self):
        assert self.func("snake_case_name") == "snake-case-name"

    def test_trims_leading_trailing_hyphens(self):
        assert self.func("---abc---") == "abc"

    def test_alphanumeric_preserved(self):
        assert self.func("v1.0.2-beta") == "v102-beta"


# ---------------------------------------------------------------------------
# init_workspace design style helpers
# ---------------------------------------------------------------------------


class TestListDesignStyles:
    @pytest.fixture(autouse=True)
    def _import(self):
        from init_workspace import list_design_styles
        self.func = list_design_styles

    def test_returns_sorted_list_from_dir(self, tmp_path: Path):
        (tmp_path / "zeta.md").write_text("---\n---\n")
        (tmp_path / "alpha.md").write_text("---\n---\n")
        (tmp_path / "mid.md").write_text("---\n---\n")
        assert self.func(tmp_path) == ["alpha", "mid", "zeta"]

    def test_returns_empty_for_missing_dir(self, tmp_path: Path):
        assert self.func(tmp_path / "does-not-exist") == []

    def test_ignores_non_md_files(self, tmp_path: Path):
        (tmp_path / "style.md").write_text("---\n---\n")
        (tmp_path / "notes.txt").write_text("ignore")
        (tmp_path / "README").write_text("ignore")
        assert self.func(tmp_path) == ["style"]

    def test_bundled_presets_are_present(self):
        from init_workspace import list_design_styles as default_lister
        names = default_lister()
        for required in ("corporate-clean", "playful-pastel", "dark-engineering", "editorial-mono"):
            assert required in names, f"missing bundled preset: {required}"


class TestResolveDesignStyle:
    @pytest.fixture(autouse=True)
    def _import(self):
        from init_workspace import resolve_design_style
        self.func = resolve_design_style

    def test_returns_path_for_existing(self, tmp_path: Path):
        target = tmp_path / "foo.md"
        target.write_text("---\n---\n")
        assert self.func("foo", tmp_path) == target

    def test_raises_for_missing(self, tmp_path: Path):
        (tmp_path / "only.md").write_text("---\n---\n")
        with pytest.raises(FileNotFoundError) as excinfo:
            self.func("nope", tmp_path)
        assert "nope" in str(excinfo.value)
        assert "only" in str(excinfo.value)

    def test_rejects_empty_name(self, tmp_path: Path):
        with pytest.raises(ValueError):
            self.func("", tmp_path)


# ---------------------------------------------------------------------------
# init_workspace.build_initial_journey
# ---------------------------------------------------------------------------


class TestBuildInitialJourney:
    @pytest.fixture(autouse=True)
    def _import(self):
        from init_workspace import build_initial_journey
        self.func = build_initial_journey

    def test_default_english_skeleton(self):
        out = self.func(
            title="Demo",
            subtitle="from A to B",
            persona_name="Alice",
            persona_role="user",
            language="en",
        )
        assert out["schema_version"] == "3"
        assert out["title"] == "Demo"
        assert out["language"] == "en"
        assert len(out["personas"]) == 1
        assert out["personas"][0]["id"] == "alice"
        assert [s["label"] for s in out["stages"]] == ["Discover", "Try", "Habit"]
        for stage in out["stages"]:
            assert len(stage["steps"]) == 1
            assert stage["steps"][0]["screen_refs"], "every example step has a screen ref"
        # v3 introduces top-level arrows[] (replaces nested transitions[]).
        assert "arrows" in out
        assert len(out["arrows"]) >= 1
        assert "stickies" in out

    def test_chinese_skeleton(self):
        out = self.func(
            title="演示",
            subtitle="",
            persona_name="主要用户",
            persona_role="用户",
            language="zh",
        )
        assert out["language"] == "zh"
        assert [s["label"] for s in out["stages"]] == ["发现", "尝试", "习惯"]
        assert out["personas"][0]["id"] == "untitled"

    def test_rejects_bad_language(self):
        with pytest.raises(ValueError):
            self.func(
                title="x", subtitle="", persona_name="a",
                persona_role="b", language="fr",
            )

    def test_persona_id_links_to_stages(self):
        out = self.func(
            title="x", subtitle="", persona_name="Bob Smith",
            persona_role="user", language="en",
        )
        persona_id = out["personas"][0]["id"]
        assert persona_id == "bob-smith"
        for stage in out["stages"]:
            assert stage["persona_id"] == persona_id

    def test_stage_ids_are_unique(self):
        out = self.func(
            title="x", subtitle="", persona_name="a",
            persona_role="b", language="en",
        )
        ids = [s["id"] for s in out["stages"]]
        assert len(ids) == len(set(ids))

    def test_v3_screens_are_present_and_wired(self):
        out = self.func(
            title="x", subtitle="", persona_name="a",
            persona_role="b", language="en",
        )
        assert out["schema_version"] == "3"
        screens = out.get("screens", [])
        assert len(screens) == 3
        ids = {s["id"] for s in screens}
        assert ids == {"welcome", "main", "done"}
        for s in screens:
            assert s["kind"]
            assert s["title"]
            assert s["layout"]["type"] in {"stack", "row", "grid"}
            # state is on every screen (color of the outer canvas card)
            assert s.get("state") in {"default", "loading", "success", "error", "warning"}
            # In v3 transitions[] is GONE from screens — they live at top level as arrows[].
            assert "transitions" not in s

        # top-level arrows wire screens together
        arrows = out.get("arrows", [])
        assert arrows, "v3 seed must include arrows[] at top level"
        # at least one is_default arrow
        assert any(a.get("is_default") for a in arrows)
        # arrows reference real screens
        for a in arrows:
            from_screen = a["from"].split("#", 1)[0]
            to_screen = a["to"]
            assert from_screen in ids, f"arrow.from references unknown screen: {a['from']}"
            assert to_screen in ids, f"arrow.to references unknown screen: {a['to']}"

        # every step references its corresponding screen by id
        step_refs = [
            stage["steps"][0]["screen_refs"][0]
            for stage in out["stages"]
        ]
        assert step_refs == ["welcome", "main", "done"]


# ---------------------------------------------------------------------------
# init_workspace.build_mermaid (uses shared escape_label_for_mermaid)
# ---------------------------------------------------------------------------


class TestBuildMermaid:
    @pytest.fixture(autouse=True)
    def _import(self):
        from init_workspace import build_mermaid
        self.func = build_mermaid

    def test_renders_nodes_and_edges(self):
        journey = {
            "stages": [
                {"id": "a", "label": "Step A"},
                {"id": "b", "label": "Step B"},
                {"id": "c", "label": "Step C"},
            ]
        }
        out = self.func(journey)
        # Plain labels need no quotes — that is the correct, safe form
        # for mermaid 10.2.3+ and avoids superfluous quoting noise.
        assert "a[Step A]" in out
        assert "b[Step B]" in out
        assert "a --> b" in out
        assert "b --> c" in out

    def test_single_stage_has_no_edges(self):
        out = self.func({"stages": [{"id": "only", "label": "Only"}]})
        assert "only" in out
        assert "-->" not in out

    def test_empty_stages_returns_comment(self):
        out = self.func({"stages": []})
        assert "%%" in out

    def test_no_stages_key_returns_comment(self):
        out = self.func({})
        assert "%%" in out

    def test_label_with_parens_is_quoted(self):
        """Labels containing parens must be wrapped in double quotes."""
        out = self.func({"stages": [{"id": "n", "label": "xxx-api (Domain API)"}]})
        assert 'n["xxx-api (Domain API)"]' in out

    def test_label_with_newline_uses_br(self):
        """Real newlines must become <br/>, never the literal `\\n`."""
        out = self.func({"stages": [{"id": "n", "label": "xxx-api\n(Domain API)"}]})
        assert 'n["xxx-api<br/>(Domain API)"]' in out
        assert "\\n" not in out
        # And there must be no literal newline inside the rendered node.
        node_line = next(line for line in out.splitlines() if line.strip().startswith("n["))
        assert "\n" not in node_line

    def test_label_with_literal_backslash_n_uses_br(self):
        """A model that writes `xxx\\n(Domain)` (two literal chars) must be fixed too."""
        out = self.func({"stages": [{"id": "n", "label": "xxx-api\\n(Domain API)"}]})
        assert 'n["xxx-api<br/>(Domain API)"]' in out

    def test_chinese_label_with_newline_uses_br(self):
        out = self.func({"stages": [{"id": "n", "label": "发现\n试用"}]})
        assert 'n["发现<br/>试用"]' in out


class TestInitWorkspaceUsesSharedEscape:
    """Sanity check that init_workspace imports the shared escape helper."""

    def test_escape_label_for_mermaid_re_exported(self):
        from init_workspace import escape_label_for_mermaid

        assert escape_label_for_mermaid("xxx-api\n(Domain API)") == (
            '"xxx-api<br/>(Domain API)"'
        )


# ---------------------------------------------------------------------------
# init_workspace.parse_design_frontmatter
# ---------------------------------------------------------------------------


class TestParseDesignFrontmatter:
    @pytest.fixture(autouse=True)
    def _import(self):
        from init_workspace import parse_design_frontmatter
        self.func = parse_design_frontmatter

    def test_parses_colors_and_typography(self):
        md = (
            "---\n"
            "version: alpha\n"
            "colors:\n"
            "  primary: \"#1A1C1E\"\n"
            "  secondary: \"#6C7278\"\n"
            "typography:\n"
            "  h1:\n"
            "    fontFamily: Inter\n"
            "    fontSize: 32px\n"
            "rounded:\n"
            "  sm: 4px\n"
            "  md: 8px\n"
            "---\n"
            "# heading\n"
        )
        out = self.func(md)
        assert out["version"] == "alpha"
        assert out["colors"]["primary"] == "#1A1C1E"
        assert out["typography"]["h1"]["fontFamily"] == "Inter"
        assert out["typography"]["h1"]["fontSize"] == "32px"
        assert out["rounded"]["sm"] == "4px"

    def test_no_frontmatter_returns_empty(self):
        assert self.func("# heading only") == {}

    def test_unterminated_frontmatter_returns_empty(self):
        assert self.func("---\nfoo: bar\nbaz: qux\n") == {}

    def test_bundled_presets_all_parse(self):
        from init_workspace import DESIGN_STYLES_DIR
        for path in DESIGN_STYLES_DIR.glob("*.md"):
            md = path.read_text(encoding="utf-8")
            out = self.func(md)
            assert "colors" in out, f"missing colors in {path.name}"
            assert "primary" in out["colors"], f"no primary in {path.name}"


# ---------------------------------------------------------------------------
# init_workspace.render_template
# ---------------------------------------------------------------------------


class TestRenderTemplate:
    @pytest.fixture(autouse=True)
    def _import(self):
        from init_workspace import render_template
        self.func = render_template

    def test_substitutes_all_tokens(self):
        tpl = "{{TITLE}} | {{SUBTITLE}} | {{LANG}} | {{PERSONA_NAME}}"
        out = self.func(
            tpl,
            title="T", subtitle="S", language="en",
            persona_name="P", persona_slug="p",
            persona_role="r", first_stage_label="L",
            mermaid_body="m", date="d",
            journey_json="{}", design_tokens_json="{}",
        )
        assert out == "T | S | en | P"

    def test_unknown_tokens_pass_through(self):
        out = self.func(
            "{{UNKNOWN}} {{TITLE}}",
            title="hi", subtitle="", language="en",
            persona_name="", persona_slug="", persona_role="",
            first_stage_label="", mermaid_body="",
            date="", journey_json="", design_tokens_json="",
        )
        assert out == "{{UNKNOWN}} hi"


# ---------------------------------------------------------------------------
# validate_sync.normalize_id and slug helpers
# ---------------------------------------------------------------------------


class TestNormalizeId:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_sync import normalize_id
        self.func = normalize_id

    def test_strips_and_lowers(self):
        assert self.func("  Foo  ") == "foo"

    def test_handles_none(self):
        assert self.func("") == ""


# ---------------------------------------------------------------------------
# validate_sync.extract_mermaid_node_ids
# ---------------------------------------------------------------------------


class TestExtractMermaidNodeIds:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_sync import extract_mermaid_node_ids
        self.func = extract_mermaid_node_ids

    def test_simple_flowchart(self):
        md = (
            "# Title\n\n"
            "```mermaid\n"
            "flowchart LR\n"
            "    a[\"A\"]\n"
            "    b[\"B\"]\n"
            "    c[\"C\"]\n"
            "    a --> b\n"
            "    b --> c\n"
            "```\n"
        )
        assert self.func(md) == ["a", "b", "c"]

    def test_edges_only(self):
        md = "```mermaid\nflowchart LR\n  alpha --> beta\n  beta --> gamma\n```\n"
        assert self.func(md) == ["alpha", "beta", "gamma"]

    def test_no_block_returns_empty(self):
        assert self.func("just prose, no mermaid") == []

    def test_skips_directive_lines(self):
        md = "```mermaid\ngraph TD\n%% a comment\n  x --> y\n```\n"
        assert self.func(md) == ["x", "y"]

    def test_deduplicates(self):
        md = "```mermaid\nflowchart LR\n  a --> b\n  b --> a\n```\n"
        assert self.func(md) == ["a", "b"]


# ---------------------------------------------------------------------------
# validate_sync.extract_stage_subsection_ids
# ---------------------------------------------------------------------------


class TestExtractStageSubsectionIds:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_sync import extract_stage_subsection_ids
        self.func = extract_stage_subsection_ids

    def test_extracts_after_stages_heading(self):
        md = (
            "# T\n## Personas\n### Bob\n## Stages\n"
            "### 1. Discover\nblah\n"
            "### 2. Sign up\nblah\n"
            "### 3. Browse & order\nblah\n"
            "## Open Questions\n### 4. ignored\n"
        )
        assert self.func(md) == ["discover", "sign-up", "browse-order"]

    def test_handles_no_stages_section(self):
        assert self.func("# title\n## Personas\n### only\n") == []

    def test_stops_at_next_h2(self):
        md = (
            "## Stages\n### 1. One\n"
            "## Other Section\n### 2. Should not appear\n"
        )
        assert self.func(md) == ["one"]


# ---------------------------------------------------------------------------
# validate_sync.validate_journey_structure
# ---------------------------------------------------------------------------


def _good_journey() -> dict:
    return {
        "schema_version": "1",
        "title": "ok",
        "language": "en",
        "personas": [{"id": "u", "name": "U", "role": "r"}],
        "stages": [
            {
                "id": "discover", "label": "Discover", "persona_id": "u",
                "steps": [{"id": "s1", "emotion": "neutral"}],
            }
        ],
    }


class TestValidateJourneyStructure:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_sync import validate_journey_structure
        self.func = validate_journey_structure

    def test_good_journey_passes(self):
        assert self.func(_good_journey()) == []

    def test_missing_title_errors(self):
        j = _good_journey(); j["title"] = ""
        errs = self.func(j)
        assert any("title" in e for e in errs)

    def test_bad_language_errors(self):
        j = _good_journey(); j["language"] = "fr"
        errs = self.func(j)
        assert any("language" in e for e in errs)

    def test_duplicate_persona_id(self):
        j = _good_journey()
        j["personas"].append({"id": "u", "name": "Other"})
        errs = self.func(j)
        assert any("duplicate persona" in e for e in errs)

    def test_persona_id_reference_missing(self):
        j = _good_journey()
        j["stages"][0]["persona_id"] = "ghost"
        errs = self.func(j)
        assert any("not in defined personas" in e for e in errs)

    def test_too_many_stages_errors(self):
        j = _good_journey()
        j["stages"] = [
            {"id": f"s{i}", "label": f"S{i}", "steps": []} for i in range(8)
        ]
        errs = self.func(j)
        assert any("too many stages" in e.lower() for e in errs)

    def test_duplicate_stage_id(self):
        j = _good_journey()
        j["stages"].append({
            "id": "discover", "label": "Dup", "persona_id": "u", "steps": [],
        })
        errs = self.func(j)
        assert any("duplicate stage" in e for e in errs)

    def test_bad_emotion(self):
        j = _good_journey()
        j["stages"][0]["steps"][0]["emotion"] = "ecstatic"
        errs = self.func(j)
        assert any("emotion" in e for e in errs)

    def test_missing_personas_errors(self):
        j = _good_journey(); j["personas"] = []
        errs = self.func(j)
        assert any("persona" in e for e in errs)


# ---------------------------------------------------------------------------
# validate_sync.compare_sync
# ---------------------------------------------------------------------------


class TestCompareSync:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_sync import compare_sync
        self.func = compare_sync

    def test_in_sync(self):
        journey = _good_journey()
        md = (
            "# ok\n## Stages\n"
            "```mermaid\nflowchart LR\n  discover[\"Discover\"]\n```\n"
            "### 1. Discover\n"
        )
        r = self.func(journey, md)
        assert r["errors"] == []
        assert not any("missing stages" in w for w in r["warnings"])

    def test_missing_in_mermaid_errors(self):
        journey = _good_journey()
        journey["stages"].append({
            "id": "extra", "label": "Extra", "persona_id": "u", "steps": [],
        })
        md = (
            "# ok\n## Stages\n"
            "```mermaid\nflowchart LR\n  discover[\"Discover\"]\n```\n"
            "### 1. Discover\n### 2. Extra\n"
        )
        r = self.func(journey, md)
        assert any("missing stages defined in journey.json" in e for e in r["errors"])

    def test_extra_in_mermaid_errors(self):
        journey = _good_journey()
        md = (
            "# ok\n## Stages\n"
            "```mermaid\nflowchart LR\n  discover --> phantom\n```\n"
            "### 1. Discover\n"
        )
        r = self.func(journey, md)
        assert any("stages not in journey.json" in e for e in r["errors"])

    def test_h1_mismatch_is_info(self):
        journey = _good_journey()
        journey["title"] = "Different Title"
        md = (
            "# Old Title\n## Stages\n"
            "```mermaid\nflowchart LR\n  discover[\"Discover\"]\n```\n"
            "### 1. Discover\n"
        )
        r = self.func(journey, md)
        assert any("H1" in i for i in r["info"])

    def test_skeleton_warns_only_as_info(self):
        """When JOURNEY.md has fewer subsections than JSON stages, it's INFO,
        not warning — the AI is in the middle of authoring."""
        journey = _good_journey()
        journey["stages"].extend([
            {"id": "try", "label": "Try", "persona_id": "u", "steps": []},
            {"id": "habit", "label": "Habit", "persona_id": "u", "steps": []},
        ])
        md = (
            "# ok\n## Stages\n"
            "```mermaid\nflowchart LR\n  discover --> try --> habit\n```\n"
            "### 1. Discover\n"
        )
        r = self.func(journey, md)
        assert r["errors"] == []
        assert any("fill in the remaining" in i for i in r["info"])


# ---------------------------------------------------------------------------
# validate_sync.validate_workspace (filesystem)
# ---------------------------------------------------------------------------


class TestValidateWorkspace:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_sync import validate_workspace
        self.func = validate_workspace

    def test_missing_files_returns_structure_error(self, tmp_path: Path):
        r = self.func(tmp_path)
        assert r["structure_ok"] is False
        assert any("missing" in e for e in r["errors"])

    def test_invalid_json_returns_structure_error(self, tmp_path: Path):
        (tmp_path / "journey.json").write_text("not json")
        (tmp_path / "JOURNEY.md").write_text("# x\n")
        r = self.func(tmp_path)
        assert r["structure_ok"] is False

    def test_good_workspace_passes(self, tmp_path: Path):
        journey = _good_journey()
        (tmp_path / "journey.json").write_text(json.dumps(journey))
        (tmp_path / "JOURNEY.md").write_text(
            "# ok\n## Stages\n"
            "```mermaid\nflowchart LR\n  discover[\"Discover\"]\n```\n"
            "### 1. Discover\n"
        )
        r = self.func(tmp_path)
        assert r["structure_ok"] is True
        assert r["errors"] == []

    def test_schema_v2_is_accepted(self, tmp_path: Path):
        journey = _good_journey()
        journey["schema_version"] = "2"
        journey["screens"] = []
        (tmp_path / "journey.json").write_text(json.dumps(journey))
        (tmp_path / "JOURNEY.md").write_text(
            "# ok\n## Stages\n"
            "```mermaid\nflowchart LR\n  discover[\"Discover\"]\n```\n"
            "### 1. Discover\n"
        )
        r = self.func(tmp_path)
        assert r["structure_ok"] is True
        assert r["errors"] == []

    def test_unsupported_schema_version_errors(self, tmp_path: Path):
        journey = _good_journey()
        journey["schema_version"] = "99"
        (tmp_path / "journey.json").write_text(json.dumps(journey))
        (tmp_path / "JOURNEY.md").write_text(
            "# ok\n## Stages\n"
            "```mermaid\nflowchart LR\n  discover[\"Discover\"]\n```\n"
            "### 1. Discover\n"
        )
        r = self.func(tmp_path)
        assert any("schema_version" in e for e in r["errors"])

    def test_schema_v3_is_accepted(self, tmp_path: Path):
        journey = _good_journey()
        journey["schema_version"] = "3"
        journey["screens"] = []
        journey["arrows"] = []
        (tmp_path / "journey.json").write_text(json.dumps(journey))
        (tmp_path / "JOURNEY.md").write_text(
            "# ok\n## Stages\n"
            "```mermaid\nflowchart LR\n  discover[\"Discover\"]\n```\n"
            "### 1. Discover\n"
        )
        r = self.func(tmp_path)
        assert r["structure_ok"] is True
        assert r["errors"] == []


# ---------------------------------------------------------------------------
# validate_screens.collect_element_ids + find_interactive_without_id
# ---------------------------------------------------------------------------


class TestCollectElementIds:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import collect_element_ids
        self.func = collect_element_ids

    def test_flat_layout(self):
        layout = {
            "type": "stack",
            "elements": [
                {"type": "button", "id": "go"},
                {"type": "text", "label": "hi"},
            ],
        }
        assert self.func(layout) == {"go"}

    def test_nested_grid(self):
        layout = {
            "type": "stack",
            "elements": [
                {
                    "type": "grid",
                    "cols": 3,
                    "elements": [
                        {"type": "keypad-button", "id": "k1"},
                        {"type": "keypad-button", "id": "k2"},
                    ],
                },
                {"type": "button", "id": "confirm"},
            ],
        }
        assert self.func(layout) == {"k1", "k2", "confirm"}

    def test_handles_missing_or_string(self):
        assert self.func(None) == set()
        assert self.func({}) == set()


class TestFindInteractiveWithoutId:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import find_interactive_without_id
        self.func = find_interactive_without_id

    def test_flags_interactive_without_id(self):
        layout = {
            "type": "stack",
            "elements": [
                {"type": "button", "label": "go", "interactive": True},
                {"type": "button", "id": "ok", "label": "ok", "interactive": True},
            ],
        }
        assert self.func(layout) == ["button"]

    def test_ignores_non_interactive(self):
        layout = {
            "type": "stack",
            "elements": [
                {"type": "text", "label": "hello"},
                {"type": "button", "label": "go", "interactive": False},
            ],
        }
        assert self.func(layout) == []


# ---------------------------------------------------------------------------
# validate_screens.validate_screens (8 rules)
# ---------------------------------------------------------------------------


def _screen(id_: str, layout=None) -> dict:
    return {
        "id": id_,
        "kind": "mobile-screen",
        "title": id_,
        "stage_id": "s1",
        "state": "default",
        "layout": layout or {
            "type": "stack",
            "elements": [
                {"type": "button", "id": "go", "label": "Go", "interactive": True},
            ],
        },
    }


class TestValidateScreens:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import validate_screens
        self.func = validate_screens

    def test_empty_passes(self):
        out = self.func([], [], [])
        assert out["errors"] == []
        assert out["warnings"] == []

    def test_unique_screen_ids(self):
        out = self.func([_screen("a"), _screen("a")], [], [])
        assert any("duplicate screen id" in e for e in out["errors"])

    def test_arrow_to_missing_screen(self):
        screens = [_screen("a")]
        arrows = [{"from": "a#go", "to": "ghost", "label": "go to ghost", "trigger": "tap"}]
        out = self.func(screens, [], arrows)
        assert any("'ghost'" in e for e in out["errors"])

    def test_arrow_from_element_missing(self):
        screens = [_screen("a")]
        arrows = [{"from": "a#nope", "to": "a", "label": "loop", "trigger": "tap"}]
        out = self.func(screens, [], arrows)
        assert any("'nope' not found" in e for e in out["errors"])

    def test_arrow_whole_screen_is_allowed(self):
        screens = [_screen("a")]
        arrows = [{"from": "a", "to": "a", "label": "self-loop (no element anchor)", "trigger": "auto"}]
        out = self.func(screens, [], arrows)
        assert out["errors"] == []

    def test_arrow_from_screen_missing(self):
        screens = [_screen("a")]
        arrows = [{"from": "ghost#go", "to": "a", "label": "bad source", "trigger": "tap"}]
        out = self.func(screens, [], arrows)
        assert any("'ghost' does not exist" in e for e in out["errors"])

    def test_step_screen_refs_resolved(self):
        screens = [_screen("a")]
        stages = [{
            "id": "s1", "label": "S1", "steps": [
                {"id": "t1", "screen_refs": ["a"]},
                {"id": "t2", "screen_refs": ["ghost"]},
            ],
        }]
        out = self.func(screens, stages, [])
        assert any("screen_refs[0]='ghost'" in e for e in out["errors"])

    def test_orphan_screen_warns(self):
        screens = [_screen("a"), _screen("b")]
        stages = [{"id": "s1", "label": "S1", "steps": [{"id": "t1", "screen_refs": ["a"]}]}]
        out = self.func(screens, stages, [])
        assert any("'b'" in w and "no incoming" in w for w in out["warnings"])

    def test_multiple_defaults_per_source_error(self):
        screens = [_screen("a")]
        arrows = [
            {"from": "a#go", "to": "a", "label": "loop1", "trigger": "tap", "is_default": True},
            {"from": "a#go", "to": "a", "label": "loop2", "trigger": "tap", "is_default": True},
        ]
        out = self.func(screens, [], arrows)
        assert any("is_default=true" in e for e in out["errors"])

    def test_interactive_without_id_warns(self):
        screens = [{
            "id": "a", "kind": "mobile-screen", "title": "a",
            "stage_id": "s1", "state": "default",
            "layout": {
                "type": "stack",
                "elements": [
                    {"type": "button", "label": "no id", "interactive": True},
                ],
            },
        }]
        stages = [{"id": "s1", "label": "S1", "steps": [{"id": "t1", "screen_refs": ["a"]}]}]
        out = self.func(screens, stages, [])
        assert any("without id" in w for w in out["warnings"])

    def test_dead_end_middle_screen_infos(self):
        # `a` has an arrow to `b`; `b` is a dead-end mid-flow (referenced in
        # step 2 of 2 in stage s1, but s1 is NOT the last stage).
        screens = [_screen("a"), _screen("b")]
        stages = [{
            "id": "s1", "label": "S1", "steps": [
                {"id": "t1", "screen_refs": ["a"]},
                {"id": "t2", "screen_refs": ["b"]},
            ],
        }, {
            "id": "s2", "label": "S2", "steps": [
                {"id": "t3", "screen_refs": ["a"]},
            ],
        }]
        arrows = [{"from": "a#go", "to": "b", "label": "a→b", "trigger": "tap"}]
        out = self.func(screens, stages, arrows)
        assert any("no outgoing arrows" in i for i in out["info"])

    def test_invalid_state_errors(self):
        screen = _screen("a")
        screen["state"] = "ecstatic"
        out = self.func([screen], [], [])
        assert any("invalid state" in e for e in out["errors"])

    def test_invalid_arrow_kind_errors(self):
        screens = [_screen("a")]
        arrows = [{"from": "a#go", "to": "a", "kind": "whoops", "trigger": "tap"}]
        out = self.func(screens, [], arrows)
        assert any("invalid kind" in e for e in out["errors"])

    def test_invalid_position_errors(self):
        screen = _screen("a")
        screen["position"] = "0,0"  # must be a {x, y} object
        out = self.func([screen], [], [])
        assert any("position" in e for e in out["errors"])


# ---------------------------------------------------------------------------
# Design-pattern sense (flat-stack-soup detector)
# ---------------------------------------------------------------------------


class TestAssessDesignPatternSense:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import assess_design_pattern_sense
        self.func = assess_design_pattern_sense

    def test_flat_stack_soup_detected(self):
        screen = {
            "id": "soup",
            "layout": {
                "type": "stack",
                "elements": [{"type": "button", "label": str(i)} for i in range(10)],
            },
        }
        msgs = self.func(screen)
        assert any(m.startswith("[flat-stack]") for m in msgs)

    def test_no_hierarchy_detected(self):
        screen = {
            "id": "bare",
            "layout": {
                "type": "stack",
                "elements": [
                    {"type": "text", "label": "a"},
                    {"type": "text", "label": "b"},
                    {"type": "text", "label": "c"},
                    {"type": "text", "label": "d"},
                    {"type": "text", "label": "e"},
                ],
            },
        }
        msgs = self.func(screen)
        assert any(m.startswith("[no-hierarchy]") for m in msgs)

    def test_monotonous_detected(self):
        screen = {
            "id": "mono",
            "layout": {
                "type": "stack",
                "elements": [
                    {"type": "app-bar", "title": "M"},
                    *[{"type": "text", "label": str(i)} for i in range(8)],
                ],
            },
        }
        msgs = self.func(screen)
        assert any(m.startswith("[monotonous]") for m in msgs)

    def test_monotonous_exempt_for_keypad_button(self):
        # 12 keypad-buttons in a grid is a legit keypad, not monotony.
        screen = {
            "id": "keypad",
            "layout": {
                "type": "stack",
                "elements": [
                    {"type": "app-bar", "title": "PIN"},
                    {"type": "grid", "cols": 3, "elements": [
                        {"type": "keypad-button", "label": str(i)} for i in range(12)
                    ]},
                ],
            },
        }
        msgs = self.func(screen)
        assert not any(m.startswith("[monotonous]") for m in msgs)

    def test_monotonous_exempt_for_list_items(self):
        # A list of list-items is a legit list, not monotony.
        screen = {
            "id": "list",
            "layout": {
                "type": "stack",
                "elements": [
                    {"type": "app-bar", "title": "Items"},
                    {"type": "section", "title": "All", "elements": [
                        {"type": "list-item", "title": f"Row {i}"} for i in range(8)
                    ]},
                ],
            },
        }
        msgs = self.func(screen)
        assert not any(m.startswith("[monotonous]") for m in msgs)

    def test_overstuffed_section_detected(self):
        screen = {
            "id": "stuffed",
            "layout": {
                "type": "stack",
                "elements": [
                    {"type": "app-bar", "title": "S"},
                    {"type": "section", "title": "Big", "elements": [
                        {"type": "list-item", "title": str(i)} for i in range(10)
                    ]},
                ],
            },
        }
        msgs = self.func(screen)
        assert any(m.startswith("[overstuffed]") for m in msgs)

    def test_clean_composed_screen_has_no_warnings(self):
        screen = {
            "id": "clean",
            "layout": {
                "type": "stack",
                "elements": [
                    {"type": "app-bar", "title": "Home"},
                    {"type": "section", "title": "A", "elements": [
                        {"type": "text", "label": "hi"},
                        {"type": "button", "label": "go"},
                    ]},
                    {"type": "section", "title": "B", "elements": [
                        {"type": "alert", "severity": "info", "title": "i"},
                    ]},
                    {"type": "footer-bar", "actions": [
                        {"label": "OK", "variant": "primary"}
                    ]},
                ],
            },
        }
        assert self.func(screen) == []

    def test_small_screen_skipped(self):
        # Few elements + no clear hierarchy is still acceptable when the
        # screen is small (≤ 4 atoms). Don't nag the user.
        screen = {
            "id": "small",
            "layout": {
                "type": "stack",
                "elements": [
                    {"type": "text", "label": "one"},
                    {"type": "text", "label": "two"},
                    {"type": "button", "label": "go"},
                ],
            },
        }
        assert self.func(screen) == []

    def test_non_dict_input_safe(self):
        assert self.func(None) == []
        assert self.func({"id": "x"}) == []
        assert self.func({"id": "x", "layout": "not-an-object"}) == []


class TestNewPrimitiveIdsAreCollected:
    """The validator must walk into the new composition primitives
    (app-bar actions, footer-bar actions, tab-bar items, key-value-list
    items) so that arrows whose `from` references e.g. `home#search`
    resolve correctly."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import collect_element_ids
        self.func = collect_element_ids

    def test_app_bar_action_ids(self):
        layout = {
            "type": "stack",
            "elements": [
                {"type": "app-bar", "title": "X", "actions": [
                    {"icon": "search", "id": "search"},
                    {"icon": "settings", "id": "settings"},
                ]}
            ],
        }
        assert self.func(layout) >= {"search", "settings"}

    def test_footer_bar_action_ids(self):
        layout = {
            "type": "stack",
            "elements": [
                {"type": "footer-bar", "actions": [
                    {"label": "Cancel", "id": "cancel"},
                    {"label": "Confirm", "id": "confirm"},
                ]}
            ],
        }
        assert self.func(layout) >= {"cancel", "confirm"}

    def test_tab_bar_item_ids(self):
        layout = {
            "type": "stack",
            "elements": [
                {"type": "tab-bar", "items": [
                    {"id": "tab-home", "label": "Home"},
                    {"id": "tab-me", "label": "Me"},
                ]}
            ],
        }
        assert self.func(layout) >= {"tab-home", "tab-me"}

    def test_section_descended_into(self):
        layout = {
            "type": "stack",
            "elements": [
                {"type": "section", "title": "S", "elements": [
                    {"type": "button", "id": "btn-inside-section", "label": "X"},
                ]}
            ],
        }
        assert "btn-inside-section" in self.func(layout)

    def test_empty_state_action_id(self):
        layout = {
            "type": "stack",
            "elements": [
                {"type": "empty-state",
                  "title": "X",
                  "action": {"label": "Go", "id": "go-from-empty"}}
            ],
        }
        assert "go-from-empty" in self.func(layout)

    def test_alert_action_id(self):
        layout = {
            "type": "stack",
            "elements": [
                {"type": "alert",
                  "severity": "info",
                  "title": "T",
                  "action": {"label": "Learn", "id": "alert-learn"}}
            ],
        }
        assert "alert-learn" in self.func(layout)

    def test_section_action_id(self):
        layout = {
            "type": "stack",
            "elements": [
                {"type": "section",
                  "title": "S",
                  "action": {"label": "See all", "id": "see-all"},
                  "elements": []}
            ],
        }
        assert "see-all" in self.func(layout)

    def test_arrow_to_app_bar_action_resolves(self):
        # End-to-end through validate_screens — ensure arrows that
        # target an app-bar action don't get falsely rejected.
        from validate_screens import validate_screens
        screens = [{
            "id": "home", "kind": "mobile-screen", "title": "Home",
            "stage_id": "s1", "state": "default",
            "layout": {
                "type": "stack",
                "elements": [
                    {"type": "app-bar", "title": "Home", "actions": [
                        {"icon": "search", "id": "search"},
                    ]},
                    {"type": "footer-bar", "actions": [
                        {"label": "Go", "id": "go-btn", "interactive": True},
                    ]},
                ],
            },
        }]
        arrows = [
            {"from": "home#search", "to": "home", "label": "search", "trigger": "tap"},
            {"from": "home#go-btn", "to": "home", "label": "go",     "trigger": "tap"},
        ]
        out = validate_screens(screens, [], arrows)
        assert out["errors"] == []


# ---------------------------------------------------------------------------
# Device-aware seed screens (build_initial_journey + device_kind)
# ---------------------------------------------------------------------------


def _walk_types(layout: dict | None) -> list[str]:
    """Helper: flatten all type names in a layout tree (containers + keys)."""
    out: list[str] = []
    if not isinstance(layout, dict):
        return out

    def visit(node):
        if not isinstance(node, dict):
            return
        t = node.get("type")
        if t:
            out.append(t)
        if t in {"stack", "grid", "row"}:
            for child in node.get("elements", []) or []:
                visit(child)
        elif t == "side-key-rail":
            for k in node.get("keys", []) or []:
                if isinstance(k, dict):
                    out.append("side-key")

    visit(layout)
    return out


class TestSeedScreensByDeviceKind:
    """Each --device-kind value must produce a seed journey that opens into
    a representative Flow view for that device, NOT a generic mobile shell."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from init_workspace import build_initial_journey
        self.build = build_initial_journey

    def _journey(self, kind: str) -> dict:
        return self.build(
            title="X", subtitle="", persona_name="U", persona_role="r",
            language="en", device_kind=kind,
        )

    def test_default_device_kind_is_mobile(self):
        # No explicit kind → mobile shape, matching the previous seed
        out = self.build(
            title="X", subtitle="", persona_name="U", persona_role="r",
            language="en",
        )
        kinds = {s["kind"] for s in out["screens"]}
        assert kinds == {"mobile-screen"}

    def test_rejects_bad_device_kind(self):
        with pytest.raises(ValueError):
            self._journey("watch")

    @pytest.mark.parametrize("kind,expected_screen_kind", [
        ("mobile",  "mobile-screen"),
        ("atm",     "atm-screen"),
        ("kiosk",   "kiosk-screen"),
        ("desktop", "desktop-window"),
        ("tv",      "tv-screen"),
    ])
    def test_each_kind_produces_correct_screen_kind(self, kind, expected_screen_kind):
        out = self._journey(kind)
        assert all(s["kind"] == expected_screen_kind for s in out["screens"])

    def test_atm_seed_uses_device_vocabulary(self):
        """The ATM seed must use chrome + side-key-rail + hardware-slot.
        This is the regression test for the 'ATM looks like a phone' bug."""
        out = self._journey("atm")
        # at least one screen must have chrome="panel"
        chromed = [s for s in out["screens"] if s.get("chrome") == "panel"]
        assert chromed, "ATM seed must have at least one chrome='panel' screen"
        # at least one screen must declare hardware[] slots
        with_hw = [s for s in out["screens"] if s.get("hardware")]
        assert with_hw, "ATM seed must have at least one screen with hardware[]"
        # at least one screen must use side-key-rail in its layout
        rail_screens = [
            s for s in out["screens"]
            if "side-key-rail" in _walk_types(s.get("layout"))
        ]
        assert rail_screens, "ATM seed must use side-key-rail for the main menu"

    def test_kiosk_seed_uses_hardware(self):
        out = self._journey("kiosk")
        with_hw = [s for s in out["screens"] if s.get("hardware")]
        assert with_hw, "kiosk seed must have at least one screen with hardware[]"

    def test_desktop_seed_does_not_use_atm_vocab(self):
        """Desktop seeds must NOT reach for side-key-rail / hardware-slot —
        those would render visually wrong on a desktop window."""
        out = self._journey("desktop")
        for s in out["screens"]:
            assert not s.get("chrome"), "desktop screens must not use chrome=panel"
            assert not s.get("hardware"), "desktop screens must not declare hardware[]"
            assert "side-key-rail" not in _walk_types(s.get("layout"))

    def test_tv_seed_uses_carousel_grid(self):
        out = self._journey("tv")
        home = out["screens"][0]
        types = _walk_types(home.get("layout"))
        assert "grid" in types, "TV home seed should use a horizontal grid"

    def test_seed_persists_device_kind_in_metadata(self):
        out = self._journey("atm")
        assert out.get("metadata", {}).get("seed_device_kind") == "atm"

    def test_seed_screens_pass_screens_validator(self):
        """End-to-end: each device-kind seed should pass `validate_screens`
        (no errors and no device-modeling warnings)."""
        from validate_screens import validate_screens
        for kind in ["mobile", "atm", "kiosk", "desktop", "tv"]:
            out = self._journey(kind)
            report = validate_screens(
                out["screens"], out["stages"], out.get("arrows", []),
            )
            assert report["errors"] == [], f"{kind} seed has errors: {report['errors']}"
            # Device-modeling warning should NOT fire on any seed
            device_warnings = [
                w for w in report["warnings"]
                if "modeled as mobile" in w or "modeled as a mobile" in w
            ]
            assert device_warnings == [], (
                f"{kind} seed wrongly triggered device-modeling warning: "
                f"{device_warnings}"
            )


# ---------------------------------------------------------------------------
# validate_screens: device-specific element resolution
# ---------------------------------------------------------------------------


class TestCollectElementIdsIncludesDeviceElements:
    """`from_element` references must resolve to side-key-rail keys and to
    top-level screen.hardware[] slot ids — not just to layout-tree element ids."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import collect_element_ids, collect_hardware_ids
        self.collect_layout = collect_element_ids
        self.collect_hardware = collect_hardware_ids

    def test_side_key_rail_keys_collected(self):
        layout = {
            "type": "row",
            "elements": [
                {"type": "side-key-rail", "side": "left", "keys": [
                    {"id": "k-withdraw", "label": "W", "interactive": True},
                    {"id": "k-deposit",  "label": "D", "interactive": True},
                ]},
                {"type": "stack", "elements": [{"type": "text", "label": "hi"}]},
            ],
        }
        assert self.collect_layout(layout) == {"k-withdraw", "k-deposit"}

    def test_hardware_slot_inline_in_layout(self):
        layout = {"type": "stack", "elements": [
            {"type": "hardware-slot", "id": "h-card", "slot": "card-reader"},
        ]}
        assert self.collect_layout(layout) == {"h-card"}

    def test_hardware_at_screen_top_level(self):
        screen = {
            "hardware": [
                {"id": "h-cash", "slot": "cash-out", "position": "bottom"},
                {"slot": "receipt", "position": "bottom"},
            ],
        }
        assert self.collect_hardware(screen) == {"h-cash"}

    def test_hardware_none_returns_empty_set(self):
        assert self.collect_hardware({}) == set()
        assert self.collect_hardware(None) == set()


class TestArrowFromElementResolvesDeviceVocab:
    """An arrow with `from='menu#k-withdraw'` (a side-key id) or
    `from='wel#h-card'` (a hardware-slot id) must NOT report
    'element not found'."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import validate_screens
        self.func = validate_screens

    def test_side_key_id_resolves(self):
        screen = {
            "id": "menu", "kind": "atm-screen", "title": "Menu",
            "stage_id": "s1", "state": "default",
            "chrome": "panel",
            "layout": {"type": "row", "elements": [
                {"type": "side-key-rail", "side": "left", "keys": [
                    {"id": "k-w", "label": "W", "interactive": True},
                ]},
            ]},
        }
        arrows = [{"from": "menu#k-w", "to": "menu", "label": "loop", "trigger": "tap", "is_default": True}]
        out = self.func([screen], [], arrows)
        assert out["errors"] == []

    def test_hardware_id_resolves(self):
        screen = {
            "id": "wel", "kind": "atm-screen", "title": "Welcome",
            "stage_id": "s1", "state": "default",
            "chrome": "panel",
            "hardware": [
                {"id": "h-card", "slot": "card-reader", "position": "top"},
            ],
            "layout": {"type": "stack", "elements": [
                {"type": "text", "label": "Insert card"},
            ]},
        }
        arrows = [{"from": "wel#h-card", "to": "wel", "label": "loop", "trigger": "insert-card", "is_default": True}]
        out = self.func([screen], [], arrows)
        assert out["errors"] == []


class TestDeviceAwareModelingCheck:
    """An atm-screen / kiosk-screen journey with NO chrome / side-key-rail /
    hardware-slot anywhere in any screen of that kind must warn."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import validate_screens, screen_has_device_specific_elements
        self.func = validate_screens
        self.has_dev = screen_has_device_specific_elements

    def test_has_device_specific_with_chrome(self):
        assert self.has_dev({"chrome": "panel"})

    def test_has_device_specific_with_hardware(self):
        assert self.has_dev({"hardware": [{"slot": "cash-out"}]})

    def test_has_device_specific_with_rail_in_layout(self):
        assert self.has_dev({"layout": {"type": "row", "elements": [
            {"type": "side-key-rail", "side": "left", "keys": []},
        ]}})

    def test_plain_atm_is_not_device_specific(self):
        assert not self.has_dev({
            "kind": "atm-screen",
            "layout": {"type": "stack", "elements": [{"type": "button"}]},
        })

    def test_warns_when_all_atm_screens_are_phone_shaped(self):
        screens = [
            {"id": "a", "kind": "atm-screen", "title": "A", "stage_id": "s1", "state": "default",
             "layout": {"type": "stack", "elements": [
                {"type": "button", "id": "x", "label": "X", "interactive": True},
             ]}},
            {"id": "b", "kind": "atm-screen", "title": "B", "stage_id": "s1", "state": "default",
             "layout": {"type": "stack", "elements": [{"type": "text", "label": "y"}]}},
        ]
        stages = [{"id": "s1", "label": "S1", "steps": [
            {"id": "t1", "screen_refs": ["a", "b"]},
        ]}]
        out = self.func(screens, stages, [])
        assert any("kind='atm-screen'" in w and "NONE" in w for w in out["warnings"])

    def test_does_not_warn_when_at_least_one_atm_has_chrome(self):
        screens = [
            {"id": "a", "kind": "atm-screen", "title": "A", "stage_id": "s1", "state": "default",
             "chrome": "panel",
             "hardware": [{"slot": "card-reader", "position": "top"}],
             "layout": {"type": "stack", "elements": [{"type": "text", "label": "x"}]}},
            {"id": "b", "kind": "atm-screen", "title": "B", "stage_id": "s1", "state": "default",
             "layout": {"type": "stack", "elements": [
                {"type": "button", "id": "x", "label": "X", "interactive": True},
             ]}},
        ]
        stages = [{"id": "s1", "label": "S1", "steps": [
            {"id": "t1", "screen_refs": ["a", "b"]},
        ]}]
        out = self.func(screens, stages, [])
        # One screen has chrome → journey-wide check passes; no warning emitted
        assert not any("NONE use side-key-rail" in w for w in out["warnings"])

    def test_does_not_warn_when_no_atm_screens(self):
        screens = [
            {"id": "a", "kind": "mobile-screen", "title": "A", "stage_id": "s1", "state": "default",
             "layout": {"type": "stack", "elements": [{"type": "text", "label": "x"}]}},
        ]
        stages = [{"id": "s1", "label": "S1", "steps": [{"id": "t1", "screen_refs": ["a"]}]}]
        out = self.func(screens, stages, [])
        assert not any("NONE use side-key-rail" in w for w in out["warnings"])


class TestParseArrowFrom:
    """`from` accepts either `<screen-id>` (whole screen) or
    `<screen-id>#<element-id>` (anchored at an element)."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import parse_arrow_from
        self.func = parse_arrow_from

    def test_screen_only(self):
        assert self.func("welcome") == ("welcome", None)

    def test_screen_with_element(self):
        assert self.func("welcome#confirm") == ("welcome", "confirm")

    def test_empty(self):
        assert self.func("") == ("", None)

    def test_non_string(self):
        assert self.func(None) == ("", None)

    def test_strips_blank_element(self):
        # "welcome#" with no element id → treat as whole-screen anchor
        assert self.func("welcome#") == ("welcome", None)


class TestComputeMinScreenCount:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import compute_min_screen_count
        self.func = compute_min_screen_count

    def test_floor_is_eight(self):
        assert self.func([{"id": "s1"}]) == 8
        assert self.func([{"id": "s1"}, {"id": "s2"}]) == 8
        assert self.func([{"id": "s1"}, {"id": "s2"}, {"id": "s3"}]) == 8

    def test_scales_with_stage_count(self):
        # 5 stages * 2 = 10, > 8 floor
        assert self.func([{"id": f"s{i}"} for i in range(5)]) == 10
        # 7 stages * 2 = 14
        assert self.func([{"id": f"s{i}"} for i in range(7)]) == 14

    def test_empty(self):
        # Even no stages still floors at 8 — a journey without screens is
        # trivially below floor, but compute_min_screen_count returns the
        # recommendation so the calling validator can report against it.
        assert self.func([]) == 8


class TestScreenCountGate:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import validate_screens
        self.func = validate_screens

    def _screens_n(self, n: int, kind: str = "mobile-screen") -> list[dict]:
        return [{
            "id": f"s{i}", "kind": kind, "title": f"S{i}", "stage_id": "stg",
            "state": "default",
            "layout": {"type": "stack", "elements": [{"type": "text", "label": f"s{i}"}]},
        } for i in range(n)]

    def _stages_n(self, n: int) -> list[dict]:
        return [{
            "id": f"stage{i}", "label": f"Stage {i}", "steps": [
                {"id": "t", "screen_refs": []},
            ],
        } for i in range(n)]

    def test_warns_when_below_floor(self):
        out = self.func(self._screens_n(3), self._stages_n(3), [], strict=False)
        assert any("Recommended floor" in w and "= 8" in w for w in out["warnings"])
        assert not any("Recommended floor" in e for e in out["errors"])

    def test_strict_promotes_to_error(self):
        out = self.func(self._screens_n(3), self._stages_n(3), [], strict=True)
        assert any("Recommended floor" in e and "= 8" in e for e in out["errors"])
        assert not any("Recommended floor" in w for w in out["warnings"])

    def test_passes_when_above_floor(self):
        out = self.func(self._screens_n(10), self._stages_n(3), [], strict=True)
        assert not any("Recommended floor" in e for e in out["errors"])
        assert not any("Recommended floor" in w for w in out["warnings"])


