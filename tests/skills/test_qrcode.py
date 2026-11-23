"""Tests for qrcode skill scripts."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest


class TestGetCacheRoot:
    """Tests for qr_ops.get_cache_root."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from qr_ops import get_cache_root

        self.func = get_cache_root

    def test_macos(self):
        home = Path("/Users/u")
        assert self.func("Darwin", {}, home) == (
            home / "Library" / "Caches" / "mythril-skills-cache"
        )

    def test_linux_default(self):
        home = Path("/home/u")
        assert self.func("Linux", {}, home) == home / ".cache" / "mythril-skills-cache"

    def test_linux_xdg(self):
        result = self.func("Linux", {"XDG_CACHE_HOME": "/x"}, Path("/home/u"))
        assert result == Path("/x/mythril-skills-cache")

    def test_windows_localappdata(self):
        result = self.func("Windows", {"LOCALAPPDATA": "/lad"}, Path("/home/u"))
        assert result == Path("/lad/mythril-skills-cache")

    def test_windows_fallback(self):
        home = Path("/home/u")
        assert self.func("Windows", {}, home) == (
            home / "AppData" / "Local" / "mythril-skills-cache"
        )


class TestSlugify:
    """Tests for qr_ops.slugify."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from qr_ops import slugify

        self.func = slugify

    def test_url_scheme_stripped(self):
        assert self.func("https://Example.com/a?b=1") == "example-com-a-b-1"

    def test_non_ascii_falls_back(self):
        assert self.func("你好") == "qr"

    def test_truncated(self):
        result = self.func("a" * 100, max_len=10)
        assert result == "a" * 10

    def test_no_trailing_dash_after_truncate(self):
        assert self.func("abcd efgh", max_len=5) == "abcd"


class TestDefaultOutputName:
    """Tests for qr_ops.default_output_name."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from qr_ops import default_output_name

        self.func = default_output_name

    def test_png(self):
        now = datetime(2026, 1, 2, 3, 4, 5)
        assert self.func("hello", "png", now) == "qr-hello-20260102-030405.png"

    def test_svg(self):
        now = datetime(2026, 1, 2, 3, 4, 5)
        assert self.func("", "svg", now) == "qr-qr-20260102-030405.svg"


class TestResolveFormat:
    """Tests for qr_ops.resolve_format."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from qr_ops import resolve_format

        self.func = resolve_format

    def test_default_png(self):
        assert self.func(None, None) == "png"

    def test_from_suffix(self):
        assert self.func("out.SVG", None) == "svg"

    def test_unknown_suffix_defaults_png(self):
        assert self.func("out.jpg", None) == "png"

    def test_explicit_wins(self):
        assert self.func("out.png", "svg") == "svg"

    def test_explicit_invalid(self):
        with pytest.raises(ValueError):
            self.func(None, "gif")


class TestResolveOutputPath:
    """Tests for qr_ops.resolve_output_path."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from qr_ops import resolve_output_path

        self.func = resolve_output_path

    def test_default_dir(self):
        result = self.func(None, "png", Path("/cache/qrcode"), "a.png")
        assert result == Path("/cache/qrcode/a.png")

    def test_appends_suffix(self):
        assert self.func("out/code", "png", Path("/c"), "x") == Path("out/code.png")

    def test_matching_suffix(self):
        assert self.func("code.svg", "svg", Path("/c"), "x") == Path("code.svg")

    def test_mismatched_suffix(self):
        with pytest.raises(ValueError):
            self.func("code.jpg", "png", Path("/c"), "x")


class TestValidateEncodeParams:
    """Tests for qr_ops.validate_encode_params."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from qr_ops import validate_encode_params

        self.func = validate_encode_params

    def test_valid(self):
        self.func(10, 4, "m")

    @pytest.mark.parametrize(
        "scale,border,error", [(0, 4, "M"), (1, -1, "M"), (1, 1, "X")]
    )
    def test_invalid(self, scale, border, error):
        with pytest.raises(ValueError):
            self.func(scale, border, error)


class TestFormatDecodeResults:
    """Tests for qr_ops.format_decode_results."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from qr_ops import format_decode_results

        self.func = format_decode_results

    def test_single_file_plain(self):
        results = [
            {"file": "a.png", "format": "QR Code", "text": "one"},
            {"file": "a.png", "format": "QR Code", "text": "two"},
        ]
        assert self.func(results, False) == "one\ntwo"

    def test_multi_file_prefixed(self):
        results = [
            {"file": "a.png", "format": "QR Code", "text": "one"},
            {"file": "b.png", "format": "QR Code", "text": "two"},
        ]
        assert self.func(results, False) == "a.png: one\nb.png: two"

    def test_json_keeps_unicode(self):
        results = [{"file": "a.png", "format": "QR Code", "text": "你好"}]
        out = self.func(results, True)
        assert "你好" in out
        assert json.loads(out) == results
