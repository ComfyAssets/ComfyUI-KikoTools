"""H3 Reference Prompter node: two local passes turn a short draft plus up to
three reference pictures into one long MiniMax H3 Image prompt."""

from typing import Any, Dict, List, Optional, Tuple

from ...base.base_node import ComfyAssetsBaseNode
from ..kiko_purge_vram.logic import repair_loaded_models, unload_models_safely
from ..prompt_enhancer.gguf_backend import free_gguf, generate_gguf
from ..prompt_enhancer.models import ModelEntry
from ..prompt_enhancer.native_backend import generate_native, load_native
from .hf_backend import free_hf, generate_hf
from .instructions import (
    describe_system,
    describe_user,
    retry_user,
    writer_system,
    writer_user,
)
from .logic import (
    DEFAULT_ROLES,
    ROLES,
    SLOTS,
    clean_result,
    image_key,
    item_seed,
    pair_items,
    tag_problems,
)
from .models import (
    default_prompter_model,
    find_prompter_model,
    prompter_model_names,
)

_SEED_MAX = 0xFFFFFFFFFFFFFFFF

# Pass-1 notes keyed by image_key; lives for the ComfyUI session.
_NOTES_CACHE: Dict[str, str] = {}


def _generate(
    entry: ModelEntry,
    clip: Any,
    system: str,
    prompt: str,
    image: Any,
    seed: int,
    temperature: float,
    max_length: int,
) -> str:
    if entry.kind == "hf":
        return generate_hf(entry, system, prompt, image, seed, temperature, max_length)
    if entry.kind == "gguf":
        return generate_gguf(
            entry, system, prompt, image, seed, temperature, max_length, False, True
        )
    return generate_native(
        clip, system, prompt, image, seed, temperature, max_length, False
    )


def _resolve_model(name: str) -> ModelEntry:
    entry = find_prompter_model(name)
    if entry is None:
        raise ValueError(
            f"No prompt model named '{name}' was found. Searched models/LLM, "
            "models/text_encoders and the LLM GGUF folder; put a vision model "
            "there or pick another one."
        )
    return entry


def _check_batches(items: List[Dict[str, Any]]) -> None:
    for item in items:
        for slot in range(1, SLOTS + 1):
            image = item.get(f"image_{slot}")
            if image is not None and image.shape[0] > 1:
                raise ValueError(
                    f"image_{slot} holds a batch of {image.shape[0]} images; "
                    "connect one image per slot, or use an image list"
                )


class _Run:
    """One execution: backend dispatch with a lazily loaded native clip."""

    def __init__(self, entry: ModelEntry, temperature: float) -> None:
        self.entry = entry
        self.temperature = temperature
        self.clip = None

    def generate(
        self, system: str, prompt: str, image: Any, seed: int, max_length: int
    ) -> str:
        if self.entry.kind == "native" and self.clip is None:
            self.clip = load_native(self.entry)
        try:
            return _generate(
                self.entry,
                self.clip,
                system,
                prompt,
                image,
                seed,
                self.temperature,
                max_length,
            )
        except Exception as error:
            if self.entry.kind != "gguf":
                raise
            raise ValueError(
                f"{self.entry.name} failed to run ({error}). GGUF vision "
                "through llama-cpp is not verified for this node; put a "
                "transformers model folder under models/LLM instead."
            ) from error


def _describe(run: _Run, item, role, slot, model, seed, tokens) -> Optional[str]:
    image = item.get(f"image_{slot}")
    if image is None:
        return None
    key = image_key(image, role, model)
    if key not in _NOTES_CACHE:
        _NOTES_CACHE[key] = run.generate(
            describe_system(role),
            describe_user(role, item["prompt"]),
            image,
            seed,
            tokens,
        ).strip()
    return _NOTES_CACHE[key]


def _write_one(run: _Run, draft: str, notes, seed: int, tokens: int) -> str:
    message = writer_user(draft, notes)
    result = clean_result(run.generate(writer_system(), message, None, seed, tokens))
    problems = tag_problems(draft, result)
    if not any(problems):
        return result
    retry = f"{message}\n\nYour previous prompt:\n{result}\n\n{retry_user(problems)}"
    result = clean_result(run.generate(writer_system(), retry, None, seed, tokens))
    missing, extra = tag_problems(draft, result)
    if missing or extra:
        parts = []
        if missing:
            parts.append("missing " + ", ".join(f"<Picture {n}>" for n in missing))
        if extra:
            parts.append("unexpected " + ", ".join(f"<Picture {n}>" for n in extra))
        raise ValueError(
            "The prompt model did not keep the picture tags after a retry: "
            + "; ".join(parts)
        )
    return result


class H3ReferencePrompterNode(ComfyAssetsBaseNode):
    """Write one MiniMax H3 Image prompt from a draft and reference pictures."""

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        names = prompter_model_names()
        required: Dict[str, Any] = {
            "prompt": (
                "STRING",
                {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Short draft; <Picture 1> to <Picture 3> tags are kept exactly",
                },
            ),
            "model": (
                names,
                {
                    "default": default_prompter_model(names),
                    "tooltip": "Vision model from models/LLM or models/text_encoders",
                },
            ),
        }
        for slot, role in enumerate(DEFAULT_ROLES, start=1):
            required[f"role_{slot}"] = (
                list(ROLES),
                {"default": role, "tooltip": f"What image_{slot} shows"},
            )
        required["seed"] = (
            "INT",
            {"default": 0, "min": 0, "max": _SEED_MAX, "control_after_generate": True},
        )
        optional: Dict[str, Any] = {
            f"image_{slot}": ("IMAGE", {"tooltip": f"Reference for <Picture {slot}>"})
            for slot in range(1, SLOTS + 1)
        }
        optional["temperature"] = (
            "FLOAT",
            {"default": 0.7, "min": 0.01, "max": 2.0, "step": 0.01, "advanced": True},
        )
        optional["describe_tokens"] = (
            "INT",
            {"default": 512, "min": 64, "max": 4096, "advanced": True},
        )
        optional["write_tokens"] = (
            "INT",
            {"default": 1536, "min": 256, "max": 8192, "advanced": True},
        )
        optional["keep_loaded"] = ("BOOLEAN", {"default": False, "advanced": True})
        return {"required": required, "optional": optional}

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "notes")
    OUTPUT_IS_LIST = (True, True)
    FUNCTION = "write"
    CATEGORY = "🫶 ComfyAssets/🧠 Prompts"

    @classmethod
    def VALIDATE_INPUTS(cls, model) -> bool:
        # A model missing on this machine must not block loading the workflow;
        # write() fails with a clear message instead.
        return True

    def write(
        self,
        prompt: List[str],
        model: List[str],
        role_1: List[str],
        role_2: List[str],
        role_3: List[str],
        seed: List[int],
        image_1=None,
        image_2=None,
        image_3=None,
        temperature: Optional[List[float]] = None,
        describe_tokens: Optional[List[int]] = None,
        write_tokens: Optional[List[int]] = None,
        keep_loaded: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        model_name = model[0]
        roles = (role_1[0], role_2[0], role_3[0])
        base_seed = seed[0]
        keep = bool(keep_loaded[0]) if keep_loaded else False
        describe_max = describe_tokens[0] if describe_tokens else 512
        write_max = write_tokens[0] if write_tokens else 1536
        items = pair_items(
            prompt=prompt,
            image_1=image_1 or [],
            image_2=image_2 or [],
            image_3=image_3 or [],
        )
        entry = _resolve_model(model_name)
        _check_batches(items)
        run = _Run(entry, temperature[0] if temperature else 0.7)
        unloaded = False
        try:
            unload_models_safely()
            unloaded = True
            prompts: List[str] = []
            notes_out: List[str] = []
            for index, item in enumerate(items):
                notes: List[Tuple[int, str, Optional[str]]] = []
                for slot, role in enumerate(roles, start=1):
                    text = _describe(
                        run, item, role, slot, model_name, base_seed, describe_max
                    )
                    notes.append((slot, role, text))
                prompts.append(
                    _write_one(
                        run,
                        item["prompt"],
                        notes,
                        item_seed(base_seed, index),
                        write_max,
                    )
                )
                notes_out.append(
                    "\n\n".join(
                        f"<Picture {slot}> ({role}): {text}"
                        for slot, role, text in notes
                        if text is not None
                    )
                )
        except Exception:
            if unloaded:
                repair_loaded_models()
            raise
        finally:
            if not keep:
                free_hf()
                free_gguf()
                run.clip = None
        return {
            "ui": {"h3_prompts": prompts, "h3_notes": notes_out},
            "result": (prompts, notes_out),
        }
