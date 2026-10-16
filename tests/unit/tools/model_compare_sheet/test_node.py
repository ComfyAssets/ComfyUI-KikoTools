"""Tests for the Model Compare Sheet node."""

import json
import os
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest
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


class TestReplaceIndex:
    @pytest.mark.parametrize(
        "old_batch, old_label, new_batch, new_label, expected",
        [
            (2, "a", 1, "a", ["01_a.png"]),
            (1, "a", 1, "b", ["01_b.png"]),
            (1, "a", 1, "A", ["01_A.png"]),
            (2, "a", 3, "b", ["01_b_1.png", "01_b_2.png", "01_b_3.png"]),
            (1, "a", 2, "a", ["01_a_1.png", "01_a_2.png"]),
            (3, "a", 2, "a", ["01_a_1.png", "01_a_2.png"]),
        ],
    )
    def test_rerun_replaces_only_its_index(
        self,
        tmp_path: Path,
        old_batch: int,
        old_label: str,
        new_batch: int,
        new_label: str,
        expected: list[str],
    ) -> None:
        with _fake_output_dir(tmp_path):
            node = ModelCompareSheetNode()
            node.collect(_image(), "first", 0, "run1", 8, 32, 8)
            node.collect(_image(batch=old_batch), old_label, 1, "run1", 8, 32, 8)
            node.collect(_image(), "neighbor", 10, "run1", 8, 32, 8)
            run_dir = tmp_path / "model_compare" / "run1"
            untouched = {
                name: (run_dir / name).read_bytes()
                for name in ("00_first.png", "10_neighbor.png")
            }
            (run_dir / "notes.txt").write_text("keep this note")
            archived = run_dir.parent / "run1_archived"
            archived.mkdir()
            (archived / "01_a.png").write_bytes(b"archived tile")
            result = node.collect(
                torch.ones(new_batch, 64, 32, 3),
                new_label,
                1,
                "run1",
                8,
                32,
                8,
                prompt={"model": "replacement"},
                extra_pnginfo={"workflow": {"id": "retry"}},
            )
        assert sorted(path.name for path in run_dir.glob("01_*.png")) == expected
        assert result["result"][0].shape == (1, 80, (new_batch + 2) * 32, 3)
        assert sorted(path.name for path in run_dir.iterdir()) == sorted(
            [
                "00_first.png",
                "10_neighbor.png",
                "grid.png",
                "grid_preview.png",
                "notes.txt",
                *expected,
            ]
        )
        for name, data in untouched.items():
            assert (run_dir / name).read_bytes() == data
        assert (run_dir / "notes.txt").read_text() == "keep this note"
        assert (archived / "01_a.png").read_bytes() == b"archived tile"
        for name in expected:
            with Image.open(run_dir / name) as image:
                assert image.getpixel((0, 0)) == (255, 255, 255)
                assert json.loads(image.info["prompt"]) == {"model": "replacement"}
                assert json.loads(image.info["workflow"]) == {"id": "retry"}

    @pytest.mark.parametrize("index", [0, 1])
    @pytest.mark.parametrize("failed_image", [1, 2])
    def test_failed_tile_write_preserves_the_existing_batch_and_grid(
        self, tmp_path: Path, index: int, failed_image: int
    ) -> None:
        with _fake_output_dir(tmp_path):
            node = ModelCompareSheetNode()
            node.collect(torch.zeros(2, 64, 32, 3), "same", index, "run1", 8, 32, 8)
            base = tmp_path / "model_compare"
            before = {
                str(path.relative_to(base)): path.read_bytes()
                for path in base.rglob("*")
                if path.is_file()
            }
            original_save = Image.Image.save
            tile_writes = 0

            def fail_tile_write(image, path, *args, **kwargs):
                nonlocal tile_writes
                if Path(path).name.startswith(f"{index:02d}_"):
                    tile_writes += 1
                    if tile_writes == failed_image:
                        raise OSError("disk full")
                return original_save(image, path, *args, **kwargs)

            with patch.object(Image.Image, "save", new=fail_tile_write):
                with pytest.raises(OSError, match="disk full"):
                    node.collect(
                        torch.ones(2, 64, 32, 3), "same", index, "run1", 8, 32, 8
                    )
        assert {
            str(path.relative_to(base)): path.read_bytes()
            for path in base.rglob("*")
            if path.is_file()
        } == before
        assert list(base.iterdir()) == [base / "run1"]

    def test_empty_batch_does_not_remove_existing_tiles(self, tmp_path: Path) -> None:
        with _fake_output_dir(tmp_path):
            node = ModelCompareSheetNode()
            node.collect(_image(), "a", 1, "run1", 8, 32, 8)
            run_dir = tmp_path / "model_compare" / "run1"
            before = {path.name: path.read_bytes() for path in run_dir.iterdir()}
            with pytest.raises(ValueError, match="at least one image"):
                node.collect(torch.empty(0, 64, 32, 3), "b", 1, "run1", 8, 32, 8)
        assert {path.name: path.read_bytes() for path in run_dir.iterdir()} == before

    @pytest.mark.parametrize("failed_image", [1, 2])
    def test_failed_publication_restores_the_previous_batch(
        self, tmp_path: Path, failed_image: int
    ) -> None:
        with _fake_output_dir(tmp_path):
            node = ModelCompareSheetNode()
            node.collect(torch.zeros(2, 64, 32, 3), "same", 1, "run1", 8, 32, 8)
            base = tmp_path / "model_compare"
            run_dir = base / "run1"
            before = {
                str(path.relative_to(base)): path.read_bytes()
                for path in base.rglob("*")
                if path.is_file()
            }
            original_replace = os.replace
            published = 0

            def fail_publication(source, destination):
                nonlocal published
                if (
                    Path(destination).parent == run_dir
                    and Path(source).parent.name != "previous"
                ):
                    published += 1
                    if published == failed_image:
                        raise OSError("publication failed")
                return original_replace(source, destination)

            with patch("os.replace", side_effect=fail_publication):
                with pytest.raises(OSError, match="publication failed"):
                    node.collect(torch.ones(2, 64, 32, 3), "same", 1, "run1", 8, 32, 8)
        assert {
            str(path.relative_to(base)): path.read_bytes()
            for path in base.rglob("*")
            if path.is_file()
        } == before
        assert list(base.iterdir()) == [run_dir]

    def test_rerun_preserves_directories_with_tile_like_names(
        self, tmp_path: Path
    ) -> None:
        with _fake_output_dir(tmp_path):
            node = ModelCompareSheetNode()
            node.collect(_image(), "a", 1, "run1", 8, 32, 8)
            run_dir = tmp_path / "model_compare" / "run1"
            notes = run_dir / "01_notes.png"
            notes.mkdir()
            (notes / "notes.txt").write_text("keep this folder")
            node.collect(_image(), "b", 1, "run1", 8, 32, 8)
        assert (notes / "notes.txt").read_text() == "keep this folder"
        assert (run_dir / "01_b.png").is_file()
        assert not (run_dir / "01_a.png").exists()

    def test_staging_does_not_expose_temporary_images_to_output_galleries(
        self, tmp_path: Path
    ) -> None:
        with _fake_output_dir(tmp_path):
            node = ModelCompareSheetNode()
            node.collect(_image(), "a", 1, "run1", 8, 32, 8)
            base = tmp_path / "model_compare"
            run_dir = base / "run1"
            temporary_images = []
            original_save = Image.Image.save
            original_replace = os.replace

            def observe_images() -> None:
                temporary_images.extend(
                    path for path in base.rglob("*.png") if path.parent != run_dir
                )

            def save_and_observe(image, path, *args, **kwargs):
                result = original_save(image, path, *args, **kwargs)
                observe_images()
                return result

            def replace_and_observe(source, destination):
                result = original_replace(source, destination)
                observe_images()
                return result

            with patch.object(Image.Image, "save", new=save_and_observe):
                with patch("os.replace", side_effect=replace_and_observe):
                    node.collect(_image(batch=2), "b", 1, "run1", 8, 32, 8)
        assert temporary_images == []
