"""Tests for image-reference skill scripts."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestAssetsDirFor:
    """Tests for image_assets.assets_dir_for."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from image_assets import assets_dir_for
        self.func = assets_dir_for

    def test_co_located_dir(self):
        result = self.func(Path("/docs/implementation.md"))
        assert result == Path("/docs/implementation.assets")

    def test_nested_doc(self):
        result = self.func(Path("/a/b/c/report.MD"))
        assert result == Path("/a/b/c/report.assets")


class TestSlugify:
    """Tests for image_assets.slugify."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from image_assets import slugify
        self.func = slugify

    def test_clean_name_preserved(self):
        assert self.func("mobile-arch.png") == "mobile-arch.png"

    def test_messy_name_normalized(self):
        assert self.func("My Mobile Arch!!.PNG") == "my-mobile-arch.png"

    def test_spaces_and_underscores(self):
        assert self.func("CI Pipeline Diagram.png") == "ci-pipeline-diagram.png"

    def test_screenshot_name(self):
        assert self.func("Screen Shot 2024-01-01 at 3.42.12 PM.png") == (
            "screen-shot-2024-01-01-at-3-42-12-pm.png"
        )

    def test_no_extension(self):
        assert self.func("architecture") == "architecture"

    def test_non_image_extension(self):
        assert self.func("figure.xyz") == "figure-xyz"

    def test_only_punctuation_falls_back(self):
        assert self.func("!!!.png") == "image.png"

    def test_uppercase_extension_lowercased(self):
        assert self.func("MyDiagram.JPG") == "mydiagram.jpg"

    def test_collapses_runs_of_hyphens(self):
        assert self.func("a---b  c.png") == "a-b-c.png"


class TestUniquePath:
    """Tests for image_assets.unique_path."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from image_assets import unique_path
        self.func = unique_path

    def test_free_dest_used_directly(self, tmp_path: Path):
        src = tmp_path / "src.png"
        src.write_bytes(b"\x89PNG")
        result = self.func(tmp_path, "mobile-arch.png", src)
        assert result == tmp_path / "mobile-arch.png"

    def test_byte_identical_reused(self, tmp_path: Path):
        src = tmp_path / "src.png"
        src.write_bytes(b"\x89PNG")
        existing = tmp_path / "mobile-arch.png"
        existing.write_bytes(b"\x89PNG")
        result = self.func(tmp_path, "mobile-arch.png", src)
        assert result == existing

    def test_conflict_gets_suffix(self, tmp_path: Path):
        src = tmp_path / "src.png"
        src.write_bytes(b"\x89PNG-new")
        (tmp_path / "mobile-arch.png").write_bytes(b"other")
        result = self.func(tmp_path, "mobile-arch.png", src)
        assert result == tmp_path / "mobile-arch-1.png"

    def test_conflict_reuses_identical_suffix(self, tmp_path: Path):
        src = tmp_path / "src.png"
        src.write_bytes(b"same-bytes")
        (tmp_path / "mobile-arch.png").write_bytes(b"other")
        (tmp_path / "mobile-arch-1.png").write_bytes(b"same-bytes")
        result = self.func(tmp_path, "mobile-arch.png", src)
        assert result == tmp_path / "mobile-arch-1.png"

    def test_multiple_conflicts(self, tmp_path: Path):
        src = tmp_path / "src.png"
        src.write_bytes(b"unique-bytes")
        (tmp_path / "mobile-arch.png").write_bytes(b"a")
        (tmp_path / "mobile-arch-1.png").write_bytes(b"b")
        result = self.func(tmp_path, "mobile-arch.png", src)
        assert result == tmp_path / "mobile-arch-2.png"


class TestRelAssetPath:
    """Tests for image_assets.rel_asset_path."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from image_assets import rel_asset_path
        self.func = rel_asset_path

    def test_simple(self):
        result = self.func(Path("/docs/implementation.md"), "mobile-arch.png")
        assert result == "implementation.assets/mobile-arch.png"

    def test_nested(self):
        result = self.func(Path("/a/b/guide.md"), "hero.jpg")
        assert result == "guide.assets/hero.jpg"


class TestMarkdownLink:
    """Tests for image_assets.markdown_link."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from image_assets import markdown_link
        self.func = markdown_link

    def test_with_alt(self):
        assert self.func("guide.assets/hero.jpg", "Team photo") == (
            "![Team photo](guide.assets/hero.jpg)"
        )

    def test_alt_defaults_to_stem(self):
        assert self.func("guide.assets/mobile-arch.png") == (
            "![mobile-arch](guide.assets/mobile-arch.png)"
        )

    def test_blank_alt_uses_stem(self):
        assert self.func("a.assets/x.png", "   ") == "![x](a.assets/x.png)"