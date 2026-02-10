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
    """Split latent dict into list of single-item latent dicts.

    Preserves all keys (e.g. noise_mask, batch_index). Tensor values whose
    first dimension matches the batch size of ``samples`` are sliced along
    dim-0; all other values are copied as-is to every item.
    """
    samples = latent["samples"]
    batch_size = samples.shape[0]
    result: List[Dict[str, torch.Tensor]] = []
    for i in range(batch_size):
        item: Dict[str, torch.Tensor] = {}
        for key, value in latent.items():
            if isinstance(value, torch.Tensor) and value.shape[0] == batch_size:
                item[key] = value[i : i + 1]
            else:
                item[key] = value
        result.append(item)
    return result


def join_latent_batch(
    latent_list: List[Dict[str, torch.Tensor]],
) -> Dict[str, torch.Tensor]:
    """Join list of latent dicts into single batched latent dict.

    Tensor values that were sliced during split are concatenated along dim-0.
    Non-tensor values are taken from the first item.
    """
    result: Dict[str, torch.Tensor] = {}
    first = latent_list[0]
    for key in first:
        if isinstance(first[key], torch.Tensor):
            result[key] = torch.cat([lat[key] for lat in latent_list], dim=0)
        else:
            result[key] = first[key]
    return result
