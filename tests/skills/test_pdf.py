"""Tests for pdf skill scripts."""

from __future__ import annotations

import pytest


class TestParsePageSpec:
    """Tests for pdf_ops._parse_page_spec."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from pdf_ops import _parse_page_spec

        self.func = _parse_page_spec

    def test_single_page(self):
        assert self.func("1", 10) == [0]

    def test_single_page_last(self):
        assert self.func("10", 10) == [9]

    def test_comma_separated(self):
        assert self.func("1,3,5", 10) == [0, 2, 4]

    def test_range(self):
        assert self.func("2-5", 10) == [1, 2, 3, 4]

    def test_mixed(self):
        assert self.func("1,3,5-8", 10) == [0, 2, 4, 5, 6, 7]

    def test_duplicates_removed(self):
        assert self.func("1,1,2", 10) == [0, 1]

    def test_range_and_single_overlap(self):
        assert self.func("3,1-5", 10) == [0, 1, 2, 3, 4]

    def test_sorted_output(self):
        assert self.func("5,1,3", 10) == [0, 2, 4]

    def test_single_page_range(self):
        assert self.func("3-3", 10) == [2]

    def test_out_of_range_page_exits(self):
        with pytest.raises(SystemExit):
            self.func("11", 10)

    def test_out_of_range_end_exits(self):
        with pytest.raises(SystemExit):
            self.func("5-11", 10)

    def test_zero_page_exits(self):
        with pytest.raises(SystemExit):
            self.func("0", 10)

    def test_inverted_range_exits(self):
        with pytest.raises(SystemExit):
            self.func("5-3", 10)

    def test_whitespace_tolerance(self):
        assert self.func(" 1 , 3 ", 10) == [0, 2]


class TestFormatSize:
    """Tests for pdf_ops._format_size."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from pdf_ops import _format_size

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


class TestBuildParser:
    """Tests for pdf_ops.build_parser — verifies CLI structure."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from pdf_ops import build_parser

        self.parser = build_parser()

    def test_info_command(self):
        args = self.parser.parse_args(["info", "test.pdf"])
        assert args.command == "info"
        assert args.file == "test.pdf"

    def test_text_command_basic(self):
        args = self.parser.parse_args(["text", "test.pdf"])
        assert args.command == "text"
        assert args.pages is None
        assert args.layout is False

    def test_text_command_with_pages_and_layout(self):
        args = self.parser.parse_args(
            ["text", "test.pdf", "--pages", "1-5", "--layout"]
        )
        assert args.pages == "1-5"
        assert args.layout is True

    def test_tables_command_default_format(self):
        args = self.parser.parse_args(["tables", "test.pdf"])
        assert args.command == "tables"
        assert args.format == "markdown"

    def test_tables_command_json_format(self):
        args = self.parser.parse_args(
            ["tables", "test.pdf", "--format", "json"]
        )
        assert args.format == "json"

    def test_tables_command_csv_with_dir(self):
        args = self.parser.parse_args(
            ["tables", "test.pdf", "--format", "csv", "--output-dir", "./out"]
        )
        assert args.format == "csv"
        assert args.output_dir == "./out"

    def test_to_images_default_scale(self):
        args = self.parser.parse_args(["to-images", "test.pdf"])
        assert args.command == "to-images"
        assert args.scale == 2.0

    def test_to_images_custom_scale(self):
        args = self.parser.parse_args(
            ["to-images", "test.pdf", "--scale", "3.0"]
        )
        assert args.scale == 3.0

    def test_merge_command(self):
        args = self.parser.parse_args(
            ["merge", "a.pdf", "b.pdf", "-o", "out.pdf"]
        )
        assert args.command == "merge"
        assert args.files == ["a.pdf", "b.pdf"]
        assert args.output == "out.pdf"

    def test_split_each(self):
        args = self.parser.parse_args(
            ["split", "test.pdf", "--each", "--output-dir", "./pages"]
        )
        assert args.each is True
        assert args.output_dir == "./pages"

    def test_split_pages(self):
        args = self.parser.parse_args(
            ["split", "test.pdf", "--pages", "1-3", "-o", "out.pdf"]
        )
        assert args.pages == "1-3"
        assert args.output == "out.pdf"

    def test_rotate_command(self):
        args = self.parser.parse_args(
            ["rotate", "test.pdf", "90", "-o", "rot.pdf"]
        )
        assert args.command == "rotate"
        assert args.angle == 90
        assert args.output == "rot.pdf"

    def test_extract_images_command(self):
        args = self.parser.parse_args(
            ["extract-images", "test.pdf", "--output-dir", "./imgs"]
        )
        assert args.command == "extract-images"
        assert args.output_dir == "./imgs"

    def test_decrypt_command(self):
        args = self.parser.parse_args(
            ["decrypt", "test.pdf", "--password", "secret", "-o", "dec.pdf"]
        )
        assert args.command == "decrypt"
        assert args.password == "secret"
        assert args.output == "dec.pdf"

    def test_no_command_exits(self):
        with pytest.raises(SystemExit):
            self.parser.parse_args([])


class TestCommandDispatch:
    """Tests for pdf_ops.COMMAND_DISPATCH mapping."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from pdf_ops import COMMAND_DISPATCH

        self.dispatch = COMMAND_DISPATCH

    def test_all_commands_present(self):
        expected = {
            "info",
            "text",
            "tables",
            "to-images",
            "merge",
            "split",
            "rotate",
            "extract-images",
            "decrypt",
        }
        assert set(self.dispatch.keys()) == expected

    def test_all_values_callable(self):
        for name, handler in self.dispatch.items():
            assert callable(handler), f"{name} handler is not callable"
