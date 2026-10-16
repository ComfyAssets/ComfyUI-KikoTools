"""Tests for the Model Compare Sheet node."""

import os
import sys
from unittest.mock import MagicMock, patch

import torch
from PIL import Image

from kikotools.tools.model_compare_sheet import ModelCompareSheetNode


def _fake_output_dir(path):
    fp = MagicMock()
    fp.get_output_directory = MagicMock(return_value=str(path))
    return patch.dict(sys.modules, {"folder_paths": fp})


def _image(batch=1, h=64, w=32):
    return torch.rand(batch, h, w, 3)


class TestModelCompareSheetNode:
    def test_is_an_output_node(self):
        assert ModelCompareSheetNode.OUTPUT_NODE is True

    def test_saves_tile_and_grid_and_returns_grid(self, tmp_path):
        with _fake_output_dir(tmp_path):
            out = ModelCompareSheetNode().collect(
                _image(), "illustrij_v20", 3, "run1", 4, 32, 8
            )
        run_dir = tmp_path / "model_compare" / "run1"
        assert (run_dir / "03_illustrij_v20.png").exists()
        assert (run_dir / "grid.png").exists()
        grid = out["result"][0]
        assert grid.shape == (1, 64 + 16, 32, 3)
        assert out["ui"]["images"][0]["filename"] == "grid_preview.png"
        assert out["ui"]["images"][0]["subfolder"] == os.path.join(
            "model_compare", "run1"
        )

    def test_grid_grows_across_runs(self, tmp_path):
        with _fake_output_dir(tmp_path):
            node = ModelCompareSheetNode()
            node.collect(_image(), "a", 0, "run1", 4, 32, 8)
            out = node.collect(_image(), "b", 1, "run1", 4, 32, 8)
        assert out["result"][0].shape == (1, 64 + 16, 64, 3)

    def test_batch_saves_every_image(self, tmp_path):
        with _fake_output_dir(tmp_path):
            ModelCompareSheetNode().collect(_image(batch=2), "a", 0, "run1", 4, 32, 8)
        run_dir = tmp_path / "model_compare" / "run1"
        assert (run_dir / "00_a_1.png").exists()
        assert (run_dir / "00_a_2.png").exists()
        assert Image.open(run_dir / "grid.png").size == (64, 64 + 16)

    def test_rerun_of_same_index_overwrites_instead_of_duplicating(self, tmp_path):
        with _fake_output_dir(tmp_path):
            node = ModelCompareSheetNode()
            node.collect(_image(), "a", 0, "run1", 4, 32, 8)
            out = node.collect(_image(), "a", 0, "run1", 4, 32, 8)
        assert out["result"][0].shape[2] == 32


class TestArchiveOnNewSweep:
    def test_index_zero_archives_the_previous_sweep(self, tmp_path):
        with _fake_output_dir(tmp_path):
            node = ModelCompareSheetNode()
            node.collect(_image(), "a", 0, "run1", 4, 32, 8)
            node.collect(_image(), "b", 1, "run1", 4, 32, 8)
            out = node.collect(_image(), "c", 0, "run1", 4, 32, 8)
        run_dir = tmp_path / "model_compare" / "run1"
        assert sorted(p.name for p in run_dir.iterdir()) == [
            "00_c.png",
            "grid.png",
            "grid_preview.png",
        ]
        assert out["result"][0].shape[2] == 32
        archived = [p for p in run_dir.parent.iterdir() if p.name.startswith("run1_")]
        assert len(archived) == 1
        assert sorted(p.name for p in archived[0].iterdir()) == [
            "00_a.png",
            "01_b.png",
            "grid.png",
            "grid_preview.png",
        ]

    def test_nonzero_index_keeps_existing_tiles(self, tmp_path):
        with _fake_output_dir(tmp_path):
            node = ModelCompareSheetNode()
            node.collect(_image(), "a", 0, "run1", 4, 32, 8)
            node.collect(_image(), "b", 3, "run1", 4, 32, 8)
        run_dir = tmp_path / "model_compare" / "run1"
        assert sorted(p.name for p in run_dir.iterdir()) == [
            "00_a.png",
            "03_b.png",
            "grid.png",
            "grid_preview.png",
        ]

    def test_index_zero_on_empty_folder_archives_nothing(self, tmp_path):
        with _fake_output_dir(tmp_path):
            ModelCompareSheetNode().collect(_image(), "a", 0, "run1", 4, 32, 8)
        assert [p.name for p in (tmp_path / "model_compare").iterdir()] == ["run1"]


class TestPreview:
    def test_ui_preview_is_downscaled_but_grid_and_output_stay_full_size(
        self, tmp_path
    ):
        with _fake_output_dir(tmp_path):
            out = ModelCompareSheetNode().collect(
                _image(h=64, w=32), "a", 0, "run1", 1, 1200, 8
            )
        run_dir = tmp_path / "model_compare" / "run1"
        assert Image.open(run_dir / "grid.png").size[0] == 1200
        assert Image.open(run_dir / "grid_preview.png").size[0] == 1024
        assert out["result"][0].shape[2] == 1200
        assert out["ui"]["images"][0]["filename"] == "grid_preview.png"

    def test_small_grid_preview_is_not_upscaled(self, tmp_path):
        with _fake_output_dir(tmp_path):
            ModelCompareSheetNode().collect(_image(), "a", 0, "run1", 1, 32, 8)
        run_dir = tmp_path / "model_compare" / "run1"
        assert Image.open(run_dir / "grid_preview.png").size[0] == 32
