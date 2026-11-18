"""Local LLM discovery for the Kiko Prompt Enhancer model picker.

Two kinds are listed: safetensors text encoders in ``text_encoders`` that core
ComfyUI can generate text with (classified with ``comfy.sd.detect_te_model``),
and llama.cpp GGUF models in ``models/LLM`` or ``text_encoders``.
"""

import importlib.util
import json
import logging
import os
import struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

NONE_FOUND = "(none found)"
MAX_HEADER_BYTES = 100 * 1024 * 1024
GGUF_NAME_HINTS = ("qwen", "llama", "joycaption")

NATIVE_CLIP_TYPES = {
    "QWEN3VL_4B": "flux3",
    "QWEN3VL_8B": "boogu",
    "QWEN3_4B": "lumina2",
    "QWEN3_8B": "flux2",
    "QWEN25_7B": "qwen_image",
}

# (path, mtime, size) -> detected TEModel name, or None when unreadable/undetected
_native_cache: Dict[Tuple[str, float, int], Optional[str]] = {}


@dataclass(frozen=True)
class ModelEntry:
    name: str
    kind: str
    path: Path
    vision: bool
    mmproj: Optional[Path]
    clip_type: Optional[str]


@lru_cache(maxsize=None)
def llama_available() -> bool:
    available = importlib.util.find_spec("llama_cpp") is not None
    if not available:
        logger.info("llama-cpp-python is not installed; GGUF models are not listed")
    return available


def _native_clip_type(detected: str) -> Optional[str]:
    if detected.startswith("QWEN35_"):
        return "moss_image"
    return NATIVE_CLIP_TYPES.get(detected)


def _native_vision(detected: str) -> bool:
    return detected.startswith(("QWEN35_", "QWEN3VL_")) or detected == "QWEN25_7B"


def _read_header(path: Path) -> dict:
    with open(path, "rb") as f:
        (length,) = struct.unpack("<Q", f.read(8))
        if length > MAX_HEADER_BYTES:
            raise ValueError(f"header length {length} is too large")
        header = json.loads(f.read(length))
    return {
        key: SimpleNamespace(shape=tuple(value["shape"]))
        for key, value in header.items()
        if key != "__metadata__"
    }


def _detect_native(path: Path) -> Optional[str]:
    stat = path.stat()
    key = (str(path), stat.st_mtime, stat.st_size)
    if key not in _native_cache:
        import comfy.sd

        try:
            detected = comfy.sd.detect_te_model(_read_header(path))
            _native_cache[key] = detected.name if detected is not None else None
        except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error) as e:
            logger.warning("Skipping unreadable text encoder %s: %s", path, e)
            _native_cache[key] = None
    return _native_cache[key]


def _walk(root: str, suffix: str):
    for folder, _, files in os.walk(root, followlinks=True):
        for file in sorted(files):
            if file.lower().endswith(suffix):
                path = Path(folder) / file
                yield path, path.relative_to(root).as_posix()


def _native_entries(roots: List[str]) -> List[ModelEntry]:
    entries = []
    for root in roots:
        for path, relative in _walk(root, ".safetensors"):
            detected = _detect_native(path)
            if detected is None or _native_clip_type(detected) is None:
                continue
            entries.append(
                ModelEntry(
                    name=f"native: {relative}",
                    kind="native",
                    path=path,
                    vision=_native_vision(detected),
                    mmproj=None,
                    clip_type=_native_clip_type(detected),
                )
            )
    return entries


def _gguf_entries(roots: List[str]) -> List[ModelEntry]:
    entries = []
    for root in roots:
        for path, relative in _walk(root, ".gguf"):
            lower = path.name.lower()
            if "mmproj" in lower or not any(hint in lower for hint in GGUF_NAME_HINTS):
                continue
            mmproj = next(
                (p for p in sorted(path.parent.glob("*.gguf")) if "mmproj" in p.name.lower()),
                None,
            )
            entries.append(
                ModelEntry(
                    name=f"gguf: {relative}",
                    kind="gguf",
                    path=path,
                    vision=mmproj is not None,
                    mmproj=mmproj,
                    clip_type=None,
                )
            )
    return entries


def list_models() -> List[ModelEntry]:
    import folder_paths

    text_encoder_roots = [
        root for root in folder_paths.get_folder_paths("text_encoders") if os.path.isdir(root)
    ]
    entries = _native_entries(text_encoder_roots)
    if llama_available():
        llm_root = os.path.join(folder_paths.models_dir, "LLM")
        gguf_roots = [llm_root] if os.path.isdir(llm_root) else []
        entries += _gguf_entries(gguf_roots + text_encoder_roots)
    unique = {}
    for entry in entries:
        unique.setdefault(entry.name, entry)
    return sorted(unique.values(), key=lambda entry: entry.name)


def model_names() -> List[str]:
    return [entry.name for entry in list_models()] or [NONE_FOUND]


def find_model(name: str) -> Optional[ModelEntry]:
    return next((entry for entry in list_models() if entry.name == name), None)
