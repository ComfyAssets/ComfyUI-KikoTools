"""Model Recommended Settings node for ComfyUI."""

import fnmatch
import glob
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from ...base.base_node import ComfyAssetsBaseNode
from ..sampler_combo.logic import SAMPLERS, SCHEDULERS
from .logic import find_sidecar, map_sampler, resolve, sources_from_sidecar

logger = logging.getLogger(__name__)

OVERRIDES_FILE = os.path.join("kikotools", "model_settings.json")
LM_APP_NAME = "ComfyUI-LoRA-Manager"
MODEL_EXTENSIONS = (".safetensors", ".gguf", ".ckpt", ".pt", ".pth", ".sft")


def model_paths(model_name: str) -> List[str]:
    """Absolute paths the name may refer to, across the model folders.

    An absolute path (Checkpoint Folder Iterator allows folders outside the
    model roots) is only used when it is an existing model file, so the node
    never reads sidecars next to arbitrary paths.
    """
    if os.path.isabs(model_name):
        is_model = model_name.lower().endswith(MODEL_EXTENSIONS)
        return [model_name] if is_model and os.path.isfile(model_name) else []
    import folder_paths

    paths = []
    for key in ("diffusion_models", "checkpoints"):
        path = folder_paths.get_full_path(key, model_name)
        if path and path not in paths:
            paths.append(path)
    return paths


def lora_manager_sidecar_root() -> Optional[str]:
    """LoRA Manager's central sidecar folder, when it is set to centralized storage."""
    import folder_paths

    candidates = []
    for custom_nodes in folder_paths.get_folder_paths("custom_nodes"):
        candidates += glob.glob(os.path.join(custom_nodes, "*", "settings.json"))
    candidates = [
        c for c in candidates if "lora" in c.lower() and "manager" in c.lower()
    ]
    try:
        from platformdirs import user_config_dir

        candidates.append(
            os.path.join(user_config_dir(LM_APP_NAME, appauthor=False), "settings.json")
        )
    except ImportError:
        pass
    for path in candidates:
        try:
            with open(path, encoding="utf-8") as f:
                settings = json.load(f)
        except (OSError, ValueError):
            continue
        if settings.get("sidecar_storage_mode") == "centralized":
            return settings.get("sidecar_storage_path")
    return None


def overrides_path() -> Optional[str]:
    try:
        import folder_paths

        return os.path.join(folder_paths.get_user_directory(), OVERRIDES_FILE)
    except (ImportError, AttributeError):
        return None


def overrides_mtime() -> float:
    path = overrides_path()
    return os.path.getmtime(path) if path and os.path.exists(path) else 0.0


def load_overrides() -> dict:
    path = overrides_path()
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        logger.warning(f"Ignoring {path}: {e}")
        return {}
    return data if isinstance(data, dict) else {}


def model_override(overrides: dict, model_name: str) -> Dict[str, Any]:
    """Settings from overrides["models"] whose key (a name or glob) matches the model."""
    stem = os.path.splitext(os.path.basename(model_name))[0]
    for pattern, settings in (overrides.get("models") or {}).items():
        if fnmatch.fnmatch(stem, pattern) or fnmatch.fnmatch(model_name, pattern):
            found = dict(settings)
            if found.get("sampler"):
                found["sampler"], named = map_sampler(str(found["sampler"]))
                found.setdefault("scheduler", named)
            return found
    return {}


class ModelRecommendedSettingsNode(ComfyAssetsBaseNode):
    """
    Steps, CFG, sampler and scheduler recommended for a model.

    Reads the settings from the model's Civitai info that LoRA Manager (or
    Civitai Helper) stored: the most common values on the example images
    first, then settings written in the description. Nothing is downloaded.
    Wire model_name from Checkpoint Folder Iterator's ckpt_name and the
    outputs into KSampler, and every model in a sweep runs with its own
    settings. The widgets are used for anything not found, for fields whose
    use_model switch is off, and for samplers or schedulers that are not
    installed (unless user/kikotools/model_settings.json substitutes one).
    """

    @classmethod
    def INPUT_TYPES(cls):
        def use(field):
            return (
                "BOOLEAN",
                {
                    "default": True,
                    "tooltip": f"Use the model's recommended {field}; off = the widget value",
                },
            )

        return {
            "required": {
                "model_name": (
                    "STRING",
                    {
                        "forceInput": True,
                        "tooltip": "Model file name or path, e.g. Checkpoint Folder Iterator's ckpt_name",
                    },
                ),
                "steps": ("INT", {"default": 25, "min": 1, "max": 1000}),
                "cfg": (
                    "FLOAT",
                    {
                        "default": 3.0,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 0.1,
                        "round": 0.01,
                    },
                ),
                "sampler_name": (SAMPLERS, {"default": "euler"}),
                "scheduler": (SCHEDULERS, {"default": "simple"}),
                "use_model_steps": use("steps"),
                "use_model_cfg": use("CFG"),
                "use_model_sampler": use("sampler"),
                "use_model_scheduler": use("scheduler"),
            }
        }

    RETURN_TYPES = ("INT", "FLOAT", SAMPLERS, SCHEDULERS, "STRING")
    RETURN_NAMES = ("steps", "cfg", "sampler_name", "scheduler", "info")
    FUNCTION = "get_settings"
    CATEGORY = "🫶 ComfyAssets/🌀 Samplers"

    @classmethod
    def IS_CHANGED(cls, **_):
        return overrides_mtime()

    def get_settings(
        self,
        model_name: str,
        steps: int,
        cfg: float,
        sampler_name: str,
        scheduler: str,
        use_model_steps: bool = True,
        use_model_cfg: bool = True,
        use_model_sampler: bool = True,
        use_model_scheduler: bool = True,
    ) -> Tuple[int, float, str, str, str]:
        overrides = load_overrides()
        sources = [("override", model_override(overrides, model_name))]
        sidecar = find_sidecar(model_paths(model_name), lora_manager_sidecar_root())
        if sidecar is None:
            header = f"{model_name}: no Civitai info found"
        else:
            header = model_name
            sources += sources_from_sidecar(sidecar, SAMPLERS, SCHEDULERS)

        values, info = resolve(
            sources,
            {
                "steps": steps,
                "cfg": cfg,
                "sampler": sampler_name,
                "scheduler": scheduler,
            },
            {
                "steps": use_model_steps,
                "cfg": use_model_cfg,
                "sampler": use_model_sampler,
                "scheduler": use_model_scheduler,
            },
            SAMPLERS,
            SCHEDULERS,
            {k: overrides.get(k) or {} for k in ("samplers", "schedulers")},
        )
        info = f"{header}\n{info}"
        self.log_info(info.replace("\n", "; "))
        return (
            int(values["steps"]),
            float(values["cfg"]),
            values["sampler"],
            values["scheduler"],
            info,
        )
