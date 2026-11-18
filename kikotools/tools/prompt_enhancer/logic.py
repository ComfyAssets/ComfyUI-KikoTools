"""Output helpers for the Kiko Prompt Enhancer."""

import re
from typing import Any, List, Optional

_PREAMBLE = re.compile(r"^(here is|here's|enhanced prompt|prompt)\b[^\n]*:\s*\n", re.IGNORECASE)
_WRAPPERS = (('"', '"'), ("'", "'"), ("```", "```"))
_SENTENCE_END = re.compile(r"[.!?][\"')\]]*(?=\s|$)")
_FENCE_LANGUAGE = re.compile(r"^[\w+-]+\n")


def split_thinking(generated: str) -> str:
    """Return the text after ``</think>``; an unclosed ``<think>`` block gives ""."""
    reasoning, sep, text = generated.partition("</think>")
    if not sep and not reasoning.lstrip().startswith("<think>"):
        text = generated
    return text.strip()


def clean_output(text: str) -> str:
    text = _PREAMBLE.sub("", text.strip(), count=1).strip()
    for start, end in _WRAPPERS:
        if len(text) >= 2 * len(start) and text.startswith(start) and text.endswith(end):
            inner = text[len(start):-len(end)]
            if start in inner:
                return text
            if start == "```":
                inner = _FENCE_LANGUAGE.sub("", inner, count=1)
            return inner.strip()
    return text


def cap_words(text: str, max_words: Optional[int]) -> str:
    if max_words is None:
        return text
    words = list(re.finditer(r"\S+", text))
    if len(words) <= max_words:
        return text
    capped = text[: words[max_words - 1].end()] if max_words > 0 else ""
    ends = list(_SENTENCE_END.finditer(capped))
    if ends:
        return capped[: ends[-1].end()]
    comma = capped.rfind(",")
    return capped[:comma].rstrip() if comma > 0 else capped


def _parse_triggers(trigger_words: str) -> List[str]:
    return [part.strip() for part in trigger_words.split(",") if part.strip()]


def strip_triggers(prompt: str, trigger_words: str) -> str:
    """Remove trigger words from the prompt so the LLM never reinterprets them."""
    triggers = _parse_triggers(trigger_words)
    if not triggers:
        return prompt
    for trigger in triggers:
        prompt = re.sub(r"(?<!\w)" + re.escape(trigger) + r"(?!\w)", "", prompt, flags=re.IGNORECASE)
    prompt = re.sub(r"[ \t]*,[ \t,]*", ", ", prompt)
    prompt = re.sub(r"[ \t]{2,}", " ", prompt)
    return prompt.strip(" \t\n,")


def prepend_triggers(text: str, trigger_words: str) -> str:
    triggers = _parse_triggers(trigger_words)
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
