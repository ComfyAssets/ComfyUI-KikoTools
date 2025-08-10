import gc
from typing import Dict, Tuple

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import comfy.model_management as mm

    COMFY_AVAILABLE = True
except ImportError:
    COMFY_AVAILABLE = False


def get_memory_stats() -> Dict[str, float]:
    stats = {
        "cuda_available": False,
        "free_mb": 0,
        "total_mb": 0,
        "used_mb": 0,
        "used_percent": 0,
    }

    if TORCH_AVAILABLE and torch.cuda.is_available():
        stats["cuda_available"] = True
        free, total = torch.cuda.mem_get_info()
        free_mb = free / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        used_mb = total_mb - free_mb

        stats["free_mb"] = free_mb
        stats["total_mb"] = total_mb
        stats["used_mb"] = used_mb
        stats["used_percent"] = (used_mb / total_mb) * 100 if total_mb > 0 else 0

    return stats


def purge_memory(mode: str = "soft", unload_models: bool = False) -> float:
    before_stats = get_memory_stats()

    if mode == "soft":
        # Basic garbage collection and cache clearing
        gc.collect()
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()

    elif mode == "aggressive":
        # Multiple passes of garbage collection with full cache clearing
        gc.collect()
        gc.collect()
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    elif mode == "models_only":
        # Only unload models
        if COMFY_AVAILABLE:
            mm.unload_all_models()
            mm.soft_empty_cache()
        gc.collect()

    elif mode == "cache_only":
        # Only clear cache without garbage collection
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()

    # Handle model unloading for non-model-specific modes
    if unload_models and mode not in ["models_only"]:
        if COMFY_AVAILABLE:
            mm.unload_all_models()
            mm.soft_empty_cache()

    after_stats = get_memory_stats()
    freed_mb = before_stats["used_mb"] - after_stats["used_mb"]

    return max(0, freed_mb)


def format_memory_report(
    before: Dict[str, float], after: Dict[str, float], mode: str, elapsed_ms: float
) -> str:
    if not before.get("cuda_available", True):
        return (
            "Memory Purge Report\n"
            "-------------------\n"
            "CUDA not available - CPU memory management only\n"
            f"Mode: {mode}\n"
            f"Time: {elapsed_ms:.1f}ms"
        )

    freed_mb = before["used_mb"] - after["used_mb"]

    report = [
        "Memory Purge Report",
        "-------------------",
        f"Mode: {mode}",
        f"Memory Freed: {freed_mb:.1f} MB",
        f"Before: {before['used_mb']:.1f} MB used ({before['used_percent']:.1f}%)",
        f"After: {after['used_mb']:.1f} MB used ({after['used_percent']:.1f}%)",
        f"Time: {elapsed_ms:.1f}ms",
    ]

    return "\n".join(report)


def should_purge(threshold_mb: int) -> Tuple[bool, str]:
    if threshold_mb <= 0:
        return True, ""

    stats = get_memory_stats()

    if not stats["cuda_available"]:
        return True, "CUDA not available, proceeding with CPU memory management"

    if stats["used_mb"] >= threshold_mb:
        return (
            True,
            f"Memory usage ({stats['used_mb']:.1f} MB) exceeds threshold ({threshold_mb} MB)",
        )
    else:
        return (
            False,
            f"Memory usage ({stats['used_mb']:.1f} MB) below threshold ({threshold_mb} MB)",
        )
