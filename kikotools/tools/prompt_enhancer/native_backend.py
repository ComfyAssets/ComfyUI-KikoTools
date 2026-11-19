"""Generate text through a ComfyUI CLIP object (core text-generation path)."""

from typing import Any, Optional, Tuple

from .logic import tokens_include_image
from .models import ModelEntry

UPDATE_COMFY = (
    "This encoder ignored the system prompt. Update ComfyUI (Sept 2026 or newer) "
    "or use a chat encoder such as Qwen3, Qwen3-VL or Qwen3.5"
)
NO_GENERATE = (
    "This ComfyUI is too old for text generation. Update ComfyUI (Sept 2026 or newer)"
)
SYSTEM_CHECK_CHARS = 40

# (path, clip) of the last encoder loaded by load_native; ComfyUI manages its VRAM
_loaded: Optional[Tuple[str, Any]] = None


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


def generate_native(
    clip,
    system: str,
    prompt: str,
    image,
    seed: int,
    temperature: float,
    max_length: int,
    thinking: bool,
) -> str:
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
    return decoded


def load_native(entry: ModelEntry):
    global _loaded
    path = str(entry.path)
    if _loaded is not None and _loaded[0] == path:
        return _loaded[1]

    import comfy.sd
    import folder_paths

    clip = comfy.sd.load_clip(
        ckpt_paths=[path],
        embedding_directory=folder_paths.get_folder_paths("embeddings"),
        clip_type=getattr(comfy.sd.CLIPType, entry.clip_type.upper()),
    )
    _loaded = (path, clip)
    return clip
