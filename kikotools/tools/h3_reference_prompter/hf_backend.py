"""Generate text with a Hugging Face model folder through transformers."""

import gc
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
from PIL import Image

from ..prompt_enhancer.models import ModelEntry

NO_TRANSFORMERS = "transformers is not installed; install transformers to use Hugging Face model folders"
SEED_MASK = 0xFFFFFFFF
REPETITION_PENALTY = 1.05
HF_BATCH_SIZE = 4

# (system, prompt, image) for one generation
Request = Tuple[str, str, Optional[torch.Tensor]]

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


def _tokenize(processor, conversations: List[List[Dict[str, Any]]]):
    """Tokenize a list of conversations, padded on the left for generation."""
    options: Dict[str, Any] = dict(
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        add_generation_prompt=True,
        # transformers 5 routes processor settings through processor_kwargs;
        # loose keywords the template does not use are dropped with a warning.
        processor_kwargs={"padding": True},
    )
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
    loaded: Tuple[Any, Any, torch.device],
    chunk: List[Request],
    seed: int,
    temperature: float,
    max_length: int,
) -> List[str]:
    processor, model, device = loaded
    conversations = [_conversation(*request) for request in chunk]
    inputs = _tokenize(processor, conversations).to(device=device, dtype=model.dtype)
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


def _chunks(requests: List[Request]) -> List[List[int]]:
    """Request indices grouped by image or no image, then cut to HF_BATCH_SIZE."""
    groups: Dict[bool, List[int]] = {}
    for index, (_, _, image) in enumerate(requests):
        groups.setdefault(image is not None, []).append(index)
    return [
        indices[start : start + HF_BATCH_SIZE]
        for indices in groups.values()
        for start in range(0, len(indices), HF_BATCH_SIZE)
    ]


def generate_hf_batch(
    entry: ModelEntry,
    requests: List[Request],
    seed: int,
    temperature: float,
    max_length: int,
) -> List[str]:
    """Generate one reply per (system, prompt, image) request, in request order.

    Every chunk samples from the same seed, so a run repeats exactly.
    """
    if not requests:
        return []
    try:
        import transformers
    except ImportError:
        raise ValueError(NO_TRANSFORMERS) from None

    loaded = _load(transformers, entry)
    results: Dict[int, str] = {}
    for indices in _chunks(requests):
        chunk = [requests[index] for index in indices]
        texts = _run_chunk(loaded, chunk, seed, temperature, max_length)
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
