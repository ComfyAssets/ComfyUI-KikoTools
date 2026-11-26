"""Pure helpers for the H3 Reference Prompter."""

import hashlib
import json
import re
from typing import Any, Dict, List, Set, Tuple

import torch

from kikotools.tools.prompt_enhancer.logic import clean_output, split_thinking

ROLES: Tuple[str, ...] = ("character", "outfit", "pose", "other")
DEFAULT_ROLES: Tuple[str, ...] = ("character", "outfit", "pose")
SLOTS = 3

_TAG = re.compile(r"<\s*Picture\s+(\d+)\s*>")
_PREAMBLE_LINE = re.compile(
    r"^\s*(?:here (?:is|'s)\b[^\n]*:[ \t]*(?:\n|\Z)"
    r"|(?:(?:final|enhanced|revised) )?prompt[ \t]*:[ \t]*)",
    re.IGNORECASE,
)
_SEED_MODULUS = 2**64


def find_tags(text: str) -> Set[int]:
    return {int(number) for number in _TAG.findall(text)}


def tag_problems(draft: str, result: str) -> Tuple[List[int], List[int]]:
    wanted = find_tags(draft)
    produced = find_tags(result)
    return sorted(wanted - produced), sorted(produced - wanted)


def pair_items(**columns: List[Any]) -> List[Dict[str, Any]]:
    lengths = {name: len(values) for name, values in columns.items()}
    sized = {length for length in lengths.values() if length > 1}
    if len(sized) > 1:
        described = ", ".join(f"{name} has {n}" for name, n in lengths.items())
        raise ValueError(f"input lists must share one length: {described}")
    count = sized.pop() if sized else 1
    items: List[Dict[str, Any]] = []
    for index in range(count):
        item: Dict[str, Any] = {}
        for name, values in columns.items():
            if not values:
                item[name] = None
            elif len(values) == 1:
                item[name] = values[0]
            else:
                item[name] = values[index]
        items.append(item)
    return items


def item_seed(seed: int, index: int) -> int:
    return (seed + index) % _SEED_MODULUS


def image_key(image: torch.Tensor, role: str, model: str) -> str:
    contiguous = image.detach().to("cpu").contiguous()
    header = json.dumps([list(contiguous.shape), role, model])
    digest = hashlib.sha256(header.encode())
    digest.update(contiguous.reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def clean_result(text: str) -> str:
    bare = split_thinking(text)
    bare = _PREAMBLE_LINE.sub("", bare, count=1)
    return clean_output(bare)
