"""System prompt library for the Kiko Prompt Enhancer.

Each ``*.md`` file is one base model. Shipped files live next to this module;
``<user dir>/kikotools/system_prompts/`` may replace them by name or add more.
A file may start with ``---`` front matter (``max_words: <int>`` and ``no_text_sentence: <text>`` are read),
and a line ``## With an image`` splits the body into the text prompt and the
text used when an image is attached.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

SHIPPED_DIR = Path(__file__).parent / "system_prompts"
OVERRIDE_DIR = "kikotools"
OVERRIDE_SUBDIR = "system_prompts"
IMAGE_HEADING = "## With an image"
FRONT_MATTER_FENCE = "---"
DEFAULT_PROMPT = "krea2"


@dataclass(frozen=True)
class SystemPrompt:
    stem: str
    text: str
    image_text: str
    max_words: Optional[int]
    path: Path
    is_override: bool
    no_text_sentence: Optional[str] = None


def override_dir() -> Optional[Path]:
    """Return the override folder, or None when no user dir is known."""
    try:
        import folder_paths

        user_dir = folder_paths.get_user_directory()
        return Path(user_dir) / OVERRIDE_DIR / OVERRIDE_SUBDIR
    except Exception:  # ImportError, AttributeError, or a broken host
        return None


def _split_front_matter(raw: str):
    lines = raw.splitlines()
    if not lines or lines[0].strip() != FRONT_MATTER_FENCE:
        return [], raw
    for end in range(1, len(lines)):
        if lines[end].strip() == FRONT_MATTER_FENCE:
            return lines[1:end], "\n".join(lines[end + 1 :])
    return [], raw


def _read_max_words(header: List[str], path: Path) -> Optional[int]:
    max_words = None
    for line in header:
        key, _, value = line.partition(":")
        if key.strip() != "max_words":
            continue
        try:
            max_words = int(value.strip())
            if max_words < 1:
                raise ValueError
        except ValueError:
            logger.warning("%s: ignoring bad max_words value %r", path, value.strip())
            max_words = None
    return max_words


def _read_no_text_sentence(header: List[str]) -> Optional[str]:
    sentence = None
    for line in header:
        key, _, value = line.partition(":")
        if key.strip() == "no_text_sentence":
            sentence = value.strip() or None
    return sentence


def parse_prompt_file(
    stem: str, raw: str, path: Path, is_override: bool
) -> SystemPrompt:
    header, body = _split_front_matter(raw)
    text, found, image_text = [], False, []
    for line in body.splitlines():
        if line.strip() == IMAGE_HEADING:
            found = True
        else:
            (image_text if found else text).append(line)
    return SystemPrompt(
        stem=stem,
        text="\n".join(text).strip(),
        image_text="\n".join(image_text).strip(),
        max_words=_read_max_words(header, path),
        path=path,
        is_override=is_override,
        no_text_sentence=_read_no_text_sentence(header),
    )


def _read_dir(directory: Optional[Path], is_override: bool) -> Dict[str, SystemPrompt]:
    if directory is None or not directory.is_dir():
        return {}
    prompts = {}
    for path in sorted(directory.glob("*.md")):
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            logger.warning("Skipping system prompt %s: %s", path, error)
            continue
        prompts[path.stem] = parse_prompt_file(path.stem, raw, path, is_override)
    return prompts


def available_prompts() -> Dict[str, SystemPrompt]:
    return {**_read_dir(SHIPPED_DIR, False), **_read_dir(override_dir(), True)}


def prompt_names() -> List[str]:
    return sorted(available_prompts())


def default_prompt_name(names: List[str]) -> str:
    return DEFAULT_PROMPT if DEFAULT_PROMPT in names else sorted(names)[0]


def load_prompt(stem: str) -> SystemPrompt:
    prompts = available_prompts()
    if stem not in prompts:
        raise ValueError(f"Unknown base model '{stem}'")
    return prompts[stem]
