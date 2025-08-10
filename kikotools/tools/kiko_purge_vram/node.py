import time
from typing import Any, Dict, Tuple

try:
    from ...base.base_node import ComfyAssetsBaseNode as BaseNode
    from ...base.any_type import AnyType
except ImportError:
    # Fallback for testing environment
    from kikotools.base.base_node import ComfyAssetsBaseNode as BaseNode
    from kikotools.base.any_type import AnyType
from .logic import get_memory_stats, purge_memory, format_memory_report, should_purge

any_type = AnyType("*")


class KikoPurgeVRAM(BaseNode):
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "anything": (any_type, {}),
                "mode": (
                    ["soft", "aggressive", "models_only", "cache_only"],
                    {
                        "default": "soft",
                        "tooltip": "Purge mode: soft (basic), aggressive (thorough), models_only (unload models), cache_only (clear cache)",
                    },
                ),
                "report_memory": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Generate detailed memory usage report",
                    },
                ),
            },
            "optional": {
                "memory_threshold_mb": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 48000,
                        "step": 100,
                        "tooltip": "Only purge if memory usage exceeds this threshold (0 = always purge)",
                    },
                ),
            },
        }

    RETURN_TYPES = (any_type, "STRING")
    RETURN_NAMES = ("passthrough", "memory_report")
    FUNCTION = "purge_vram"
    CATEGORY = "🫶 ComfyAssets/🛠️ Utils"
    OUTPUT_NODE = True
    DESCRIPTION = "Purge VRAM to free up GPU memory during workflow execution. Passes through any input unchanged."

    def purge_vram(
        self,
        anything: Any,
        mode: str,
        report_memory: bool,
        memory_threshold_mb: int = 0,
    ) -> Tuple[Any, str]:
        # Check if we should purge based on threshold
        should_run, threshold_msg = should_purge(memory_threshold_mb)

        if not should_run:
            if report_memory:
                return anything, f"Memory purge skipped: {threshold_msg}"
            else:
                return anything, ""

        # Get before stats
        before_stats = get_memory_stats() if report_memory else None
        start_time = time.time()

        # Determine if we should unload models
        unload_models = mode in ["models_only", "aggressive"]

        # Perform memory purge
        purge_memory(mode=mode, unload_models=unload_models)

        # Calculate elapsed time
        elapsed_ms = (time.time() - start_time) * 1000

        # Generate report if requested
        if report_memory:
            after_stats = get_memory_stats()
            report = format_memory_report(before_stats, after_stats, mode, elapsed_ms)
            if threshold_msg and memory_threshold_mb > 0:
                report = f"{threshold_msg}\n\n{report}"
        else:
            report = ""

        # Pass through the input unchanged
        return anything, report


NODE_CLASS_MAPPINGS = {"KikoPurgeVRAM": KikoPurgeVRAM}

NODE_DISPLAY_NAME_MAPPINGS = {"KikoPurgeVRAM": "Kiko Purge VRAM"}
