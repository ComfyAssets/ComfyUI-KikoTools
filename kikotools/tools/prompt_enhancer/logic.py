"""Output helpers for the Kiko Prompt Enhancer."""

import re
from typing import Any, Optional

_PREAMBLE = re.compile(r"^(here is|here's|enhanced prompt|prompt)\b[^\n]*:\s*\n", re.IGNORECASE)
_WRAPPERS = (('"', '"'), ("'", "'"), ("```", "```"))
_SENTENCE_END = ".!?"


def split_thinking(generated: str) -> str:
    """Return the answer with any ``<think>`` block removed (mirrors core TextGenerateV2)."""
    reasoning, sep, text = generated.partition("</think>")
    if not sep and not reasoning.lstrip().startswith("<think>"):
        text = generated
    return text.strip()


def clean_output(text: str) -> str:
    text = _PREAMBLE.sub("", text.strip(), count=1).strip()
    for start, end in _WRAPPERS:
        if len(text) >= 2 * len(start) and text.startswith(start) and text.endswith(end):
            return text[len(start):-len(end)].strip()
    return text


def cap_words(text: str, max_words: Optional[int]) -> str:
    if max_words is None:
        return text
    words = list(re.finditer(r"\S+", text))
    if len(words) <= max_words:
        return text
    capped = text[: words[max_words - 1].end()] if max_words > 0 else ""
    last_end = max(capped.rfind(c) for c in _SENTENCE_END)
    return capped[: last_end + 1] if last_end >= 0 else capped


def prepend_triggers(text: str, trigger_words: str) -> str:
    triggers = [part.strip() for part in trigger_words.split(",") if part.strip()]
    if not triggers:
        return text
    return ", ".join(triggers + [text])


def tokens_include_image(tokens: Any) -> bool:
    if isinstance(tokens, dict):
        return any(tokens_include_image(value) for value in tokens.values())
    if isinstance(tokens, (list, tuple)):
        return any(
            (isinstance(item, tuple) and bool(item) and isinstance(item[0], dict) and item[0].get("type") == "image")
            or (not isinstance(item, tuple) and tokens_include_image(item))
            for item in tokens
        )
    return False
