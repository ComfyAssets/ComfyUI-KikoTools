"""Generate text with a Hugging Face model folder through transformers."""

import gc
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from PIL import Image

from kikotools.tools.prompt_enhancer.models import ModelEntry

NO_TRANSFORMERS = "transformers is not installed; install transformers to use Hugging Face model folders"
SEED_MASK = 0xFFFFFFFF

# (path, (processor, model, device)) of the last model loaded; one slot only
_loaded: Optional[Tuple[str, Tuple[Any, Any, torch.device]]] = None


def _to_pil(image: torch.Tensor) -> Image.Image:
    frame = image[0].clamp(0, 1).mul(255).round().to(torch.uint8).cpu().numpy()
    return Image.fromarray(np.ascontiguousarray(frame)).convert("RGB")


def _load(transformers, entry: ModelEntry) -> Tuple[Any, Any, torch.device]:
    global _loaded
    key = str(entry.path)
    if _loaded is not None and _loaded[0] == key:
        return _loaded[1]
    free_hf()

    cuda = torch.cuda.is_available()
    device = torch.device("cuda" if cuda else "cpu")
    processor = transformers.AutoProcessor.from_pretrained(key, trust_remote_code=False)
    model = transformers.AutoModelForImageTextToText.from_pretrained(
        key,
        trust_remote_code=False,
        dtype=torch.bfloat16 if cuda else torch.float32,
    ).to(device)
    _loaded = (key, (processor, model, device))
    return _loaded[1]


def _template_uses_thinking(processor) -> bool:
    """True when the chat template text mentions enable_thinking.

    transformers hands an extra keyword to the template only when the template
    uses it; otherwise the keyword goes to the processor with a warning.
    """
    template = getattr(processor, "chat_template", None)
    if isinstance(template, dict):
        texts = template.values()
    else:
        texts = [template]
    return any(isinstance(text, str) and "enable_thinking" in text for text in texts)


def _tokenize(processor, messages: List[Dict[str, Any]]):
    options: Dict[str, Any] = dict(
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
    )
    if _template_uses_thinking(processor):
        options["enable_thinking"] = False
    return processor.apply_chat_template(messages, **options)


def generate_hf(
    entry: ModelEntry,
    system: str,
    prompt: str,
    image: Optional[torch.Tensor],
    seed: int,
    temperature: float,
    max_length: int,
) -> str:
    try:
        import transformers
    except ImportError:
        raise ValueError(NO_TRANSFORMERS) from None

    user: List[Dict[str, Any]] = []
    if image is not None:
        user.append({"type": "image", "image": _to_pil(image)})
    user.append({"type": "text", "text": prompt})
    messages = [
        {"role": "system", "content": [{"type": "text", "text": system}]},
        {"role": "user", "content": user},
    ]

    processor, model, device = _load(transformers, entry)
    inputs = _tokenize(processor, messages).to(device=device, dtype=model.dtype)

    masked_seed = seed & SEED_MASK
    torch.manual_seed(masked_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(masked_seed)

    sampling: Dict[str, Any] = {"do_sample": temperature > 0}
    if temperature > 0:
        sampling["temperature"] = temperature
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=max_length, **sampling)

    new_tokens = output[:, inputs["input_ids"].shape[1] :]
    return processor.batch_decode(new_tokens, skip_special_tokens=True)[0].strip()


def free_hf() -> None:
    global _loaded
    if _loaded is None:
        return
    _loaded = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
