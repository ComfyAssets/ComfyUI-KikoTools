"""H3 Reference Prompter node: two local passes turn a short draft plus up to
three reference pictures into one long MiniMax H3 Image prompt."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from ...base.base_node import ComfyAssetsBaseNode
from ..kiko_purge_vram.logic import repair_loaded_models, unload_models_safely
from ..prompt_enhancer.gguf_backend import free_gguf, generate_gguf
from ..prompt_enhancer.models import ModelEntry
from ..prompt_enhancer.native_backend import generate_native, load_native
from .hf_backend import Request, free_hf, generate_hf, generate_hf_batch
from .instructions import (
    AgeRange,
    describe_system,
    describe_user,
    retry_user,
    writer_system,
    writer_user,
)
from .logic import (
    AUTO,
    ROLE_CHOICES,
    SLOTS,
    check_adult,
    clean_result,
    draft_lead,
    drop_echoes,
    find_youth_word,
    image_key,
    is_nude,
    item_seed,
    pair_items,
    resolve_roles,
    tag_problems,
)
from .models import (
    default_prompter_model,
    find_prompter_model,
    prompter_model_names,
)

_SEED_MAX = 0xFFFFFFFFFFFFFFFF

logger = logging.getLogger(__name__)

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


def _generate_batch(
    entry: ModelEntry,
    requests: List[Request],
    seed: int,
    temperature: float,
    max_length: int,
) -> List[str]:
    return generate_hf_batch(entry, requests, seed, temperature, max_length)


def _resolve_model(name: str) -> ModelEntry:
    entry = find_prompter_model(name)
    if entry is None:
        raise ValueError(
            f"No prompt model named '{name}' was found. Searched models/LLM, "
            "models/text_encoders and the LLM GGUF folder; put a vision model "
            "there or pick another one. The model must be a vision model, and "
            "a GGUF also needs its mmproj file next to it."
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


def _check_something_to_write(
    prompts: List[str], images: Dict[str, Optional[List[Any]]]
) -> None:
    has_draft = any(text and text.strip() for text in prompts)
    has_image = any(
        image is not None for column in images.values() for image in column or []
    )
    if not has_draft and not has_image:
        raise ValueError(
            "nothing to write from: the draft is empty and no picture is connected"
        )


class _Run:
    """One execution: backend dispatch with a lazily loaded native clip.

    Seeds: one batched call samples with a single seed, so for hf entries
    every item in a batch uses the base seed and runs still repeat exactly.
    The gguf and native loops keep per-item seeds (base seed plus index).
    """

    def __init__(self, entry: ModelEntry, temperature: float) -> None:
        self.entry = entry
        self.temperature = temperature
        self.clip: Any = None

    @property
    def batched(self) -> bool:
        return self.entry.kind == "hf"

    def generate_batch(
        self, requests: List[Request], seed: int, max_length: int
    ) -> List[str]:
        return _generate_batch(self.entry, requests, seed, self.temperature, max_length)

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


Pending = Tuple[int, str, Any, str]  # (slot, role, image, draft)
Note = Tuple[int, str, Optional[str]]  # (slot, role, notes or None)
Item = Dict[str, Any]  # one prompt, its image_1..image_3 and resolved roles
Roles = Tuple[str, str, str]
Settings = Tuple[str, int, int, int]  # (model, seed, describe_max, write_max)


def _with_roles(items: List[Item], roles: Roles) -> List[Item]:
    """Each item with its own roles, read from its draft where a role is auto."""
    return [
        {**item, "roles": resolve_roles(item["prompt"] or "", roles)} for item in items
    ]


def _pending_pictures(items: List[Item], model: str, tokens: int) -> Dict[str, Pending]:
    """Uncached pictures across all items, keyed by image_key; first item wins."""
    pending: Dict[str, Pending] = {}
    for item in items:
        for slot, role in enumerate(item["roles"], start=1):
            image = item.get(f"image_{slot}")
            if image is None:
                continue
            key = image_key(image, role, model, tokens)
            if key not in _NOTES_CACHE and key not in pending:
                pending[key] = (slot, role, image, item["prompt"])
    return pending


def _describe_all(
    run: _Run, items: List[Item], model: str, seed: int, tokens: int
) -> None:
    """Fill _NOTES_CACHE for every picture of every item."""
    pending = _pending_pictures(items, model, tokens)
    requests = [
        (describe_system(role), describe_user(role, draft), image)
        for slot, role, image, draft in pending.values()
    ]
    if run.batched:
        texts = run.generate_batch(requests, seed, tokens) if requests else []
    else:
        texts = [run.generate(*request, seed, tokens) for request in requests]
    for (key, (slot, role, _, _)), raw in zip(pending.items(), texts):
        text = clean_result(raw)
        if not text:
            raise ValueError(
                f"{model} returned no description for image_{slot} ({role}); "
                "try again or pick another model"
            )
        _NOTES_CACHE[key] = text


def _item_notes(item: Item, model: str, tokens: int) -> List[Note]:
    notes: List[Note] = []
    for slot, role in enumerate(item["roles"], start=1):
        image = item.get(f"image_{slot}")
        key = None if image is None else image_key(image, role, model, tokens)
        text = None if key is None else _NOTES_CACHE[key]
        notes.append((slot, role, text))
    return notes


def _notes_text(notes: List[Note]) -> str:
    return "\n\n".join(
        f"<Picture {slot}> ({role}): {text}"
        for slot, role, text in notes
        if text is not None
    )


def _adult_range(item: Item, notes: List[Note]) -> Optional[AgeRange]:
    """The checked age range of a nude item; None when the item is not nude.

    Raises ValueError when a nude item has no adult character picture.
    """
    connected = [role for _, role, text in notes if text is not None]
    if not is_nude(item["prompt"], connected):
        return None
    characters = [
        (slot, text)
        for slot, role, text in notes
        if role == "character" and text is not None
    ]
    return check_adult(characters, item["prompt"] or "")


# (missing tags, extra tags, blank written part, banned word) per written prompt
Problems = Tuple[List[int], List[int], bool, Optional[str]]


def _combine(lead: str, raw: str) -> Tuple[str, str]:
    """(written, combined): the cleaned model text, and the full prompt."""
    written = drop_echoes(clean_result(raw), lead)
    parts = [part for part in (lead, written) if part]
    return written, "\n\n".join(parts).rstrip()


def _problems(draft: str, written: str, combined: str, nude: bool) -> Problems:
    """Tag problems, a blank part and, in nude mode, a youth word or "girl"
    in the model's part (the draft lead is not checked here)."""
    missing, extra = tag_problems(draft, combined)
    banned = find_youth_word(written, girl=True) if nude else None
    return missing, extra, not written, banned


def _has_problem(problems: Problems) -> bool:
    missing, extra, blank, banned = problems
    return bool(missing or extra or blank or banned)


def _retry_message(message: str, written: str, problems: Problems) -> str:
    missing, extra, blank, banned = problems
    previous = f"\n\nYour previous prompt:\n{written}" if written else ""
    retry = retry_user((missing, extra), blank=blank, banned=banned)
    return f"{message}{previous}\n\n{retry}"


def _tag_error(missing: List[int], extra: List[int]) -> ValueError:
    parts = []
    if missing:
        parts.append("missing " + ", ".join(f"<Picture {n}>" for n in missing))
    if extra:
        parts.append("unexpected " + ", ".join(f"<Picture {n}>" for n in extra))
    return ValueError(
        "The prompt model did not keep the picture tags after a retry: "
        + "; ".join(parts)
    )


def _raise_if_failed(problems: Problems, model: str) -> None:
    missing, extra, blank, banned = problems
    if blank:
        raise ValueError(
            f"{model} wrote no prompt text after a retry (the reply was empty, "
            "or cut off inside its thinking). Raise write_tokens or pick "
            "another model."
        )
    if banned:
        raise ValueError(
            f"{model} still used the word '{banned}' in a nude prompt after a "
            "retry; a nude prompt must describe an adult. No prompt was written."
        )
    if missing or extra:
        raise _tag_error(missing, extra)


def _write_one(
    run: _Run,
    draft: str,
    notes: List[Note],
    adult: Optional[AgeRange],
    seed: int,
    tokens: int,
) -> str:
    lead = draft_lead(draft)
    message = writer_user(lead, notes, adult)
    nude = adult is not None

    def attempt(text: str) -> Tuple[str, str]:
        return _combine(lead, run.generate(writer_system(), text, None, seed, tokens))

    written, combined = attempt(message)
    problems = _problems(draft, written, combined, nude)
    if not _has_problem(problems):
        return combined
    written, combined = attempt(_retry_message(message, written, problems))
    _raise_if_failed(_problems(draft, written, combined, nude), run.entry.name)
    return combined


def _write_batch(
    run: _Run,
    drafts: List[str],
    notes: List[List[Note]],
    adults: List[Optional[AgeRange]],
    seed: int,
    tokens: int,
) -> List[str]:
    """Write every draft in one batch, then retry the failing ones in one more."""
    leads = [draft_lead(draft) for draft in drafts]
    messages = [writer_user(*args) for args in zip(leads, notes, adults)]

    def attempt(indices: List[int], texts: List[str]) -> List[Tuple[str, str]]:
        raws = run.generate_batch(
            [(writer_system(), t, None) for t in texts], seed, tokens
        )
        return [_combine(leads[i], raw) for i, raw in zip(indices, raws)]

    def problems_of(index: int, result: Tuple[str, str]) -> Problems:
        return _problems(drafts[index], *result, adults[index] is not None)

    results = attempt(list(range(len(drafts))), messages)
    problems = [problems_of(i, result) for i, result in enumerate(results)]
    failing = [i for i, found in enumerate(problems) if _has_problem(found)]
    if not failing:
        return [combined for _, combined in results]
    retries = [_retry_message(messages[i], results[i][0], problems[i]) for i in failing]
    redone = dict(zip(failing, attempt(failing, retries)))
    for index in failing:
        _raise_if_failed(problems_of(index, redone[index]), run.entry.name)
    return [redone.get(i, result)[1] for i, result in enumerate(results)]


def _write_all(
    run: _Run,
    items: List[Item],
    notes: List[List[Note]],
    adults: List[Optional[AgeRange]],
    base_seed: int,
    tokens: int,
) -> List[str]:
    drafts = [item["prompt"] for item in items]
    if run.batched:
        return _write_batch(run, drafts, notes, adults, base_seed, tokens)
    return [
        _write_one(run, *args, item_seed(base_seed, index), tokens)
        for index, args in enumerate(zip(drafts, notes, adults))
    ]


def _run_items(
    run: _Run, items: List[Item], settings: Settings
) -> List[Tuple[str, str]]:
    """Describe every picture first, then write every prompt: (prompt, notes)."""
    model_name, base_seed, describe_max, write_max = settings
    _describe_all(run, items, model_name, base_seed, describe_max)
    notes = [_item_notes(item, model_name, describe_max) for item in items]
    # Every nude item passes the adult check before anything is written.
    adults = [_adult_range(item, n) for item, n in zip(items, notes)]
    written = _write_all(run, items, notes, adults, base_seed, write_max)
    return [(text, _notes_text(n)) for text, n in zip(written, notes)]


def _result(pairs: List[Tuple[str, str]]) -> Dict[str, Any]:
    prompts = [written for written, _ in pairs]
    notes_out = [notes_text for _, notes_text in pairs]
    return {
        "ui": {"h3_prompts": prompts, "h3_notes": notes_out},
        "result": (prompts, notes_out),
    }


def _free_other_backends(kind: str) -> None:
    """Free the slots of backends other than ``kind``, even with keep_loaded."""
    if kind != "hf":
        free_hf()
    if kind != "gguf":
        free_gguf()


def _execute(
    run: _Run, items: List[Item], settings: Settings, keep: bool
) -> List[Tuple[str, str]]:
    _free_other_backends(run.entry.kind)
    unloaded = False
    try:
        unload_models_safely()
        unloaded = True
        return _run_items(run, items, settings)
    except Exception:
        if unloaded:
            _repair_quietly()
        raise
    finally:
        if not keep:
            free_hf()
            free_gguf()
            run.clip = None


def _repair_quietly() -> None:
    try:
        repair_loaded_models()
    except Exception:
        logger.exception("repair_loaded_models failed after a prompter error")


def _optional_inputs() -> Dict[str, Any]:
    """Picture slots and the advanced tuning widgets."""
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
    optional["keep_loaded"] = (
        "BOOLEAN",
        {
            "default": False,
            "advanced": True,
            "tooltip": "Keep the prompt model loaded for the next run. A "
            "kept hf: model sits outside ComfyUI's memory management.",
        },
    )
    return optional


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
        for slot in range(1, SLOTS + 1):
            required[f"role_{slot}"] = (
                list(ROLE_CHOICES),
                {
                    "default": AUTO,
                    "tooltip": f"What image_{slot} shows; auto reads the draft's "
                    f"'<Picture {slot}> is the ...' sentence",
                },
            )
        required["seed"] = (
            "INT",
            {"default": 0, "min": 0, "max": _SEED_MAX, "control_after_generate": True},
        )
        return {"required": required, "optional": _optional_inputs()}

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "notes")
    OUTPUT_IS_LIST = (True, True)
    FUNCTION = "write"
    CATEGORY = "🫶 ComfyAssets/🧠 Prompts"

    @classmethod
    def VALIDATE_INPUTS(cls, model: Any) -> bool:
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
        image_1: Optional[List[Any]] = None,
        image_2: Optional[List[Any]] = None,
        image_3: Optional[List[Any]] = None,
        temperature: Optional[List[float]] = None,
        describe_tokens: Optional[List[int]] = None,
        write_tokens: Optional[List[int]] = None,
        keep_loaded: Optional[List[bool]] = None,
    ) -> Dict[str, Any]:
        if not prompt:
            raise ValueError("no prompt: connect or type a draft prompt")
        images = {"image_1": image_1, "image_2": image_2, "image_3": image_3}
        _check_something_to_write(prompt, images)
        model_name = model[0]
        keep = bool(keep_loaded[0]) if keep_loaded else False
        settings: Settings = (
            model_name,
            seed[0],
            describe_tokens[0] if describe_tokens else 512,
            write_tokens[0] if write_tokens else 1536,
        )
        items = pair_items(prompt=prompt, **{k: v or [] for k, v in images.items()})
        entry = _resolve_model(model_name)
        _check_batches(items)
        run = _Run(entry, temperature[0] if temperature else 0.7)
        roles: Roles = (role_1[0], role_2[0], role_3[0])
        pairs = _execute(run, _with_roles(items, roles), settings, keep)
        if entry.kind == "native" and not keep:
            # ComfyUI manages the native clip; dropping our reference frees nothing.
            unload_models_safely()
        return _result(pairs)
