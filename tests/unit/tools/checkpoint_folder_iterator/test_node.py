"""Tests for the Checkpoint Folder Iterator node."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from kikotools.tools.checkpoint_folder_iterator import CheckpointFolderIteratorNode

NODE = "kikotools.tools.checkpoint_folder_iterator.node"
ENTRIES = [
    ("X/a_v1.safetensors", "/models/checkpoints/X/a_v1.safetensors"),
    ("X/b_v2.safetensors", "/models/checkpoints/X/b_v2.safetensors"),
]


def _fake_comfy_modules():
    fp = MagicMock()
    fp.get_folder_paths = MagicMock(return_value=["/models/embeddings"])
    comfy = MagicMock()
    comfy.sd.load_checkpoint_guess_config = MagicMock(
        return_value=("MODEL", "CLIP", "VAE", "extra")
    )
    return (
        patch.dict(
            sys.modules, {"folder_paths": fp, "comfy": comfy, "comfy.sd": comfy.sd}
        ),
        fp,
        comfy,
    )


class TestCheckpointFolderIteratorNode:
    def test_input_index_increments_after_generate(self):
        index = CheckpointFolderIteratorNode.INPUT_TYPES()["required"]["index"]
        assert index[0] == "INT"
        assert index[1]["control_after_generate"] is True

    def test_loads_the_indexed_checkpoint_from_its_scanned_path(self):
        ctx, fp, comfy = _fake_comfy_modules()
        with ctx, patch(f"{NODE}.list_checkpoint_entries", return_value=ENTRIES):
            out = CheckpointFolderIteratorNode().load("X", 1, "", "")
        comfy.sd.load_checkpoint_guess_config.assert_called_once()
        assert comfy.sd.load_checkpoint_guess_config.call_args.args == (
            "/models/checkpoints/X/b_v2.safetensors",
        )
        fp.get_full_path_or_raise.assert_not_called()
        assert out == ("MODEL", "CLIP", "VAE", "X/b_v2.safetensors", "b_v2", 1, 2)

    def test_absolute_folder_outside_models_dir_loads_by_real_path(self):
        ctx, _, comfy = _fake_comfy_modules()
        external = [("ext_v1.safetensors", "/mnt/drive/ckpts/ext_v1.safetensors")]
        with ctx, patch(f"{NODE}.list_checkpoint_entries", return_value=external):
            out = CheckpointFolderIteratorNode().load("/mnt/drive/ckpts", 0, "", "")
        assert comfy.sd.load_checkpoint_guess_config.call_args.args == (
            "/mnt/drive/ckpts/ext_v1.safetensors",
        )
        assert out[3:] == ("ext_v1.safetensors", "ext_v1", 0, 1)

    def test_index_past_the_end_raises_instead_of_restarting(self):
        ctx, _, comfy = _fake_comfy_modules()
        with ctx, patch(f"{NODE}.list_checkpoint_entries", return_value=ENTRIES):
            with pytest.raises(ValueError, match="past the end"):
                CheckpointFolderIteratorNode().load("X", 2, "", "")
        comfy.sd.load_checkpoint_guess_config.assert_not_called()

    def test_empty_folder_raises_clear_error(self):
        ctx, _, _ = _fake_comfy_modules()
        with ctx, patch(f"{NODE}.list_checkpoint_entries", return_value=[]):
            with pytest.raises(ValueError, match="No checkpoints"):
                CheckpointFolderIteratorNode().load("Empty", 0, "", "")
