"""Pure helpers for the H3 Reference Prompter."""

import hashlib
import json
import re
from typing import Any, Dict, List, Sequence, Set, Tuple

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
