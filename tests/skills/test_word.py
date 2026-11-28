"""Tests for word skill scripts."""

from __future__ import annotations

import pytest


class TestFormatSize:
    """Tests for word_ops._format_size."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from word_ops import _format_size

        self.func = _format_size

    def test_bytes(self):
        assert self.func(500) == "500 B"

    def test_kilobytes(self):
        assert self.func(2048) == "2.0 KB"

    def test_megabytes(self):
        assert self.func(1048576) == "1.0 MB"

    def test_zero(self):
        assert self.func(0) == "0 B"

    def test_just_under_1kb(self):
        assert self.func(1023) == "1023 B"

    def test_exactly_1kb(self):
        assert self.func(1024) == "1.0 KB"

    def test_large_mb(self):
        result = self.func(52_428_800)
        assert result == "50.0 MB"


class TestCountWords:
    """Tests for word_ops._count_words."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from word_ops import _count_words

        self.func = _count_words

    def test_english_words(self):
        assert self.func("hello world") == 2

    def test_empty_string(self):
        assert self.func("") == 0

    def test_cjk_characters(self):
        assert self.func("你好世界") == 4

    def test_mixed_english_cjk(self):
        result = self.func("hello 你好 world 世界")
        assert result == 6  # 2 English words + 4 CJK characters

    def test_whitespace_only(self):
        assert self.func("   ") == 0

    def test_multiple_spaces(self):
        assert self.func("hello   world") == 2


class TestBuildParser:
    """Tests for word_ops.build_parser — verifies CLI structure."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from word_ops import build_parser

        self.parser = build_parser()

    def test_info_command(self):
        args = self.parser.parse_args(["info", "test.docx"])
        assert args.command == "info"
        assert args.file == "test.docx"

    def test_text_command_basic(self):
        args = self.parser.parse_args(["text", "test.docx"])
        assert args.command == "text"
        assert args.file == "test.docx"
        assert args.limit is None
        assert args.skip_empty is False

    def test_text_command_with_limit(self):
        args = self.parser.parse_args(
            ["text", "test.docx", "--limit", "50"]
        )
        assert args.limit == 50

    def test_text_command_skip_empty(self):
        args = self.parser.parse_args(
            ["text", "test.docx", "--skip-empty"]
        )
        assert args.skip_empty is True

    def test_tables_command_default_format(self):
        args = self.parser.parse_args(["tables", "test.docx"])
        assert args.command == "tables"
        assert args.format == "markdown"

    def test_tables_command_json_format(self):
        args = self.parser.parse_args(
            ["tables", "test.docx", "--format", "json"]
        )
        assert args.format == "json"

    def test_tables_command_csv_with_dir(self):
        args = self.parser.parse_args(
            ["tables", "test.docx", "--format", "csv", "--output-dir", "./out"]
        )
        assert args.format == "csv"
        assert args.output_dir == "./out"

    def test_extract_images_command(self):
        args = self.parser.parse_args(
            ["extract-images", "test.docx", "--output-dir", "./imgs"]
        )
        assert args.command == "extract-images"
        assert args.output_dir == "./imgs"

    def test_to_markdown_command(self):
        args = self.parser.parse_args(["to-markdown", "test.docx"])
        assert args.command == "to-markdown"
        assert args.output is None

    def test_to_markdown_with_output(self):
        args = self.parser.parse_args(
            ["to-markdown", "test.docx", "-o", "out.md"]
        )
        assert args.output == "out.md"

    def test_no_command_exits(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args([])


class TestCommandDispatch:
    """Tests for word_ops.COMMAND_DISPATCH mapping."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from word_ops import COMMAND_DISPATCH

        self.dispatch = COMMAND_DISPATCH

    def test_all_commands_present(self):
        expected = {
            "info",
            "text",
            "tables",
            "extract-images",
            "to-markdown",
        }
        assert set(self.dispatch.keys()) == expected

    def test_all_values_callable(self):
        for name, handler in self.dispatch.items():
            assert callable(handler), f"{name} handler is not callable"


def _hyperlink(paragraph, text: str, url: str | None):
    """Append a w:hyperlink run (external when *url* is given) to a paragraph."""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    link = OxmlElement("w:hyperlink")
    if url:
        rid = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
        link.set(qn("r:id"), rid)
    run = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = text
    run.append(t)
    link.append(run)
    paragraph._p.append(link)


def _tracked_insert(paragraph, text: str):
    """Append a w:ins (tracked insertion) run to a paragraph."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    ins = OxmlElement("w:ins")
    ins.set(qn("w:id"), "1")
    ins.set(qn("w:author"), "t")
    run = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    run.append(t)
    ins.append(run)
    paragraph._p.append(ins)


class TestHeadingLevel:
    """Tests for word_ops.heading_level."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from word_ops import heading_level

        self.func = heading_level

    def test_numbered(self):
        assert self.func("Heading 1") == 1
        assert self.func("Heading 3") == 3

    def test_clamped_to_six(self):
        assert self.func("Heading 9") == 6

    def test_custom_heading_does_not_crash(self):
        assert self.func("Heading Custom") == 1
        assert self.func("Heading") == 1

    def test_title_and_body(self):
        assert self.func("Title") == 1
        assert self.func("Normal") is None
        assert self.func(None) is None


class TestFormatSegments:
    """Tests for word_ops.format_segments."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from word_ops import format_segments

        self.func = format_segments

    def test_plain(self):
        assert self.func([("a ", False, False, None), ("b", False, False, None)]) == "a b"

    def test_adjacent_bold_runs_merge(self):
        segs = [("Hel", True, False, None), ("lo", True, False, None)]
        assert self.func(segs) == "**Hello**"

    def test_whitespace_kept_outside_markers(self):
        segs = [("say ", False, False, None), ("hi ", True, False, None), ("now", False, False, None)]
        assert self.func(segs) == "say **hi** now"

    def test_bold_italic(self):
        assert self.func([("x", True, True, None)]) == "***x***"

    def test_link(self):
        segs = [("See ", False, False, None), ("docs", False, False, "https://e.com"),
                (" now", False, False, None)]
        assert self.func(segs) == "See [docs](https://e.com) now"

    def test_link_with_mixed_formatting(self):
        segs = [("a", True, False, "u"), ("b", False, False, "u")]
        assert self.func(segs) == "[**a**b](u)"


class TestUniqueHeaders:
    """Tests for word_ops.unique_headers."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from word_ops import unique_headers

        self.func = unique_headers

    def test_blank_and_duplicate(self):
        assert self.func(["Name", "", "Name"]) == ["Name", "col_2", "Name_2"]

    def test_unique_passthrough(self):
        assert self.func(["a", "b"]) == ["a", "b"]


class TestTableConversion:
    """Tests for word_ops._table_to_markdown / _table_to_json."""

    @pytest.fixture()
    def table(self):
        import docx

        doc = docx.Document()
        t = doc.add_table(rows=3, cols=2)
        data = [["Name", "Note"], ["Ann", "a|b"], ["Bob", ""]]
        for r, row in enumerate(data):
            for c, val in enumerate(row):
                t.cell(r, c).text = val
        return t

    def test_markdown(self, table):
        from word_ops import _table_to_markdown

        assert _table_to_markdown(table).splitlines() == [
            "| Name | Note |",
            "| --- | --- |",
            "| Ann | a\\|b |",
            "| Bob |  |",
        ]

    def test_json(self, table):
        from word_ops import _table_to_json

        assert _table_to_json(table) == [
            {"Name": "Ann", "Note": "a|b"},
            {"Name": "Bob", "Note": ""},
        ]

    def test_json_header_only_is_empty(self):
        import docx

        from word_ops import _table_to_json

        t = docx.Document().add_table(rows=1, cols=2)
        assert _table_to_json(t) == []


class TestCmdToMarkdown:
    """Integration tests for word_ops.cmd_to_markdown on generated documents."""

    def _convert(self, tmp_path, doc) -> str:
        import argparse

        from word_ops import cmd_to_markdown

        src = tmp_path / "in.docx"
        out = tmp_path / "out.md"
        doc.save(str(src))
        cmd_to_markdown(argparse.Namespace(file=str(src), output=str(out)))
        return out.read_text(encoding="utf-8")

    def test_hyperlink_and_tracked_insert_text_kept(self, tmp_path):
        import docx

        doc = docx.Document()
        p = doc.add_paragraph("See ")
        _hyperlink(p, "the docs", "https://example.com/docs")
        _tracked_insert(p, " today")
        p2 = doc.add_paragraph("Anchor ")
        _hyperlink(p2, "here", None)
        md = self._convert(tmp_path, doc)
        assert "See [the docs](https://example.com/docs) today" in md
        assert "Anchor here" in md

    def test_custom_heading_tables_and_order(self, tmp_path):
        import docx

        doc = docx.Document()
        doc.add_paragraph("Intro", style="Heading 1")
        doc.styles.add_style("Heading Custom", 1)
        doc.add_paragraph("Custom", style="Heading Custom")
        t = doc.add_table(rows=2, cols=1)
        t.cell(0, 0).text = "H"
        t.cell(1, 0).text = "v"
        doc.add_paragraph("After")
        md = self._convert(tmp_path, doc)
        assert md.index("# Intro") < md.index("# Custom") < md.index("| H |") < md.index("After")


class TestCmdTextCustomHeading:
    """`text` must not crash on non-numeric heading styles."""

    def test_no_crash(self, tmp_path, capsys):
        import argparse

        import docx

        from word_ops import cmd_text

        doc = docx.Document()
        doc.styles.add_style("Heading Custom", 1)
        doc.add_paragraph("Custom", style="Heading Custom")
        src = tmp_path / "in.docx"
        doc.save(str(src))
        cmd_text(argparse.Namespace(file=str(src), limit=None, skip_empty=True))
        assert "# Custom" in capsys.readouterr().out
