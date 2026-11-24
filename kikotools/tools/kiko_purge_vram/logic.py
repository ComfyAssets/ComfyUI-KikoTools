import gc
from typing import Dict, Optional, Tuple

try:
    import comfy.model_management as mm

    COMFY_AVAILABLE = True
except ImportError:
    COMFY_AVAILABLE = False


MODES: Tuple[str, ...] = ("all", "models", "cache")

LEGACY_MODES: Dict[str, str] = {
    "soft": "all",
    "aggressive": "all",
    "models_only": "models",
    "cache_only": "cache",
}

_BYTES_PER_MB = 1024 * 1024


def resolve_mode(mode: str) -> Tuple[str, Optional[str]]:
    """Return (new_mode, legacy_name_or_None); reject anything unknown."""
    if mode in MODES:
        return mode, None
    if mode in LEGACY_MODES:
        return LEGACY_MODES[mode], mode
    raise ValueError(f"Unknown mode '{mode}'. Expected one of: {', '.join(MODES)}")


def plan_steps(mode: str, collect_garbage: bool) -> Dict[str, bool]:
    """Decide which purge steps run for an already-resolved mode."""
    return {
        "models": mode in ("all", "models"),
        "gc": collect_garbage,
        "cache": mode in ("all", "cache"),
    }


def memory_view(mode: str) -> str:
    """Cache purges are judged by the driver's view, the rest by ComfyUI's."""
    return "driver" if mode == "cache" else "comfy"


def read_memory_mb(view: str) -> Optional[Tuple[float, float]]:
    """Return (free_mb, total_mb), or None when memory cannot be read."""
    if not COMFY_AVAILABLE:
        return None
    try:
        device = mm.get_torch_device()
        if view == "driver" and getattr(device, "type", None) not in ("cpu", "mps"):
            free_total, free_torch = mm.get_free_memory(device, torch_free_too=True)
            free_bytes = free_total - free_torch
        else:
            free_bytes = mm.get_free_memory(device)
        total_bytes = mm.get_total_memory(device)
        return free_bytes / _BYTES_PER_MB, total_bytes / _BYTES_PER_MB
    except Exception:
        return None


def should_skip(threshold_mb: int, free_mb: Optional[float]) -> bool:
    """True when enough memory is already free, so the purge is not needed."""
    return threshold_mb > 0 and free_mb is not None and free_mb >= threshold_mb


def _contains(entries: list, entry: object) -> bool:
    """Identity membership; LoadedModel.__eq__ compares patchers, not entries."""
    return any(item is entry for item in entries)


def _remove(entries: list, entry: object) -> None:
    for index, item in enumerate(entries):
        if item is entry:
            del entries[index]
            return


def unload_models_safely() -> None:
    """Unload loaded models one at a time, tolerating the list shrinking.

    ComfyUI's unload_all_models() indexes into the live list and can raise
    IndexError when a finalizer removes entries mid-loop. Iterate a copy and
    re-check each entry against the live list instead. Then call
    unload_all_models() once, so hooks other packs wrap around it still run;
    the list is empty by then, so its stale-index loop has nothing to trip on.
    """
    loaded = getattr(mm, "current_loaded_models", None)
    if not isinstance(loaded, list):
        mm.unload_all_models()
        return
    unloaded_any = False
    for entry in list(loaded):
        if not _contains(loaded, entry):
            continue
        if entry.real_model is None or entry.model is None:
            _remove(loaded, entry)
            continue
        entry.model_unload()
        unloaded_any = True
        _remove(loaded, entry)
    mm.unload_all_models()
    if unloaded_any:
        mm.soft_empty_cache()


def is_out_of_memory(exc: BaseException) -> bool:
    """True when ComfyUI's own is_oom() recognises the error."""
    checker = getattr(mm, "is_oom", None)
    if not COMFY_AVAILABLE or not callable(checker):
        return False
    try:
        return bool(checker(exc))
    except Exception:
        return False


def repair_loaded_models() -> int:
    """Drop half-unloaded entries (real_model None); return how many."""
    loaded = getattr(mm, "current_loaded_models", None)
    if not isinstance(loaded, list):
        return 0
    broken = [entry for entry in loaded if entry.real_model is None]
    for entry in broken:
        _remove(loaded, entry)
    return len(broken)


def run_steps(steps: Dict[str, bool]) -> None:
    """Run the enabled steps in order: unload models, collect, empty cache."""
    if COMFY_AVAILABLE and steps.get("models"):
        unload_models_safely()
    if steps.get("gc"):
        gc.collect()
    if COMFY_AVAILABLE and steps.get("cache"):
        mm.soft_empty_cache(True)
