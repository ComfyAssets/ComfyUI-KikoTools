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
VISION_HANDLERS = ("MTMDChatHandler", "Qwen25VLChatHandler")
NO_VISION_HANDLER = (
    "llama-cpp-python has no vision chat handler; update llama-cpp-python"
)
THINKING_TOO_LONG = "thinking used up max_length; raise max_length or turn thinking off"

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
            (
                getattr(llama_chat_format, name)
                for name in VISION_HANDLERS
                if hasattr(llama_chat_format, name)
            ),
            None,
        )
        if handler_cls is None:
            raise ValueError(NO_VISION_HANDLER)
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


def _text_handler(llm, entry: ModelEntry):
    """Render the GGUF's own chat template so enable_thinking reaches it."""
    from llama_cpp import llama_chat_format

    template = llm.metadata.get("tokenizer.chat_template")
    if not template:
        raise ValueError(f"{entry.name} has no chat template")

    def piece(token):
        return llm.detokenize([token], special=True).decode("utf-8", errors="ignore")

    return llama_chat_format.Jinja2ChatFormatter(
        template=template,
        eos_token=piece(llm.token_eos()),
        bos_token=piece(llm.token_bos()),
        stop_token_ids=[llm.token_eos()],
    ).to_chat_handler()


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

    user: Any = prompt
    if image is not None:
        user = [
            {"type": "image_url", "image_url": {"url": _image_data_uri(image)}},
            {"type": "text", "text": prompt},
        ]

    try:
        llm = _load(llama_cpp, entry, image is not None, seed)
        handler = llm.chat_handler or _text_handler(llm, entry)
        result = handler(
            llama=llm,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            enable_thinking=thinking,
            temperature=temperature,
            top_k=64,
            top_p=0.95,
            min_p=0.05,
            repeat_penalty=1.05,
            max_tokens=max_length,
            seed=seed,
        )
        choice = result["choices"][0]
        content = choice["message"]["content"]
        if (
            thinking
            and choice["finish_reason"] == "length"
            and "</think>" not in content
        ):
            raise ValueError(THINKING_TOO_LONG)
        return content
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
