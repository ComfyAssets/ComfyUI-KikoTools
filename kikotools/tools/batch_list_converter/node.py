"""Batch/List conversion nodes for ComfyUI."""

from typing import Dict, List, Tuple

import torch

from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    split_image_batch,
    join_image_batch,
    split_latent_batch,
    join_latent_batch,
)


class ImageBatchToImageListNode(ComfyAssetsBaseNode):
    """Split an IMAGE batch [B,H,W,C] into a list of individual images."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("images", "count")
    OUTPUT_IS_LIST = (True, False)
    FUNCTION = "split_batch"
    CATEGORY = "🫶 ComfyAssets/📦 Latents"

    def split_batch(self, images: torch.Tensor) -> Tuple[List[torch.Tensor], int]:
        image_list = split_image_batch(images)
        count = len(image_list)
        self.log_info(f"Split image batch of {count} into list")
        return (image_list, count)


class ImageListToImageBatchNode(ComfyAssetsBaseNode):
    """Join a list of IMAGE tensors into a single batched IMAGE [B,H,W,C]."""

    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "INT")
    RETURN_NAMES = ("images", "count")
    FUNCTION = "join_batch"
    CATEGORY = "🫶 ComfyAssets/📦 Latents"

    def join_batch(self, images: List[torch.Tensor]) -> Tuple[torch.Tensor, int]:
        batch = join_image_batch(images)
        count = batch.shape[0]
        self.log_info(f"Joined {count} images into batch")
        return (batch, count)


class LatentBatchToLatentListNode(ComfyAssetsBaseNode):
    """Split a LATENT batch into a list of individual latent dicts."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latent": ("LATENT",),
            }
        }

    RETURN_TYPES = ("LATENT", "INT")
    RETURN_NAMES = ("latents", "count")
    OUTPUT_IS_LIST = (True, False)
    FUNCTION = "split_batch"
    CATEGORY = "🫶 ComfyAssets/📦 Latents"

    def split_batch(
        self, latent: Dict[str, torch.Tensor]
    ) -> Tuple[List[Dict[str, torch.Tensor]], int]:
        latent_list = split_latent_batch(latent)
        count = len(latent_list)
        self.log_info(f"Split latent batch of {count} into list")
        return (latent_list, count)


class LatentListToLatentBatchNode(ComfyAssetsBaseNode):
    """Join a list of LATENT dicts into a single batched LATENT."""

    INPUT_IS_LIST = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "latents": ("LATENT",),
            }
        }

    RETURN_TYPES = ("LATENT", "INT")
    RETURN_NAMES = ("latent", "count")
    FUNCTION = "join_batch"
    CATEGORY = "🫶 ComfyAssets/📦 Latents"

    def join_batch(
        self, latents: List[Dict[str, torch.Tensor]]
    ) -> Tuple[Dict[str, torch.Tensor], int]:
        batch = join_latent_batch(latents)
        count = batch["samples"].shape[0]
        self.log_info(f"Joined {count} latents into batch")
        return (batch, count)


NODE_CLASS_MAPPINGS = {
    "ImageBatchToImageList": ImageBatchToImageListNode,
    "ImageListToImageBatch": ImageListToImageBatchNode,
    "LatentBatchToLatentList": LatentBatchToLatentListNode,
    "LatentListToLatentBatch": LatentListToLatentBatchNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImageBatchToImageList": "Image Batch to Image List",
    "ImageListToImageBatch": "Image List to Image Batch",
    "LatentBatchToLatentList": "Latent Batch to Latent List",
    "LatentListToLatentBatch": "Latent List to Latent Batch",
}
