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
        assert out["schema_version"] == "2"
        assert out["title"] == "Demo"
        assert out["language"] == "en"
        assert len(out["personas"]) == 1
        assert out["personas"][0]["id"] == "alice"
        assert [s["label"] for s in out["stages"]] == ["Discover", "Try", "Habit"]
        # v2 skeleton seeds one example step + one screen ref per stage so
        # the Flow view has something to render in a brand-new workspace.
        for stage in out["stages"]:
            assert len(stage["steps"]) == 1
            assert stage["steps"][0]["screen_refs"], "every example step has a screen ref"

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

    def test_v2_screens_are_present_and_wired(self):
        out = self.func(
            title="x", subtitle="", persona_name="a",
            persona_role="b", language="en",
        )
        assert out["schema_version"] == "2"
        screens = out.get("screens", [])
        assert len(screens) == 3
        ids = {s["id"] for s in screens}
        assert ids == {"welcome", "main", "done"}
        # every screen has a layout, kind, title, and at least one transition
        for s in screens:
            assert s["kind"]
            assert s["title"]
            assert s["layout"]["type"] == "stack"
            assert s["transitions"], "each example screen has an outgoing transition"
            # exactly one default per screen
            assert sum(1 for t in s["transitions"] if t.get("is_default")) == 1
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
        journey["schema_version"] = "3"
        (tmp_path / "journey.json").write_text(json.dumps(journey))
        (tmp_path / "JOURNEY.md").write_text(
            "# ok\n## Stages\n"
            "```mermaid\nflowchart LR\n  discover[\"Discover\"]\n```\n"
            "### 1. Discover\n"
        )
        r = self.func(tmp_path)
        assert any("schema_version" in e for e in r["errors"])


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


def _screen(id_: str, transitions=None, layout=None) -> dict:
    return {
        "id": id_,
        "kind": "mobile-screen",
        "title": id_,
        "stage_id": "s1",
        "layout": layout or {
            "type": "stack",
            "elements": [
                {"type": "button", "id": "go", "label": "Go", "interactive": True},
            ],
        },
        "transitions": transitions or [],
    }


class TestValidateScreens:
    @pytest.fixture(autouse=True)
    def _import(self):
        from validate_screens import validate_screens
        self.func = validate_screens

    def test_empty_passes(self):
        out = self.func([], [])
        assert out["errors"] == []
        assert out["warnings"] == []

    def test_unique_screen_ids(self):
        out = self.func([_screen("a"), _screen("a")], [])
        assert any("duplicate screen id" in e for e in out["errors"])

    def test_transition_to_missing_screen(self):
        screens = [
            _screen("a", transitions=[
                {"from_element": "go", "trigger": "tap", "to_screen": "ghost",
                 "label": "go to ghost"},
            ]),
        ]
        out = self.func(screens, [])
        assert any("'ghost' does not exist" in e for e in out["errors"])

    def test_from_element_missing(self):
        screens = [
            _screen("a", transitions=[
                {"from_element": "nope", "trigger": "tap", "to_screen": "a",
                 "label": "loop"},
            ]),
        ]
        out = self.func(screens, [])
        assert any("from_element='nope'" in e for e in out["errors"])

    def test_from_element_any_is_allowed(self):
        screens = [
            _screen("a", transitions=[
                {"from_element": "any", "trigger": "tap", "to_screen": "a",
                 "label": "tap anywhere"},
            ]),
        ]
        out = self.func(screens, [])
        assert out["errors"] == []

    def test_step_screen_refs_resolved(self):
        screens = [_screen("a")]
        stages = [{
            "id": "s1", "label": "S1", "steps": [
                {"id": "t1", "screen_refs": ["a"]},
                {"id": "t2", "screen_refs": ["ghost"]},
            ],
        }]
        out = self.func(screens, stages)
        assert any("screen_refs[0]='ghost'" in e for e in out["errors"])

    def test_orphan_screen_warns(self):
        screens = [_screen("a"), _screen("b")]
        stages = [{"id": "s1", "label": "S1", "steps": [{"id": "t1", "screen_refs": ["a"]}]}]
        out = self.func(screens, stages)
        assert any("'b'" in w and "no incoming" in w for w in out["warnings"])

    def test_multiple_defaults_error(self):
        screens = [_screen("a", transitions=[
            {"from_element": "go", "trigger": "tap", "to_screen": "a",
             "label": "loop1", "is_default": True},
            {"from_element": "go", "trigger": "tap", "to_screen": "a",
             "label": "loop2", "is_default": True},
        ])]
        out = self.func(screens, [])
        assert any("is_default=true" in e for e in out["errors"])

    def test_interactive_without_id_warns(self):
        screens = [{
            "id": "a", "kind": "mobile-screen", "title": "a",
            "stage_id": "s1",
            "layout": {
                "type": "stack",
                "elements": [
                    {"type": "button", "label": "no id", "interactive": True},
                ],
            },
            "transitions": [],
        }]
        stages = [{"id": "s1", "label": "S1", "steps": [{"id": "t1", "screen_refs": ["a"]}]}]
        out = self.func(screens, stages)
        assert any("without id" in w for w in out["warnings"])

    def test_dead_end_middle_screen_infos(self):
        screens = [_screen("a"), _screen("b", transitions=[])]
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
        # Link a -> b so b has inbound
        screens[0]["transitions"] = [
            {"from_element": "go", "trigger": "tap", "to_screen": "b",
             "label": "go to b"},
        ]
        out = self.func(screens, stages)
        # b is referenced in step 2 of 2 in stage s1 (last step of that stage)
        # but stage s1 is NOT the last stage, so it should NOT be flagged as
        # a "natural terminal screen" — info should mention dead-end.
        assert any("no outgoing transitions" in i for i in out["info"])


