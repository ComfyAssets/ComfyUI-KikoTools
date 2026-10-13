"""Extra coverage for Local Image Loader logic (scan/search)."""

import os
from unittest.mock import patch

import pytest

from kikotools.tools.local_image_loader import logic
from kikotools.tools.local_image_loader.logic import scan_directory, search_files


@pytest.fixture
def files(tmp_path):
    (tmp_path / "cat.png").write_bytes(b"12345")
    (tmp_path / "dog.jpg").write_bytes(b"1")
    (tmp_path / "cat.mp4").write_bytes(b"1")
    (tmp_path / "cat.mp3").write_bytes(b"1")
    (tmp_path / "cat.txt").write_bytes(b"1")
    (tmp_path / ".hidden.png").write_bytes(b"1")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "cat2.png").write_bytes(b"1")
    (tmp_path / "catdir").mkdir()
    (tmp_path / "other").mkdir()
    (tmp_path / "other" / "deep_cat.webp").write_bytes(b"1")
    return tmp_path


def test_load_image_bad_metadata_json_falls_back_to_raw(tmp_path):
    from PIL import Image, PngImagePlugin

    info = PngImagePlugin.PngInfo()
    info.add_text("prompt", "not json")
    info.add_text("workflow", "{bad")
    path = tmp_path / "m.png"
    Image.new("RGB", (2, 2)).save(path, pnginfo=info)
    _, meta = logic.load_image_from_path(str(path))
    assert meta["prompt"] == "not json"
    assert meta["workflow"] == "{bad"


class TestScanDirectory:
    def test_hide_dot_files_toggle(self, files):
        names = {i["name"] for i in scan_directory(str(files))}
        assert ".hidden.png" not in names
        names = {i["name"] for i in scan_directory(str(files), hide_dot_folders=False)}
        assert ".hidden.png" in names

    def test_sort_by_size_and_date(self, files):
        by_size = [
            i["name"]
            for i in scan_directory(str(files), sort_by="size", sort_order="desc")
            if i["type"] == "image"
        ]
        assert by_size[0] == "cat.png"
        by_date = scan_directory(str(files), sort_by="date")
        assert by_date[0]["type"] == "dir"

    def test_vanishing_file_skipped(self, files):
        real = os.stat

        def flaky(p, *a, **k):
            if str(p).endswith(".png"):
                raise FileNotFoundError
            return real(p, *a, **k)

        with patch.object(os, "stat", side_effect=flaky):
            names = {i["name"] for i in scan_directory(str(files))}
        assert "cat.png" not in names and "dog.jpg" in names


class TestSearchFiles:
    def test_finds_nested_and_dirs(self, files):
        names = [r["name"] for r in search_files(str(files), "cat")]
        assert {"cat.png", "cat2.png", "catdir", "deep_cat.webp"} <= set(names)
        assert "cat.txt" not in names and "cat.mp4" not in names

    def test_media_flags(self, files):
        names = [
            r["name"]
            for r in search_files(str(files), "cat", show_videos=True, show_audio=True)
        ]
        assert "cat.mp4" in names and "cat.mp3" in names

    def test_blank_query_empty(self, files):
        assert search_files(str(files), "   ") == []
        assert search_files(str(files), "") == []

    def test_not_a_directory(self, tmp_path):
        with pytest.raises(NotADirectoryError):
            search_files(str(tmp_path / "nope"), "x")

    def test_max_results(self, files):
        assert len(search_files(str(files), "cat", max_results=2)) == 2

    def test_unreadable_directory_ignored(self, files):
        real = os.listdir

        def flaky(p):
            if str(p).endswith("sub"):
                raise PermissionError
            return real(p)

        with patch.object(os, "listdir", side_effect=flaky):
            names = [r["name"] for r in search_files(str(files), "cat")]
        assert "cat2.png" not in names

    def test_stat_failure_skipped(self, files):
        real = os.stat

        def flaky(p, *a, **k):
            if str(p).endswith("cat.png"):
                raise PermissionError
            return real(p, *a, **k)

        with patch.object(os, "stat", side_effect=flaky):
            names = [r["name"] for r in search_files(str(files), "cat")]
        assert "cat.png" not in names and "cat2.png" in names
