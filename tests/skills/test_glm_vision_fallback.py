"""Tests for glm-vision-fallback skill scripts."""

import base64
import io
import json
import urllib.error

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 8


class TestIsUrl:
    """Tests for vision_fallback.is_url."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from vision_fallback import is_url

        self.func = is_url

    @pytest.mark.parametrize("value", ["http://x.com/a.png", "https://x.com/a.png"])
    def test_urls(self, value):
        assert self.func(value) is True

    @pytest.mark.parametrize("value", ["a.png", "/tmp/a.png", "ftp://x/a.png"])
    def test_paths(self, value):
        assert self.func(value) is False


class TestGuessMimeType:
    """Tests for vision_fallback.guess_mime_type."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from vision_fallback import guess_mime_type

        self.func = guess_mime_type

    @pytest.mark.parametrize(
        ("name", "data", "expected"),
        [
            ("a.bin", PNG, "image/png"),
            ("a.bin", JPEG, "image/jpeg"),
            ("a.bin", b"GIF89a" + b"\x00" * 6, "image/gif"),
            ("a.bin", b"RIFF\x00\x00\x00\x00WEBP", "image/webp"),
            ("a.bin", b"BM" + b"\x00" * 10, "image/bmp"),
        ],
    )
    def test_magic_bytes_win_over_extension(self, tmp_path, name, data, expected):
        path = tmp_path / name
        path.write_bytes(data)
        assert self.func(path) == expected

    def test_falls_back_to_extension(self, tmp_path):
        path = tmp_path / "pic.png"
        path.write_bytes(b"not-really")
        assert self.func(path) == "image/png"

    def test_unknown_format_raises(self, tmp_path):
        path = tmp_path / "blob.unknownext"
        path.write_bytes(b"zzzz")
        with pytest.raises(ValueError, match="Unsupported image format"):
            self.func(path)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Cannot read image file"):
            self.func(tmp_path / "missing.png")


class TestBuildContent:
    """Tests for vision_fallback.build_content."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from vision_fallback import build_content

        self.func = build_content

    def test_local_file_is_inlined_and_url_kept(self, tmp_path):
        path = tmp_path / "a.png"
        path.write_bytes(PNG)
        content = self.func([str(path), "https://x.com/b.jpg"], "what?")

        assert len(content) == 3
        local = content[0]["image_url"]["url"]
        assert local.startswith("data:image/png;base64,")
        assert base64.b64decode(local.split(",", 1)[1]) == PNG
        assert content[1] == {
            "type": "image_url",
            "image_url": {"url": "https://x.com/b.jpg"},
        }
        assert content[2] == {"type": "text", "text": "what?"}


class TestParseResponse:
    """Tests for vision_fallback.parse_response."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from vision_fallback import parse_response

        self.func = parse_response

    def test_extracts_content(self):
        data = {"choices": [{"message": {"content": "hello"}}]}
        assert self.func(data) == "hello"

    @pytest.mark.parametrize("data", [{}, {"choices": []}, {"choices": [None]}])
    def test_malformed_raises(self, data):
        with pytest.raises(RuntimeError, match="Unexpected API response"):
            self.func(data)


class TestHttpErrorMessage:
    """Tests for vision_fallback._http_error_message."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from vision_fallback import _http_error_message

        self.func = _http_error_message

    @staticmethod
    def _error(code: int, body: bytes) -> urllib.error.HTTPError:
        return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(body))

    def test_hint_and_detail(self):
        body = json.dumps({"error": {"message": "bad key"}}).encode()
        message = self.func(self._error(401, body))
        assert "HTTP 401" in message
        assert "invalid or expired" in message
        assert "(bad key)" in message

    def test_string_error_and_no_hint(self):
        body = json.dumps({"error": "boom"}).encode()
        assert self.func(self._error(500, body)) == (
            "GLM vision API returned HTTP 500 (boom)"
        )

    def test_non_json_body(self):
        message = self.func(self._error(429, b"<html>"))
        assert message == (
            "GLM vision API returned HTTP 429 rate limited - wait a moment and retry."
        )
