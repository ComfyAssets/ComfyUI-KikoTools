"""Pure tensor split/join functions for batch-list conversions."""

import torch
from typing import Dict, List


def split_image_batch(images: torch.Tensor) -> List[torch.Tensor]:
    """Split [B,H,W,C] image batch into list of [1,H,W,C] tensors."""
    return [images[i : i + 1] for i in range(images.shape[0])]


def join_image_batch(image_list: List[torch.Tensor]) -> torch.Tensor:
    """Join list of image tensors into single [B,H,W,C] batch."""
    return torch.cat(image_list, dim=0)


def split_latent_batch(
    latent: Dict[str, torch.Tensor],
) -> List[Dict[str, torch.Tensor]]:
    """Split latent dict into list of single-item latent dicts."""
    samples = latent["samples"]
    return [{"samples": samples[i : i + 1]} for i in range(samples.shape[0])]


def join_latent_batch(
    latent_list: List[Dict[str, torch.Tensor]],
) -> Dict[str, torch.Tensor]:
    """Join list of latent dicts into single batched latent dict."""
    return {"samples": torch.cat([lat["samples"] for lat in latent_list], dim=0)}
