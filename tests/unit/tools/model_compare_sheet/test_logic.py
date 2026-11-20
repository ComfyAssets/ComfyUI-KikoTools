"""Tests for Model Compare Sheet logic."""

import os

import pytest
from PIL import Image

from kikotools.tools.model_compare_sheet.logic import (
    build_contact_sheet,
    label_from_filename,
    list_tiles,
    resolve_run_dir,
    sweep_fingerprint,
    tile_filename,
)


class TestResolveRunDir:
    def test_run_dir_lives_under_model_compare(self, tmp_path):
        assert resolve_run_dir(str(tmp_path), "illustrious") == os.path.join(
            str(tmp_path), "model_compare", "illustrious"
        )

    def test_nested_run_names_are_allowed(self, tmp_path):
        assert resolve_run_dir(str(tmp_path), "proj/2026-10-15/sweep") == os.path.join(
            str(tmp_path), "model_compare", "proj", "2026-10-15", "sweep"
        )

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "../escape",
            "/abs/path",
            "a/../../b",
            "..\\escape",
            "a\\..\\..\\b",
            "C:\\abs",
            ".",
            "./x",
            "a/./b",
            "a//b",
            "x/..",
        ],
    )
    def test_rejects_names_that_leave_model_compare(self, tmp_path, bad):
        with pytest.raises(ValueError, match="run_name"):
            resolve_run_dir(str(tmp_path), bad)

    def test_rejects_symlink_escape_into_another_output_folder(self, tmp_path):
        base = tmp_path / "model_compare"
        base.mkdir()
        outside = tmp_path / "unrelated"
        outside.mkdir()
        try:
            (base / "link").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            pytest.skip(f"Directory symlinks unavailable: {exc}")
        with pytest.raises(ValueError, match="run_name"):
            resolve_run_dir(str(tmp_path), "link/run")


class TestTileFilename:
    def test_single_image_run(self):
        assert tile_filename(3, "illustrij_v20", 0, 1) == "03_illustrij_v20.png"

    def test_batch_gets_a_suffix(self):
        assert tile_filename(3, "illustrij_v20", 1, 2) == "03_illustrij_v20_2.png"

    def test_label_characters_are_sanitized(self):
        assert tile_filename(0, "a/b:c d", 0, 1) == "00_a_b_c_d.png"


def test_label_from_filename_strips_index_and_extension():
    assert label_from_filename("03_illustrij_v20.png") == "illustrij_v20"
    assert label_from_filename("03_illustrij_v20_2.png") == "illustrij_v20_2"
    assert label_from_filename("grid.png") == "grid"


def test_list_tiles_skips_grid_and_sorts_naturally(tmp_path):
    for name in ("10_b.png", "2_a.png", "grid.png", "grid_preview.png", "notes.txt"):
        (tmp_path / name).write_bytes(b"")
    assert list_tiles(str(tmp_path)) == [
        str(tmp_path / "2_a.png"),
        str(tmp_path / "10_b.png"),
    ]


class TestBuildContactSheet:
    def _tiles(self, tmp_path, n, size=(100, 200)):
        paths = []
        for i in range(n):
            p = tmp_path / f"{i:02d}_m{i}.png"
            Image.new("RGB", size, (i * 40, 0, 0)).save(p)
            paths.append(str(p))
        return paths

    def test_grid_dimensions_follow_columns_and_tile_width(self, tmp_path):
        paths = self._tiles(tmp_path, 3)
        sheet = build_contact_sheet(paths, columns=2, tile_width=50, font_size=10)
        # 3 tiles in 2 columns = 2 rows; tiles scale to 50x100; label band 2*font
        assert sheet.size == (100, 2 * (100 + 20))

    def test_fewer_tiles_than_columns_shrinks_width(self, tmp_path):
        paths = self._tiles(tmp_path, 1)
        sheet = build_contact_sheet(paths, columns=5, tile_width=50, font_size=10)
        assert sheet.size == (50, 100 + 20)

    def test_label_band_is_drawn(self, tmp_path):
        paths = self._tiles(tmp_path, 1)
        sheet = build_contact_sheet(paths, columns=1, tile_width=50, font_size=10)
        band = sheet.crop((0, 100, 50, 120))
        assert len(band.getcolors(maxcolors=4096) or []) > 1


def _prompt(text="a cat", index=0, seed=1000, columns=3):
    return {
        "1": {
            "class_type": "CheckpointFolderIterator",
            "inputs": {"folder": "Moss", "index": index},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": text, "clip": ["9", 0]},
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {"seed": seed, "steps": 25, "model": ["1", 0]},
        },
        "4": {"class_type": "SeedHistory", "inputs": {"seed": seed}},
        "5": {
            "class_type": "ModelCompareSheet",
            "inputs": {
                "images": ["6", 0],
                "label": ["1", 4],
                "index": ["1", 5],
                "columns": columns,
            },
        },
    }


class TestSweepFingerprint:
    def test_iterator_index_does_not_count(self):
        assert sweep_fingerprint(_prompt(index=0), "5") == sweep_fingerprint(
            _prompt(index=4), "5"
        )

    def test_seeds_do_not_count(self):
        assert sweep_fingerprint(_prompt(seed=1), "5") == sweep_fingerprint(
            _prompt(seed=2), "5"
        )

    def test_sheet_layout_does_not_count(self):
        assert sweep_fingerprint(_prompt(columns=3), "5") == sweep_fingerprint(
            _prompt(columns=5), "5"
        )

    def test_prompt_change_counts(self):
        assert sweep_fingerprint(_prompt("a cat"), "5") != sweep_fingerprint(
            _prompt("a dog"), "5"
        )

    def test_rewiring_the_sheet_to_another_image_source_counts(self):
        rewired = _prompt()
        rewired["5"]["inputs"]["images"] = ["7", 0]
        assert sweep_fingerprint(rewired, "5") != sweep_fingerprint(_prompt(), "5")

    def test_unknown_prompt_or_sheet_gives_none(self):
        assert sweep_fingerprint(None, "5") is None
        assert sweep_fingerprint(_prompt(), None) is None
        assert sweep_fingerprint(_prompt(), "99") is None
