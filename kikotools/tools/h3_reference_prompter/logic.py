"""Pure helpers for the H3 Reference Prompter."""

import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import torch

from ..prompt_enhancer.logic import clean_output, split_thinking

ROLES: Tuple[str, ...] = ("character", "outfit", "pose", "other")
DEFAULT_ROLES: Tuple[str, ...] = ("character", "outfit", "pose")
SLOTS = 3
# "auto" reads a slot's role from the draft; it is a choice, not a role.
AUTO = "auto"
ROLE_CHOICES: Tuple[str, ...] = (AUTO,) + ROLES

# KikoCharSheet's "<Picture N> is the character." sentences, English and Chinese.
_ROLE_SENTENCE = re.compile(
    r"<\s*Picture\s+(\d+)\s*>\s*(?:is\s+the\s+(character|outfit|pose)\s*\."
    r"|是\s*(人物|服装|姿势)\s*。)",
    re.IGNORECASE,
)
_ZH_ROLES = {"人物": "character", "服装": "outfit", "姿势": "pose"}

# Nude mode: the draft says nude or naked and no outfit picture is connected.
NUDE_MIN_AGE = 20
YOUTH_WORDS: Tuple[str, ...] = (
    "teen",
    "teenage",
    "teenager",
    "adolescent",
    "schoolgirl",
    "child",
    "childlike",
    "kid",
    "minor",
    "underage",
    "loli",
)
_NUDE = re.compile(r"\b(?:nude|naked)\b|裸", re.IGNORECASE)
_AGE_LINE = re.compile(
    r"estimated\s+age\s*:\s*(\d+)\s*(?:to|-|–)\s*(\d+)\s*years?", re.IGNORECASE
)


# Forms the plain words plus an "s" do not reach.
_EXTRA_YOUTH_FORMS = ("children", "teenaged")


def _word_pattern(words: Iterable[str]) -> "re.Pattern[str]":
    """Whole words in any case, each with an optional plural (teen, teens)."""
    names = "|".join(sorted(words, key=len, reverse=True))
    extra = "|".join(_EXTRA_YOUTH_FORMS)
    return re.compile(rf"\b(?:{extra}|(?:{names})s?)\b", re.IGNORECASE)


_YOUTH = _word_pattern(YOUTH_WORDS)
_YOUTH_OR_GIRL = _word_pattern(YOUTH_WORDS + ("girl",))
_REFUSAL = (
    f"Nude prompts need an adult character picture whose estimated age is "
    f"{NUDE_MIN_AGE} or older."
)

_TAG = re.compile(r"<\s*Picture\s+(\d+)\s*>")
_PREAMBLE_LINE = re.compile(
    r"^\s*(?:here (?:is|'s)\b[^\n]*:[ \t]*(?:\n|\Z)"
    r"|(?:(?:final|enhanced|revised) )?prompt[ \t]*:[ \t]*)",
    re.IGNORECASE,
)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
# Titles that do not end a sentence (Dr., Mr., Mrs., St., Prof. ...).
_TITLE_END = re.compile(r"(?:^|\s)(?:Dr|Mr|Mrs|Ms|Mx|St|Jr|Sr|Prof)\.$")
_SEED_MODULUS = 2**64


def find_tags(text: str) -> Set[int]:
    return {int(number) for number in _TAG.findall(text)}


def tag_problems(draft: str, result: str) -> Tuple[List[int], List[int]]:
    wanted = find_tags(draft)
    produced = find_tags(result)
    return sorted(wanted - produced), sorted(produced - wanted)


def _draft_roles(draft: str) -> Dict[int, str]:
    """Slot number to role for every picture sentence in the draft."""
    named: Dict[int, str] = {}
    for number, english, chinese in _ROLE_SENTENCE.findall(draft or ""):
        named[int(number)] = english.lower() if english else _ZH_ROLES[chinese]
    return named


def resolve_roles(draft: str, roles: Sequence[str]) -> Tuple[str, ...]:
    """Each slot's role: an explicit choice, else the draft's, else the default."""
    named = _draft_roles(draft)
    return tuple(
        role if role != AUTO else named.get(slot, DEFAULT_ROLES[slot - 1])
        for slot, role in enumerate(roles, start=1)
    )


def _sentences(line: str) -> List[str]:
    """Split one line at sentence ends, never right after a short title."""
    pieces: List[str] = []
    start = 0
    for match in _SENTENCE_BREAK.finditer(line):
        head = line[start : match.start()]
        if _TITLE_END.search(head):
            continue
        pieces.append(head)
        start = match.end()
    pieces.append(line[start:])
    return pieces


def draft_lead(draft: str) -> str:
    """The draft's sentences in their original order, word for word.

    Sentences end at ., ! or ? and at line breaks. Sentences that shared a
    line are joined by a space and lines by a line break. Fragments with no
    letter or digit (a stray lone period) and empty lines are dropped.
    """
    lines: List[str] = []
    for line in draft.strip().split("\n"):
        kept = [
            sentence.strip()
            for sentence in _sentences(line.strip())
            if re.search(r"\w", sentence)
        ]
        if kept:
            lines.append(" ".join(kept))
    return "\n".join(lines)


def pair_items(**columns: List[Any]) -> List[Dict[str, Any]]:
    lengths = {name: len(values) for name, values in columns.items()}
    sized = {length for length in lengths.values() if length > 1}
    if len(sized) > 1:
        described = ", ".join(f"{name} has {n}" for name, n in lengths.items())
        raise ValueError(f"input lists must share one length: {described}")
    count = sized.pop() if sized else 1
    items: List[Dict[str, Any]] = []
    for index in range(count):
        item: Dict[str, Any] = {}
        for name, values in columns.items():
            if not values:
                item[name] = None
            elif len(values) == 1:
                item[name] = values[0]
            else:
                item[name] = values[index]
        items.append(item)
    return items


def item_seed(seed: int, index: int) -> int:
    return (seed + index) % _SEED_MODULUS


def image_key(image: torch.Tensor, role: str, model: str, tokens: int) -> str:
    """Notes cache key: picture content, role, model and describe token limit."""
    contiguous = image.detach().to("cpu").contiguous()
    header = json.dumps([list(contiguous.shape), role, model, tokens])
    digest = hashlib.sha256(header.encode())
    digest.update(contiguous.reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def _squash(text: str) -> str:
    return " ".join(text.split()).lower()


def drop_repeats(text: str) -> str:
    """Drop lines and sentences that repeat earlier ones; the first stays."""
    seen_lines: Set[str] = set()
    out: List[str] = []
    for line in text.split("\n"):
        key = _squash(line)
        if not key:
            out.append(line)
            continue
        if key in seen_lines:
            continue
        seen_lines.add(key)
        sentences = _SENTENCE_BREAK.split(line)
        kept: List[str] = []
        seen_sentences: Set[str] = set()
        for sentence in sentences:
            sentence_key = _squash(sentence)
            if sentence_key not in seen_sentences:
                seen_sentences.add(sentence_key)
                kept.append(sentence)
        out.append(line if len(kept) == len(sentences) else " ".join(kept))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip("\n")


def _echo_key(sentence: str) -> str:
    return _squash(sentence).rstrip(".!?,;: ")


def drop_echoes(written: str, lead: str) -> str:
    """Drop sentences of ``written`` that repeat any sentence of ``lead``.

    Matching ignores case, spacing and end punctuation; lines left empty are
    removed.
    """
    echoes = {
        _echo_key(sentence)
        for line in lead.split("\n")
        for sentence in _sentences(line)
    } - {""}
    if not echoes:
        return written
    lines: List[str] = []
    for line in written.split("\n"):
        sentences = _sentences(line)
        kept = [s for s in sentences if _echo_key(s) not in echoes]
        if len(kept) == len(sentences):
            lines.append(line)
        elif kept:
            lines.append(" ".join(kept))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def clean_result(text: str) -> str:
    bare = split_thinking(text)
    bare = _PREAMBLE_LINE.sub("", bare, count=1)
    return drop_repeats(clean_output(bare))


def says_nude(draft: Optional[str]) -> bool:
    """The draft says nude, naked or 裸, whatever pictures are connected.

    This alone turns on the adult age check: the draft is copied into the
    prompt, so its nude wording reaches the image model either way.
    """
    return bool(_NUDE.search(draft or ""))


def is_nude(draft: Optional[str], connected_roles: Iterable[str]) -> bool:
    """The draft says nude and no connected picture is the outfit: the writer
    describes the unclothed body in place of an outfit."""
    return says_nude(draft) and "outfit" not in connected_roles


def parse_age_estimate(notes: Optional[str]) -> Optional[Tuple[int, int]]:
    """(low, high) from the last "Estimated age: N to M years." line, or None."""
    found = _AGE_LINE.findall(notes or "")
    if not found:
        return None
    low, high = sorted(int(number) for number in found[-1])
    return low, high


def find_youth_word(text: Optional[str], girl: bool = False) -> Optional[str]:
    """The first youth word in ``text``, lower case; "girl" only when asked."""
    match = (_YOUTH_OR_GIRL if girl else _YOUTH).search(text or "")
    return match.group(0).lower() if match else None


def _years(estimate: Tuple[int, int]) -> str:
    return f"{estimate[0]} to {estimate[1]} years"


def _check_character(slot: int, notes: str) -> Tuple[int, int]:
    estimate = parse_age_estimate(notes)
    if estimate is None:
        raise ValueError(
            f"{_REFUSAL} The describer gave no age estimate for image_{slot}."
        )
    word = find_youth_word(notes)
    if word is not None:
        raise ValueError(
            f"{_REFUSAL} The notes for image_{slot} use the word '{word}' "
            f"(estimate: {_years(estimate)})."
        )
    if estimate[0] < NUDE_MIN_AGE:
        raise ValueError(
            f"{_REFUSAL} The describer estimated {_years(estimate)} for image_{slot}."
        )
    return estimate


def check_adult(characters: List[Tuple[int, str]], draft: str) -> Tuple[int, int]:
    """Refuse a nude item unless every character picture reads as an adult.

    ``characters`` holds (slot, notes) for each connected character picture.
    Returns the (low, high) estimate spanning all of them.
    """
    word = find_youth_word(draft, girl=True)
    if word is not None:
        raise ValueError(f"{_REFUSAL} The draft uses the word '{word}'.")
    if not characters:
        raise ValueError(f"{_REFUSAL} No character picture is connected.")
    estimates = [_check_character(slot, notes) for slot, notes in characters]
    return min(low for low, _ in estimates), max(high for _, high in estimates)
