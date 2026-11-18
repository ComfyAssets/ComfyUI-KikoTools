"""Kiko Prompt Enhancer node: rewrite a short prompt in a base model's style."""

import hashlib
from typing import Any, Dict, Tuple

from ...base.base_node import ComfyAssetsBaseNode
from .library import default_prompt_name, load_prompt, prompt_names
from .logic import (
    append_no_text,
    cap_words,
    clean_output,
    prepend_triggers,
    split_thinking,
    strip_triggers,
)
from .gguf_backend import generate_gguf
from .models import NONE_FOUND, find_model, model_names
from .native_backend import generate_native, load_native

UNCENSORED_HINTS = ("uncensored", "abliterated", "heretic")


def default_model(names):
    uncensored = [
        name for name in names if any(hint in name.lower() for hint in UNCENSORED_HINTS)
    ]
    native = [name for name in uncensored if name.startswith("native:")]
    return (native or uncensored or names)[0]


def generate_with_model(
    model, system, prompt, image, seed, temperature, max_length, thinking, keep_loaded
):
    entry = find_model(model) if model != NONE_FOUND else None
    if entry is None:
        raise ValueError(
            f"No model named '{model}' and no clip connected; "
            "pick a model or connect an encoder"
        )
    if image is not None and not entry.vision:
        raise ValueError(
            f"{model} cannot read images; pick a vision model "
            "(one with an mmproj file, or a Qwen-VL / Qwen3.5 encoder)"
        )
    args = (system, prompt, image, seed, temperature, max_length, thinking)
    if entry.kind == "gguf":
        return generate_gguf(entry, *args, keep_loaded)
    return generate_native(load_native(entry), *args)


class PromptEnhancerNode(ComfyAssetsBaseNode):
    """Rewrite a short prompt with the loaded text encoder and a per-model system prompt."""

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        names = prompt_names()
        models = model_names()
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "tooltip": "Short idea to expand",
                    },
                ),
                "base_model": (
                    names,
                    {
                        "default": default_prompt_name(names),
                        "tooltip": "System prompt file to rewrite for",
                    },
                ),
                "model": (
                    models,
                    {
                        "default": default_model(models),
                        "tooltip": "Text encoder from models/text_encoders or GGUF from models/LLM",
                    },
                ),
                "mode": (
                    ["text", "vision"],
                    {
                        "default": "text",
                        "tooltip": "vision describes the connected image; needs a vision model",
                    },
                ),
                "seed": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "control_after_generate": True,
                    },
                ),
            },
            "optional": {
                "clip": (
                    "CLIP",
                    {
                        "tooltip": "Overrides model; chat text encoder, e.g. Qwen3, Qwen3-VL or Qwen3.5"
                    },
                ),
                "trigger_words": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Comma-separated; added to the front of the result and removed from the prompt before the encoder sees it",
                    },
                ),
                "image": (
                    "IMAGE",
                    {"tooltip": "Used in vision mode"},
                ),
                "temperature": (
                    "FLOAT",
                    {
                        "default": 0.7,
                        "min": 0.01,
                        "max": 2.0,
                        "step": 0.01,
                        "advanced": True,
                    },
                ),
                "max_length": (
                    "INT",
                    {"default": 1024, "min": 64, "max": 8192, "advanced": True},
                ),
                "thinking": ("BOOLEAN", {"default": False, "advanced": True}),
                "keep_loaded": ("BOOLEAN", {"default": False, "advanced": True}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "system_prompt")
    FUNCTION = "enhance"
    CATEGORY = "🫶 ComfyAssets/🧠 Prompts"

    @classmethod
    def VALIDATE_INPUTS(cls, model) -> bool:
        # A saved model missing on this machine is fine when a clip is connected;
        # enhance() raises if neither is usable.
        return True

    @classmethod
    def IS_CHANGED(cls, base_model: str, model: str, mode: str, **kwargs) -> str:
        digest = hashlib.sha256(load_prompt(base_model).path.read_bytes())
        digest.update(f"\0{model}\0{mode}".encode())
        return digest.hexdigest()

    def enhance(
        self,
        prompt: str,
        base_model: str,
        model: str,
        mode: str,
        seed: int,
        clip=None,
        trigger_words: str = "",
        image=None,
        temperature: float = 0.7,
        max_length: int = 1024,
        thinking: bool = False,
        keep_loaded: bool = False,
    ) -> Tuple[str, str]:
        image = image if mode == "vision" else None
        if not prompt.strip() and image is None:
            raise ValueError("The prompt is empty; type an idea or attach an image")
        prompt = strip_triggers(prompt, trigger_words)
        if not prompt and image is None:
            raise ValueError(
                "the prompt only contains trigger words; describe the scene in the prompt"
            )
        if mode == "vision" and image is None:
            raise ValueError(
                "vision mode needs an image; connect one to the image input"
            )
        library_prompt = load_prompt(base_model)
        system = library_prompt.text
        if image is not None and library_prompt.image_text:
            system += "\n\n" + library_prompt.image_text
        if not system.strip():
            raise ValueError(f"system prompt file '{base_model}' is empty")
        args = (system, prompt, image, seed, temperature, max_length, thinking)
        if clip is not None:
            decoded = generate_native(clip, *args)
        else:
            decoded = generate_with_model(model, *args, keep_loaded)
        text = clean_output(split_thinking(decoded))
        max_words = library_prompt.max_words
        sentence = library_prompt.no_text_sentence
        if sentence and max_words is not None:
            max_words -= len(sentence.split())
        final = prepend_triggers(
            append_no_text(cap_words(text, max_words), sentence), trigger_words
        )
        return final, system


# Setup API routes
try:
    import server

    from .routes import copy_route

    server.PromptServer.instance.routes.post("/kikotools/prompt_enhancer/copy")(
        copy_route
    )
except ImportError:
    # Server not available during testing
    pass
