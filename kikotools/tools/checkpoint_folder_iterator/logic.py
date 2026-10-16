"""Logic for the Checkpoint Folder Iterator node."""

import os
from typing import List, Sequence, Tuple, TypeVar

from ...base.model_folders import filter_by_pattern, scan_model_entries

T = TypeVar("T")


def list_checkpoint_entries(
    folder_path: str, include_pattern: str = "", exclude_pattern: str = ""
) -> List[Tuple[str, str]]:
    """(name, absolute_path) pairs for every checkpoint, filtered, in natural order.

    The absolute path is what gets loaded, so folders outside the configured
    checkpoints roots work too; the name is relative to the root (or to the
    folder itself when it lives outside every root) and is used for labels.
    """
    entries = scan_model_entries(folder_path, "checkpoints")
    names = [name for name, _ in entries]
    kept = set(filter_by_pattern(names, include_pattern, exclude_pattern))
    return [(name, path) for name, path in entries if name in kept]


def list_checkpoints(
    folder_path: str, include_pattern: str = "", exclude_pattern: str = ""
) -> List[str]:
    """Checkpoint names (relative to the checkpoints roots) in natural order."""
    entries = list_checkpoint_entries(folder_path, include_pattern, exclude_pattern)
    return [name for name, _ in entries]


def pick_checkpoint(items: Sequence[T], index: int) -> T:
    """Return items[index], or raise when the sweep has run past the end.

    Wrapping would silently restart the sweep (and, downstream, archive the
    grid that just finished), so an over-queued run fails loudly instead.
    """
    if not items:
        raise ValueError("No checkpoints found")
    if not 0 <= index < len(items):
        raise ValueError(
            f"Index {index} is past the end: only {len(items)} checkpoints matched. "
            "The sweep is complete; reset index to 0 to start a new one."
        )
    return items[index]


def label_for(ckpt_name: str) -> str:
    """Label drawn under a tile for this checkpoint. Default: the file stem."""
    return os.path.splitext(os.path.basename(ckpt_name))[0]
