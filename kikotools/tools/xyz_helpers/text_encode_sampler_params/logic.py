"""Logic module for Text Encode Sampler Params node."""

from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)


# A separator is a whole line of 3+ identical '-', '*', '=' or '~' characters.
_SEPARATOR_RE = re.compile(r"(?m)^[ \t]*([-*=~])\1{2,}[ \t]*\r?$")


def split_prompts(text: str) -> List[str]:
    """
    Split text into multiple prompts using separator lines.

    A separator is a line consisting only of three or more identical
    characters from ``-``, ``*``, ``=`` or ``~`` (surrounding spaces allowed).
    Separator-like text in the middle of a line does not split.

    Args:
        text: Multi-line text with separators

    Returns:
        List of non-empty, stripped prompt strings
    """
    prompts = [part.strip() for part in _SEPARATOR_RE.split(text)[0::2]]
    prompts = [p for p in prompts if p]
    logger.info(f"Split text into {len(prompts)} prompts")
    return prompts


def encode_prompts(prompts: List[str], clip_encoder) -> List[Any]:
    """
    Encode a list of prompts using CLIP encoder.

    Returns one conditioning per prompt, in order.

    Raises:
        ValueError: If any prompt fails to encode (so indices never misalign)
    """
    try:
        from nodes import CLIPTextEncode
    except ImportError:
        logger.error("CLIPTextEncode not available, returning mock encodings")
        return [{"mock": prompt} for prompt in prompts]

    encoder = CLIPTextEncode()
    encoded = []
    for i, prompt in enumerate(prompts):
        try:
            conditioning = encoder.encode(clip_encoder, prompt)[0]
        except Exception as e:
            raise ValueError(f"Failed to encode prompt {i + 1}: {e}") from e
        if conditioning is None:
            raise ValueError(f"Failed to encode prompt {i + 1}: encoder returned None")
        encoded.append(conditioning)
        logger.debug(f"Encoded prompt {i + 1}/{len(prompts)}")

    logger.info(f"Encoded {len(encoded)} prompts")
    return encoded


def create_sampler_params_conditioning(
    prompts: List[str], encoded: List[Any]
) -> Dict[str, Any]:
    """
    Create a conditioning dictionary for sampler params.

    Args:
        prompts: List of original text prompts
        encoded: List of encoded conditioning tensors

    Returns:
        Dictionary with text and encoded conditioning
    """
    return {"text": prompts, "encoded": encoded, "count": len(prompts)}


def validate_prompt_format(text: str) -> bool:
    """
    Validate that the prompt text is properly formatted.

    Args:
        text: Input text to validate

    Returns:
        True if format is valid
    """
    if not text or not text.strip():
        logger.warning("Empty prompt text")
        return False

    if len(text) > 10000:
        logger.warning(f"Prompt text too long: {len(text)} characters")
        return False

    return True


def get_prompt_statistics(prompts: List[str]) -> Dict[str, Any]:
    """
    Get statistics about the prompts.

    Args:
        prompts: List of prompts

    Returns:
        Dictionary with statistics
    """
    if not prompts:
        return {
            "count": 0,
            "total_chars": 0,
            "avg_chars": 0,
            "min_chars": 0,
            "max_chars": 0,
        }

    char_counts = [len(p) for p in prompts]

    return {
        "count": len(prompts),
        "total_chars": sum(char_counts),
        "avg_chars": sum(char_counts) // len(char_counts),
        "min_chars": min(char_counts),
        "max_chars": max(char_counts),
    }
