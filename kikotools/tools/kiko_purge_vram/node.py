import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from ...base.base_node import ComfyAssetsBaseNode as BaseNode
    from ...base.any_type import AnyType
except ImportError:
    # Fallback for testing environment
    from kikotools.base.base_node import ComfyAssetsBaseNode as BaseNode
    from kikotools.base.any_type import AnyType
from .logic import (
    MODES,
    memory_view,
    plan_steps,
    read_memory_mb,
    repair_loaded_models,
    resolve_mode,
    run_steps,
    should_skip,
)

logger = logging.getLogger(__name__)

any_type = AnyType("*")

CREDIT = "Behaviour based on Free VRAM Pixaroma from ComfyUI-Pixaroma by Pixaroma."
NO_INPUT_REPORT = "Nothing wired in: connect a value to 'anything' to purge."
MAX_THRESHOLD_MB = 262144


class KikoPurgeVRAM(BaseNode):
    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        return {
            "required": {
                "mode": (
                    list(MODES),
                    {
                        "default": "all",
                        "tooltip": (
                            "all: unload models, collect garbage, empty the cache. "
                            "models: unload models and collect garbage. "
                            "cache: only empty the GPU cache. "
                            "Garbage collection follows collect_garbage in every mode."
                        ),
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
                "anything": (any_type, {}),
                "memory_threshold_mb": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": MAX_THRESHOLD_MB,
                        "step": 100,
                        "tooltip": (
                            "Skip the purge when at least this many MB are already "
                            "free (0 = always purge)"
                        ),
                    },
                ),
                "collect_garbage": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": "Run Python garbage collection (in every mode, before the cache is emptied)",
                    },
                ),
                "every_run": (
                    "BOOLEAN",
                    {
                        "default": True,
                        "tooltip": (
                            "Run on every queue. Turn off to let ComfyUI cache the "
                            "node so nodes after it do not re-run."
                        ),
                    },
                ),
            },
        }

    RETURN_TYPES = (any_type, "STRING")
    RETURN_NAMES = ("passthrough", "memory_report")
    FUNCTION = "purge_vram"
    CATEGORY = "🫶 ComfyAssets/🛠️ Utils"
    OUTPUT_NODE = True
    DESCRIPTION = (
        "Frees GPU memory mid-workflow and passes the input through unchanged: "
        "'all' unloads models, collects garbage and empties the cache, 'models' "
        "skips the cache step, 'cache' only empties the cache. " + CREDIT
    )

    @classmethod
    def VALIDATE_INPUTS(cls, mode: Optional[str]) -> Union[bool, str]:
        """Naming only `mode` makes ComfyUI skip its dropdown check, so old
        mode names keep loading; unknown ones are rejected here."""
        if mode is None:  # linked input: ComfyUI passes None, run time resolves it
            return True
        try:
            resolve_mode(mode)
        except ValueError as error:
            return str(error)
        return True

    @classmethod
    def IS_CHANGED(cls, **kwargs: Any) -> Union[float, str]:
        if kwargs.get("every_run") is not False:
            return float("nan")
        return "|".join(
            str(kwargs.get(key))
            for key in ("mode", "memory_threshold_mb", "collect_garbage")
        )

    def purge_vram(
        self,
        mode: str,
        report_memory: bool,
        anything: Any = None,
        memory_threshold_mb: int = 0,
        collect_garbage: bool = True,
        every_run: bool = True,
    ) -> Tuple[Any, str]:
        if anything is None:
            return None, NO_INPUT_REPORT

        resolved, legacy = resolve_mode(mode)
        view = memory_view(resolved)
        before = read_memory_mb(view)

        if should_skip(memory_threshold_mb, before[0] if before else None):
            report = (
                f"Memory purge skipped: {before[0]:.1f} MB free is at or above "
                f"the {memory_threshold_mb} MB threshold"
            )
            return anything, report if report_memory else ""

        start = time.perf_counter()
        try:
            run_steps(plan_steps(resolved, collect_garbage))
        except Exception as exc:
            removed = repair_loaded_models()
            logger.exception("Kiko Purge VRAM: purge failed")
            raise RuntimeError(
                f"Kiko Purge VRAM could not free memory: {exc}. "
                f"ComfyUI's loaded-model list was repaired ({removed} "
                "half-unloaded entries removed) so later jobs keep working."
            ) from exc
        elapsed_ms = (time.perf_counter() - start) * 1000
        after = read_memory_mb(view)

        if not report_memory:
            return anything, ""
        return anything, self._report(
            resolved, legacy, memory_threshold_mb, before, after, elapsed_ms
        )

    @staticmethod
    def _report(
        mode: str,
        legacy: Optional[str],
        threshold_mb: int,
        before: Optional[Tuple[float, float]],
        after: Optional[Tuple[float, float]],
        elapsed_ms: float,
    ) -> str:
        lines: List[str] = []
        if threshold_mb > 0:
            lines.append(f"Threshold: {threshold_mb} MB")
        label = f"Mode: {mode}" + (f" (from legacy '{legacy}')" if legacy else "")
        lines.append(label)
        if before and after:
            freed = max(0.0, after[0] - before[0])
            lines.append(f"Memory Freed: {freed:.1f} MB")
            lines.append(f"Before: {before[0]:.1f} MB free of {before[1]:.1f} MB")
            lines.append(f"After: {after[0]:.1f} MB free of {after[1]:.1f} MB")
        else:
            lines.append("Memory figures unavailable")
        lines.append(f"Time: {elapsed_ms:.1f}ms")
        return "\n".join(lines)


NODE_CLASS_MAPPINGS = {"KikoPurgeVRAM": KikoPurgeVRAM}

NODE_DISPLAY_NAME_MAPPINGS = {"KikoPurgeVRAM": "Kiko Purge VRAM"}
