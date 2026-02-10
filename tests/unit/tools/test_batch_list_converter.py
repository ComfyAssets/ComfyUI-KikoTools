"""Tests for Batch/List conversion nodes and logic."""

import pytest
import torch

from kikotools.tools.batch_list_converter.logic import (
    split_image_batch,
    join_image_batch,
    split_latent_batch,
    join_latent_batch,
)
from kikotools.tools.batch_list_converter.node import (
    ImageBatchToImageListNode,
    ImageListToImageBatchNode,
    LatentBatchToLatentListNode,
    LatentListToLatentBatchNode,
)


class TestBatchListConverterLogic:
    """Test pure split/join functions."""

    # -- Image split --

    def test_split_image_batch_single(self):
        """Single image batch returns list of one."""
        images = torch.rand(1, 64, 64, 3)
        result = split_image_batch(images)
        assert len(result) == 1
        assert result[0].shape == (1, 64, 64, 3)
        assert torch.equal(result[0], images)

    def test_split_image_batch_multiple(self):
        """Multi-image batch splits correctly."""
        images = torch.rand(4, 64, 64, 3)
        result = split_image_batch(images)
        assert len(result) == 4
        for i, img in enumerate(result):
            assert img.shape == (1, 64, 64, 3)
            assert torch.equal(img, images[i : i + 1])

    def test_split_image_preserves_batch_dim(self):
        """Each split image keeps 4D shape [1,H,W,C]."""
        images = torch.rand(3, 128, 256, 3)
        result = split_image_batch(images)
        for img in result:
            assert img.ndim == 4
            assert img.shape[0] == 1

    # -- Image join --

    def test_join_image_batch_single(self):
        """Join single image produces batch of 1."""
        image_list = [torch.rand(1, 64, 64, 3)]
        result = join_image_batch(image_list)
        assert result.shape == (1, 64, 64, 3)

    def test_join_image_batch_multiple(self):
        """Join multiple images into batch."""
        image_list = [torch.rand(1, 64, 64, 3) for _ in range(5)]
        result = join_image_batch(image_list)
        assert result.shape == (5, 64, 64, 3)

    def test_image_roundtrip(self):
        """split -> join produces identical tensor."""
        original = torch.rand(4, 64, 64, 3)
        reconstructed = join_image_batch(split_image_batch(original))
        assert torch.equal(original, reconstructed)

    # -- Latent split --

    def test_split_latent_batch_single(self):
        """Single latent returns list of one dict."""
        latent = {"samples": torch.rand(1, 4, 32, 32)}
        result = split_latent_batch(latent)
        assert len(result) == 1
        assert "samples" in result[0]
        assert result[0]["samples"].shape == (1, 4, 32, 32)

    def test_split_latent_batch_multiple(self):
        """Multi-item latent splits correctly."""
        latent = {"samples": torch.rand(3, 4, 32, 32)}
        result = split_latent_batch(latent)
        assert len(result) == 3
        for i, lat in enumerate(result):
            assert lat["samples"].shape == (1, 4, 32, 32)
            assert torch.equal(lat["samples"], latent["samples"][i : i + 1])

    # -- Latent join --

    def test_join_latent_batch_single(self):
        """Join single latent dict."""
        latent_list = [{"samples": torch.rand(1, 4, 32, 32)}]
        result = join_latent_batch(latent_list)
        assert "samples" in result
        assert result["samples"].shape == (1, 4, 32, 32)

    def test_join_latent_batch_multiple(self):
        """Join multiple latent dicts into batch."""
        latent_list = [{"samples": torch.rand(1, 4, 32, 32)} for _ in range(4)]
        result = join_latent_batch(latent_list)
        assert result["samples"].shape == (4, 4, 32, 32)

    def test_latent_roundtrip(self):
        """split -> join produces identical tensor."""
        original = {"samples": torch.rand(5, 4, 64, 64)}
        reconstructed = join_latent_batch(split_latent_batch(original))
        assert torch.equal(original["samples"], reconstructed["samples"])

    def test_split_latent_preserves_noise_mask(self):
        """noise_mask is sliced alongside samples."""
        latent = {
            "samples": torch.rand(3, 4, 32, 32),
            "noise_mask": torch.rand(3, 1, 32, 32),
        }
        result = split_latent_batch(latent)
        assert len(result) == 3
        for i, item in enumerate(result):
            assert "noise_mask" in item
            assert item["noise_mask"].shape == (1, 1, 32, 32)
            assert torch.equal(item["noise_mask"], latent["noise_mask"][i : i + 1])

    def test_join_latent_preserves_noise_mask(self):
        """noise_mask is concatenated alongside samples."""
        latent_list = [
            {
                "samples": torch.rand(1, 4, 32, 32),
                "noise_mask": torch.rand(1, 1, 32, 32),
            }
            for _ in range(3)
        ]
        result = join_latent_batch(latent_list)
        assert "noise_mask" in result
        assert result["noise_mask"].shape == (3, 1, 32, 32)

    def test_latent_roundtrip_with_extra_keys(self):
        """Round-trip preserves all tensor keys."""
        original = {
            "samples": torch.rand(4, 4, 64, 64),
            "noise_mask": torch.rand(4, 1, 64, 64),
        }
        reconstructed = join_latent_batch(split_latent_batch(original))
        assert torch.equal(original["samples"], reconstructed["samples"])
        assert torch.equal(original["noise_mask"], reconstructed["noise_mask"])

    def test_split_latent_copies_non_tensor_values(self):
        """Non-tensor metadata is copied to each item."""
        latent = {
            "samples": torch.rand(2, 4, 32, 32),
            "some_flag": "preserve_me",
        }
        result = split_latent_batch(latent)
        for item in result:
            assert item["some_flag"] == "preserve_me"


class TestBatchListConverterNodes:
    """Test ComfyUI node classes."""

    # -- ImageBatchToImageList --

    def test_image_b2l_attributes(self):
        assert ImageBatchToImageListNode.RETURN_TYPES == ("IMAGE", "INT")
        assert ImageBatchToImageListNode.RETURN_NAMES == ("images", "count")
        assert ImageBatchToImageListNode.OUTPUT_IS_LIST == (True, False)
        assert ImageBatchToImageListNode.FUNCTION == "split_batch"
        assert ImageBatchToImageListNode.CATEGORY == "🫶 ComfyAssets/📦 Latents"

    def test_image_b2l_input_types(self):
        inputs = ImageBatchToImageListNode.INPUT_TYPES()
        assert "required" in inputs
        assert "images" in inputs["required"]
        assert inputs["required"]["images"] == ("IMAGE",)

    def test_image_b2l_execute(self):
        node = ImageBatchToImageListNode()
        images = torch.rand(3, 64, 64, 3)
        result = node.split_batch(images)
        image_list, count = result
        assert isinstance(image_list, list)
        assert len(image_list) == 3
        assert count == 3

    # -- ImageListToImageBatch --

    def test_image_l2b_attributes(self):
        assert ImageListToImageBatchNode.INPUT_IS_LIST is True
        assert ImageListToImageBatchNode.RETURN_TYPES == ("IMAGE", "INT")
        assert ImageListToImageBatchNode.RETURN_NAMES == ("images", "count")
        assert ImageListToImageBatchNode.FUNCTION == "join_batch"

    def test_image_l2b_execute(self):
        node = ImageListToImageBatchNode()
        image_list = [torch.rand(1, 64, 64, 3) for _ in range(4)]
        batch, count = node.join_batch(image_list)
        assert batch.shape == (4, 64, 64, 3)
        assert count == 4

    # -- LatentBatchToLatentList --

    def test_latent_b2l_attributes(self):
        assert LatentBatchToLatentListNode.RETURN_TYPES == ("LATENT", "INT")
        assert LatentBatchToLatentListNode.RETURN_NAMES == ("latents", "count")
        assert LatentBatchToLatentListNode.OUTPUT_IS_LIST == (True, False)
        assert LatentBatchToLatentListNode.FUNCTION == "split_batch"

    def test_latent_b2l_execute(self):
        node = LatentBatchToLatentListNode()
        latent = {"samples": torch.rand(2, 4, 32, 32)}
        latent_list, count = node.split_batch(latent)
        assert isinstance(latent_list, list)
        assert len(latent_list) == 2
        assert count == 2

    # -- LatentListToLatentBatch --

    def test_latent_l2b_attributes(self):
        assert LatentListToLatentBatchNode.INPUT_IS_LIST is True
        assert LatentListToLatentBatchNode.RETURN_TYPES == ("LATENT", "INT")
        assert LatentListToLatentBatchNode.RETURN_NAMES == ("latent", "count")
        assert LatentListToLatentBatchNode.FUNCTION == "join_batch"

    def test_latent_l2b_execute(self):
        node = LatentListToLatentBatchNode()
        latent_list = [{"samples": torch.rand(1, 4, 32, 32)} for _ in range(3)]
        batch, count = node.join_batch(latent_list)
        assert "samples" in batch
        assert batch["samples"].shape == (3, 4, 32, 32)
        assert count == 3

    # -- Inheritance --

    def test_all_nodes_inherit_base(self):
        from kikotools.base.base_node import ComfyAssetsBaseNode

        for cls in (
            ImageBatchToImageListNode,
            ImageListToImageBatchNode,
            LatentBatchToLatentListNode,
            LatentListToLatentBatchNode,
        ):
            assert issubclass(cls, ComfyAssetsBaseNode)

    # -- Registration mappings --

    def test_node_class_mappings(self):
        from kikotools.tools.batch_list_converter.node import NODE_CLASS_MAPPINGS

        assert len(NODE_CLASS_MAPPINGS) == 4
        assert "ImageBatchToImageList" in NODE_CLASS_MAPPINGS
        assert "ImageListToImageBatch" in NODE_CLASS_MAPPINGS
        assert "LatentBatchToLatentList" in NODE_CLASS_MAPPINGS
        assert "LatentListToLatentBatch" in NODE_CLASS_MAPPINGS

    def test_node_display_name_mappings(self):
        from kikotools.tools.batch_list_converter.node import NODE_DISPLAY_NAME_MAPPINGS

        assert len(NODE_DISPLAY_NAME_MAPPINGS) == 4
        assert (
            NODE_DISPLAY_NAME_MAPPINGS["ImageBatchToImageList"]
            == "Image Batch to Image List"
        )
