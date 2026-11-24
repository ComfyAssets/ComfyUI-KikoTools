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


def run_steps(steps: Dict[str, bool]) -> None:
    """Run the enabled steps in order: unload models, collect, empty cache."""
    if COMFY_AVAILABLE and steps.get("models"):
        mm.unload_all_models()
    if steps.get("gc"):
        gc.collect()
    if COMFY_AVAILABLE and steps.get("cache"):
        mm.soft_empty_cache(True)
