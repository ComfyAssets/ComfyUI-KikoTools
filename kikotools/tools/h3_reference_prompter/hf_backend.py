"""Generate text with a Hugging Face model folder through transformers."""

import gc
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from PIL import Image

from ..prompt_enhancer.models import ModelEntry
from .models import read_architectures as _read_architectures

NO_TRANSFORMERS = "transformers is not installed; install transformers to use Hugging Face model folders"
SEED_MASK = 0xFFFFFFFF
REPETITION_PENALTY = 1.05
HF_BATCH_SIZE = 4
# Pictures are scaled down to at most this many pixels before description.
MAX_IMAGE_PIXELS = 1_048_576
# Batched generation is verified live only for these; others run one at a time.
BATCH_ARCHITECTURES = (
    "Qwen3VLForConditionalGeneration",
    "Qwen3_5ForConditionalGeneration",
)
# processor_kwargs (needed to pad a batch) exists from transformers 5 on.
BATCH_MIN_TRANSFORMERS = 5

# (system, prompt, image) for one generation
Request = Tuple[str, str, Optional[torch.Tensor]]
Loaded = Tuple[Any, Any, torch.device]  # (processor, model, device)

# (path, loaded, architectures) of the last model loaded; one slot only
_loaded: Optional[Tuple[str, Loaded, Tuple[str, ...]]] = None


def _to_pil(image: torch.Tensor) -> Image.Image:
    frame = image[0].clamp(0, 1).mul(255).round().to(torch.uint8).cpu().numpy()
    pil = Image.fromarray(np.ascontiguousarray(frame)).convert("RGB")
    width, height = pil.size
    if width * height <= MAX_IMAGE_PIXELS:
        return pil
    scale = math.sqrt(MAX_IMAGE_PIXELS / (width * height))
    size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return pil.resize(size, Image.Resampling.LANCZOS)


def _transformers_major(transformers) -> int:
    version = str(getattr(transformers, "__version__", ""))
    head = version.split(".", 1)[0]
    return int(head) if head.isdigit() else 0


def _batch_size(transformers, architectures: Tuple[str, ...]) -> int:
    if _transformers_major(transformers) < BATCH_MIN_TRANSFORMERS:
        return 1
    if not any(arch in BATCH_ARCHITECTURES for arch in architectures):
        return 1
    return HF_BATCH_SIZE


def _load(transformers, entry: ModelEntry) -> Tuple[Loaded, Tuple[str, ...]]:
    """(processor, model, device) and the folder's architectures; one slot."""
    global _loaded
    key = str(entry.path)
    if _loaded is not None and _loaded[0] == key:
        return _loaded[1], _loaded[2]
    free_hf()

    cuda = torch.cuda.is_available()
    device = torch.device("cuda" if cuda else "cpu")
    processor = transformers.AutoProcessor.from_pretrained(key, trust_remote_code=False)
    model = transformers.AutoModelForImageTextToText.from_pretrained(
        key,
        trust_remote_code=False,
        dtype=torch.bfloat16 if cuda else torch.float32,
    ).to(device)
    _loaded = (key, (processor, model, device), _read_architectures(entry.path))
    return _loaded[1], _loaded[2]


def _template_uses_thinking(processor) -> bool:
    """True when the template apply_chat_template will use mentions
    enable_thinking.

    That is the "default" entry of a template dict, or the template string.
    transformers hands an extra keyword to the template only when that
    template uses it; otherwise the keyword replaces processor_kwargs.
    """
    template = getattr(processor, "chat_template", None)
    if isinstance(template, dict):
        template = template.get("default")
    return isinstance(template, str) and "enable_thinking" in template


def _conversation(
    system: str, prompt: str, image: Optional[torch.Tensor]
) -> List[Dict[str, Any]]:
    user: List[Dict[str, Any]] = []
    if image is not None:
        user.append({"type": "image", "image": _to_pil(image)})
    user.append({"type": "text", "text": prompt})
    return [
        {"role": "system", "content": [{"type": "text", "text": system}]},
        {"role": "user", "content": user},
    ]


def _tokenize(processor, conversations: List[List[Dict[str, Any]]], padded: bool):
    """Tokenize a list of conversations, padded on the left for generation.

    Only named apply_chat_template arguments are passed: in transformers 5 any
    loose keyword the template does not use replaces processor_kwargs.
    """
    options: Dict[str, Any] = dict(
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
    )
    if padded:
        options["processor_kwargs"] = {"padding": True}
    if _template_uses_thinking(processor):
        options["enable_thinking"] = False
    tokenizer = processor.tokenizer
    side = tokenizer.padding_side
    tokenizer.padding_side = "left"
    try:
        return processor.apply_chat_template(conversations, **options)
    finally:
        tokenizer.padding_side = side


def _seed_all(seed: int) -> None:
    masked_seed = seed & SEED_MASK
    torch.manual_seed(masked_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(masked_seed)


def _run_chunk(
    loaded: Loaded,
    chunk: List[Request],
    seed: int,
    temperature: float,
    max_length: int,
    padded: bool,
) -> List[str]:
    processor, model, device = loaded
    conversations = [_conversation(*request) for request in chunk]
    inputs = _tokenize(processor, conversations, padded).to(
        device=device, dtype=model.dtype
    )
    _seed_all(seed)
    sampling: Dict[str, Any] = {"do_sample": temperature > 0}
    if temperature > 0:
        sampling["temperature"] = temperature
    with torch.inference_mode():
        output = model.generate(
            **inputs,
            max_new_tokens=max_length,
            repetition_penalty=REPETITION_PENALTY,
            **sampling,
        )
    # Left padding gives every row the same prompt length.
    new_tokens = output[:, inputs["input_ids"].shape[1] :]
    decoded = processor.batch_decode(new_tokens, skip_special_tokens=True)
    return [text.strip() for text in decoded]


def _chunks(requests: List[Request], size: int) -> List[List[int]]:
    """Request indices grouped by image or no image, then cut to ``size``."""
    groups: Dict[bool, List[int]] = {}
    for index, (_, _, image) in enumerate(requests):
        groups.setdefault(image is not None, []).append(index)
    return [
        indices[start : start + size]
        for indices in groups.values()
        for start in range(0, len(indices), size)
    ]


def generate_hf_batch(
    entry: ModelEntry,
    requests: List[Request],
    seed: int,
    temperature: float,
    max_length: int,
) -> List[str]:
    """Generate one reply per (system, prompt, image) request, in request order.

    Every chunk samples from the same seed, so a run repeats exactly. Only
    BATCH_ARCHITECTURES on transformers 5 or newer run more than one request
    per chunk.
    """
    if not requests:
        return []
    try:
        import transformers
    except ImportError:
        raise ValueError(NO_TRANSFORMERS) from None

    loaded, architectures = _load(transformers, entry)
    size = _batch_size(transformers, architectures)
    padded = _transformers_major(transformers) >= BATCH_MIN_TRANSFORMERS
    results: Dict[int, str] = {}
    for indices in _chunks(requests, size):
        chunk = [requests[index] for index in indices]
        texts = _run_chunk(loaded, chunk, seed, temperature, max_length, padded)
        results.update(zip(indices, texts))
    return [results[index] for index in range(len(requests))]


def generate_hf(
    entry: ModelEntry,
    system: str,
    prompt: str,
    image: Optional[torch.Tensor],
    seed: int,
    temperature: float,
    max_length: int,
) -> str:
    return generate_hf_batch(
        entry, [(system, prompt, image)], seed, temperature, max_length
    )[0]


def free_hf() -> None:
    global _loaded
    if _loaded is None:
        return
    _loaded = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
