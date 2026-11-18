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
    tokens_include_image,
)

UPDATE_COMFY = (
    "This encoder ignored the system prompt. Update ComfyUI (Sept 2026 or newer) "
    "or use a chat encoder such as Qwen3, Qwen3-VL or Qwen3.5"
)
NO_GENERATE = "This ComfyUI is too old for text generation. Update ComfyUI (Sept 2026 or newer)"
SYSTEM_CHECK_CHARS = 40


def _prompt_ids(tokens: Any) -> list:
    """All prompt token ids, read the way core TextGenerateV2 reads them."""
    if isinstance(tokens, dict):
        tokens = next(iter(tokens.values()), [])
    return [
        t[0]
        for chunk in tokens
        for t in chunk
        if isinstance(t, tuple) and isinstance(t[0], int)
    ]


class PromptEnhancerNode(ComfyAssetsBaseNode):
    """Rewrite a short prompt with the loaded text encoder and a per-model system prompt."""

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        names = prompt_names()
        return {
            "required": {
                "clip": (
                    "CLIP",
                    {"tooltip": "Chat text encoder, e.g. Qwen3, Qwen3-VL or Qwen3.5"},
                ),
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
                "trigger_words": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Comma-separated; added to the front of the result and removed from the prompt before the encoder sees it",
                    },
                ),
                "image": (
                    "IMAGE",
                    {"tooltip": "Needs a vision encoder such as Qwen3-VL or Qwen3.5"},
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
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "system_prompt")
    FUNCTION = "enhance"
    CATEGORY = "🫶 ComfyAssets/🧠 Prompts"

    @classmethod
    def IS_CHANGED(cls, base_model: str, **kwargs) -> str:
        return hashlib.sha256(load_prompt(base_model).path.read_bytes()).hexdigest()

    def enhance(
        self,
        clip,
        prompt: str,
        base_model: str,
        seed: int,
        trigger_words: str = "",
        image=None,
        temperature: float = 0.7,
        max_length: int = 1024,
        thinking: bool = False,
    ) -> Tuple[str, str]:
        if not prompt.strip() and image is None:
            raise ValueError("The prompt is empty; type an idea or attach an image")
        prompt = strip_triggers(prompt, trigger_words)
        if not prompt and image is None:
            raise ValueError(
                "the prompt only contains trigger words; describe the scene in the prompt"
            )
        library_prompt = load_prompt(base_model)
        system = library_prompt.text
        if image is not None and library_prompt.image_text:
            system += "\n\n" + library_prompt.image_text
        if not system.strip():
            raise ValueError(f"system prompt file '{base_model}' is empty")
        if not hasattr(clip, "generate"):
            raise ValueError(NO_GENERATE)

        tokens = clip.tokenize(
            prompt, image=image, thinking=thinking, system_prompt=system, min_length=1
        )
        if image is not None and not tokens_include_image(tokens):
            encoder = type(getattr(clip, "cond_stage_model", clip)).__name__
            raise ValueError(
                f"{encoder} did not take the image; load a vision encoder such as Qwen3-VL or Qwen3.5"
            )
        if system[:SYSTEM_CHECK_CHARS] not in clip.decode(_prompt_ids(tokens)):
            raise ValueError(UPDATE_COMFY)

        generated = clip.generate(
            tokens,
            do_sample=True,
            max_length=max_length,
            temperature=temperature,
            top_k=64,
            top_p=0.95,
            min_p=0.05,
            repetition_penalty=1.05,
            presence_penalty=0.0,
            seed=seed,
        )
        decoded = clip.decode(generated)
        if thinking and "</think>" not in decoded:
            raise ValueError(
                "thinking used up max_length; raise max_length or turn thinking off"
            )
        text = clean_output(split_thinking(decoded))
        max_words = library_prompt.max_words
        sentence = library_prompt.no_text_sentence
        if sentence and '"' not in text and max_words is not None:
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
