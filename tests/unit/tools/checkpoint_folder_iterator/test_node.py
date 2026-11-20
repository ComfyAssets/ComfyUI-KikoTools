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
    comfy.sd.load_diffusion_model = MagicMock(return_value="UNET")
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

    def test_model_type_defaults_to_checkpoint(self):
        model_type = CheckpointFolderIteratorNode.INPUT_TYPES()["optional"][
            "model_type"
        ]
        assert model_type[0] == ["checkpoint", "diffusion_model"]
        assert model_type[1]["default"] == "checkpoint"

    def test_diffusion_model_scans_diffusion_models_and_loads_model_only(self):
        ctx, _, comfy = _fake_comfy_modules()
        unets = [
            ("Moss/sft.safetensors", "/models/diffusion_models/Moss/sft.safetensors")
        ]
        with (
            ctx,
            patch(f"{NODE}.list_checkpoint_entries", return_value=unets) as listing,
        ):
            out = CheckpointFolderIteratorNode().load(
                "Moss", 0, "", "", model_type="diffusion_model"
            )
        assert listing.call_args.args[3] == "diffusion_models"
        comfy.sd.load_diffusion_model.assert_called_once_with(
            "/models/diffusion_models/Moss/sft.safetensors"
        )
        comfy.sd.load_checkpoint_guess_config.assert_not_called()
        assert out == ("UNET", None, None, "Moss/sft.safetensors", "sft", 0, 1)
