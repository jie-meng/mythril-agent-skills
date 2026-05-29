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
