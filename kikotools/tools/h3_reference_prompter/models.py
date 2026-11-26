"""Model picker listing for the H3 Reference Prompter.

Merges Hugging Face transformers folders under ``models/LLM`` with the
vision-capable models the Kiko Prompt Enhancer already finds. The Enhancer's
own picker is left untouched.
"""

import json
import os
from pathlib import Path
from typing import List, Optional

from ..prompt_enhancer.models import NONE_FOUND, ModelEntry, list_models

HF_ARCHITECTURES = (
    "Qwen3_5ForConditionalGeneration",
    "Qwen3VLForConditionalGeneration",
    "Gemma4ForConditionalGeneration",
    "Gemma4UnifiedForConditionalGeneration",
)

PREFERRED_DEFAULT = "Qwen3.5-4B"


def _is_recognised(folder: Path) -> bool:
    try:
        config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(config, dict):
        return False
    architectures = config.get("architectures")
    if not isinstance(architectures, list):
        return False
    return any(arch in HF_ARCHITECTURES for arch in architectures)


def hf_entries(llm_root: Path) -> List[ModelEntry]:
    """List transformers folders under ``llm_root``, never descending into one."""
    llm_root = Path(llm_root)
    if not llm_root.is_dir():
        return []
    entries = []
    for folder, dirs, _ in os.walk(llm_root, followlinks=True):
        dirs.sort()
        path = Path(folder)
        if not _is_recognised(path):
            continue
        dirs.clear()
        entries.append(
            ModelEntry(
                name=f"hf: {path.relative_to(llm_root).as_posix()}",
                kind="hf",
                path=path,
                vision=True,
                mmproj=None,
                clip_type=None,
            )
        )
    return entries


def _usable_enhancer_entry(entry: ModelEntry) -> bool:
    if not entry.vision:
        return False
    return entry.kind != "gguf" or entry.mmproj is not None


def list_prompter_models() -> List[ModelEntry]:
    import folder_paths

    llm_root = Path(os.path.join(folder_paths.models_dir, "LLM"))
    candidates = hf_entries(llm_root) + [
        entry for entry in list_models() if _usable_enhancer_entry(entry)
    ]
    unique = {}
    for entry in candidates:
        unique.setdefault(entry.name, entry)
    return sorted(unique.values(), key=lambda entry: entry.name)


def prompter_model_names() -> List[str]:
    return [entry.name for entry in list_prompter_models()] or [NONE_FOUND]


def find_prompter_model(name: str) -> Optional[ModelEntry]:
    return next((e for e in list_prompter_models() if e.name == name), None)


def default_prompter_model(names: List[str]) -> str:
    for name in names:
        if PREFERRED_DEFAULT in name:
            return name
    for name in names:
        if name.startswith("hf: "):
            return name
    return names[0]
