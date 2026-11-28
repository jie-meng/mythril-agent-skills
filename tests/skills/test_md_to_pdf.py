"""Tests for md-to-pdf skill scripts."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestResolveOutputPath:
    """Tests for md_to_pdf.resolve_output_path."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from md_to_pdf import resolve_output_path

        self.func = resolve_output_path

    def test_no_output_uses_same_dir(self):
        result = self.func(Path("/docs/README.md"), None)
        assert result == Path("/docs/README.pdf")

    def test_no_output_replaces_extension(self):
        result = self.func(Path("notes.md"), None)
        assert result == Path("notes.pdf")

    def test_explicit_output(self):
        result = self.func(Path("input.md"), "/tmp/out.pdf")
        assert result == Path("/tmp/out.pdf")

    def test_explicit_output_relative(self):
        result = self.func(Path("input.md"), "build/output.pdf")
        assert result == Path("build/output.pdf")

    def test_nested_input_path(self):
        result = self.func(Path("/a/b/c/doc.md"), None)
        assert result == Path("/a/b/c/doc.pdf")


class TestReadCssFile:
    """Tests for md_to_pdf.read_css_file."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from md_to_pdf import read_css_file

        self.func = read_css_file

    def test_reads_existing_css(self, tmp_path: Path):
        css = tmp_path / "style.css"
        css.write_text("body { color: red; }")
        result = self.func(str(css))
        assert result == "body { color: red; }"

    def test_missing_css_exits(self):
        with pytest.raises(SystemExit):
            self.func("/nonexistent/style.css")


class TestValidPaperSizes:
    """Tests for md_to_pdf.VALID_PAPER_SIZES."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from md_to_pdf import VALID_PAPER_SIZES

        self.sizes = VALID_PAPER_SIZES

    def test_contains_a4(self):
        assert "A4" in self.sizes

    def test_contains_landscape_variants(self):
        assert "A4-L" in self.sizes
        assert "Letter-L" in self.sizes

    def test_contains_letter(self):
        assert "Letter" in self.sizes

    def test_contains_legal(self):
        assert "Legal" in self.sizes


class TestBuildParser:
    """Tests for md_to_pdf.build_parser — verifies CLI structure."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from md_to_pdf import build_parser

        self.parser = build_parser()

    def test_basic_args(self):
        args = self.parser.parse_args(["input.md"])
        assert args.file == "input.md"
        assert args.output is None
        assert args.toc == 0
        assert args.paper_size == "A4"
        assert args.css is None
        assert args.title is None
        assert args.author is None
        assert args.optimize is False

    def test_output_flag(self):
        args = self.parser.parse_args(["input.md", "-o", "out.pdf"])
        assert args.output == "out.pdf"

    def test_long_output_flag(self):
        args = self.parser.parse_args(["input.md", "--output", "out.pdf"])
        assert args.output == "out.pdf"

    def test_toc_level(self):
        args = self.parser.parse_args(["input.md", "--toc", "3"])
        assert args.toc == 3

    def test_paper_size(self):
        args = self.parser.parse_args(["input.md", "--paper-size", "Letter"])
        assert args.paper_size == "Letter"

    def test_css(self):
        args = self.parser.parse_args(["input.md", "--css", "style.css"])
        assert args.css == "style.css"

    def test_metadata(self):
        args = self.parser.parse_args([
            "input.md", "--title", "My Doc", "--author", "Jane"
        ])
        assert args.title == "My Doc"
        assert args.author == "Jane"

    def test_optimize(self):
        args = self.parser.parse_args(["input.md", "--optimize"])
        assert args.optimize is True

    def test_all_options(self):
        args = self.parser.parse_args([
            "input.md",
            "-o", "out.pdf",
            "--toc", "2",
            "--paper-size", "A4-L",
            "--css", "s.css",
            "--title", "T",
            "--author", "A",
            "--optimize",
        ])
        assert args.file == "input.md"
        assert args.output == "out.pdf"
        assert args.toc == 2
        assert args.paper_size == "A4-L"
        assert args.css == "s.css"
        assert args.title == "T"
        assert args.author == "A"
        assert args.optimize is True

    def test_no_file_exits(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args([])


class TestOutputConflict:
    """Tests for md_to_pdf.output_conflict."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from md_to_pdf import output_conflict

        self.func = output_conflict

    def test_new_output_ok(self, tmp_path):
        assert self.func(tmp_path / "a.md", tmp_path / "a.pdf", False) is None

    def test_existing_output_needs_force(self, tmp_path):
        out = tmp_path / "a.pdf"
        out.write_bytes(b"%PDF")
        assert "--force" in self.func(tmp_path / "a.md", out, False)
        assert self.func(tmp_path / "a.md", out, True) is None

    def test_output_equal_to_input_refused(self, tmp_path):
        src = tmp_path / "a.md"
        src.write_text("# x")
        assert self.func(src, src, True) is not None


class TestPreflightCommand:
    """SKILL.md pre-flight must not rely on markdown_pdf.__version__ (absent)."""

    def test_no_version_attribute_in_preflight(self):
        from pathlib import Path

        skill_md = (
            Path(__file__).resolve().parents[2]
            / "mythril_agent_skills" / "skills" / "md-to-pdf" / "SKILL.md"
        ).read_text(encoding="utf-8")
        assert "markdown_pdf.__version__" not in skill_md
