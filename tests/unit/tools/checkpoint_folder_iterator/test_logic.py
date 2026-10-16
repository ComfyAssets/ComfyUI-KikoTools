"""Tests for Checkpoint Folder Iterator logic."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from kikotools.tools.checkpoint_folder_iterator.logic import (
    label_for,
    list_checkpoint_entries,
    list_checkpoints,
    pick_checkpoint,
)


def _touch(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("x")


def _fake_checkpoints(root):
    fp = MagicMock()
    fp.folder_names_and_paths = {"checkpoints": [[str(root)]]}
    return patch.dict(sys.modules, {"folder_paths": fp})


class TestListCheckpoints:
    def test_lists_safetensors_in_natural_order(self, tmp_path):
        for name in ("illustrij_v20", "illustrij_v3", "ilustmix_v9"):
            _touch(str(tmp_path / "Illustrious" / f"{name}.safetensors"))
        _touch(str(tmp_path / "Illustrious" / "illustrij_v20.jpeg"))
        with _fake_checkpoints(tmp_path):
            names = list_checkpoints("Illustrious")
        assert names == [
            "Illustrious/illustrij_v3.safetensors",
            "Illustrious/illustrij_v20.safetensors",
            "Illustrious/ilustmix_v9.safetensors",
        ]

    def test_include_and_exclude_patterns(self, tmp_path):
        for name in ("a_v1", "a_v2", "b_v1"):
            _touch(str(tmp_path / "X" / f"{name}.safetensors"))
        with _fake_checkpoints(tmp_path):
            names = list_checkpoints("X", include_pattern="^X/a_", exclude_pattern="v2")
        assert names == ["X/a_v1.safetensors"]


class TestListCheckpointEntries:
    def test_pairs_each_name_with_its_absolute_path(self, tmp_path):
        _touch(str(tmp_path / "X" / "a_v1.safetensors"))
        with _fake_checkpoints(tmp_path):
            entries = list_checkpoint_entries("X")
        assert entries == [
            ("X/a_v1.safetensors", str(tmp_path / "X" / "a_v1.safetensors"))
        ]

    def test_patterns_apply_to_entries_too(self, tmp_path):
        for name in ("a_v1", "a_v2", "b_v1"):
            _touch(str(tmp_path / "X" / f"{name}.safetensors"))
        with _fake_checkpoints(tmp_path):
            entries = list_checkpoint_entries("X", "^X/a_", "v2")
        assert [name for name, _ in entries] == ["X/a_v1.safetensors"]

    def test_absolute_folder_outside_roots_keeps_real_paths(self, tmp_path):
        root = tmp_path / "models" / "checkpoints"
        elsewhere = tmp_path / "external_drive" / "ckpts"
        _touch(str(elsewhere / "ext_v1.safetensors"))
        with _fake_checkpoints(root):
            entries = list_checkpoint_entries(str(elsewhere))
        assert entries == [
            ("ext_v1.safetensors", str(elsewhere / "ext_v1.safetensors"))
        ]


class TestPickCheckpoint:
    def test_returns_the_indexed_item(self):
        names = ["a", "b", "c"]
        assert pick_checkpoint(names, 0) == "a"
        assert pick_checkpoint(names, 2) == "c"

    def test_index_past_the_end_raises_instead_of_wrapping(self):
        with pytest.raises(ValueError, match="past the end.*3 checkpoints"):
            pick_checkpoint(["a", "b", "c"], 3)

    def test_negative_index_raises(self):
        with pytest.raises(ValueError, match="past the end"):
            pick_checkpoint(["a"], -1)

    def test_empty_list_raises(self):
        with pytest.raises(ValueError, match="No checkpoints"):
            pick_checkpoint([], 0)


class TestLabelFor:
    def test_default_label_is_the_file_stem(self):
        assert label_for("Illustrious/illustrij_v20.safetensors") == "illustrij_v20"
        assert label_for("Illustrious/reijlita/x_v1.safetensors") == "x_v1"
