"""Generate text with a GGUF model through llama-cpp-python (optional dependency)."""

import base64
import gc
import io
from typing import Any, Optional, Tuple

import numpy as np
import torch
from PIL import Image

from .models import ModelEntry

NO_LLAMA = "llama-cpp-python is not installed; install it to use GGUF models"
VISION_HANDLERS = ("Qwen3VLChatHandler", "Qwen25VLChatHandler", "MTMDChatHandler")

# ((path, mmproj or None), Llama) of the last model loaded; one slot only
_loaded: Optional[Tuple[Tuple[str, Optional[str]], Any]] = None


def _image_data_uri(image) -> str:
    frame = image[0].clamp(0, 1).mul(255).round().to(torch.uint8).cpu().numpy()
    buf = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(frame)).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _load(llama_cpp, entry: ModelEntry, use_image: bool, seed: int):
    global _loaded
    key = (str(entry.path), str(entry.mmproj) if use_image else None)
    if _loaded is not None and _loaded[0] == key:
        return _loaded[1]
    free_gguf()

    import comfy.model_management

    comfy.model_management.unload_all_models()
    comfy.model_management.soft_empty_cache()

    handler = None
    if use_image:
        from llama_cpp import llama_chat_format

        handler_cls = next(
            getattr(llama_chat_format, name)
            for name in VISION_HANDLERS
            if hasattr(llama_chat_format, name)
        )
        handler = handler_cls(clip_model_path=key[1], verbose=False)

    llm = llama_cpp.Llama(
        model_path=key[0],
        n_ctx=8192,
        n_gpu_layers=-1,
        flash_attn=torch.cuda.is_available(),
        seed=seed,
        verbose=False,
        chat_handler=handler,
    )
    _loaded = (key, llm)
    return llm


def generate_gguf(
    entry: ModelEntry,
    system: str,
    prompt: str,
    image,
    seed: int,
    temperature: float,
    max_length: int,
    thinking: bool,
    keep_loaded: bool,
) -> str:
    try:
        import llama_cpp
    except ImportError:
        raise ValueError(NO_LLAMA) from None

    text = prompt if thinking else prompt + "\n/no_think"
    user: Any = text
    if image is not None:
        user = [
            {"type": "image_url", "image_url": {"url": _image_data_uri(image)}},
            {"type": "text", "text": text},
        ]

    try:
        llm = _load(llama_cpp, entry, image is not None, seed)
        result = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            top_k=64,
            top_p=0.95,
            min_p=0.05,
            repeat_penalty=1.05,
            max_tokens=max_length,
            seed=seed,
        )
        return result["choices"][0]["message"]["content"]
    finally:
        if not keep_loaded:
            free_gguf()


def free_gguf() -> None:
    global _loaded
    if _loaded is None:
        return
    llm = _loaded[1]
    _loaded = None
    if hasattr(llm, "close"):
        llm.close()
    del llm
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
