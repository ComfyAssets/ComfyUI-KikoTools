"""Logic module for Text Encode Sampler Params node."""

from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)


def split_prompts(text: str) -> List[str]:
    """
    Split text into multiple prompts using separator patterns.

    Recognizes various separator patterns:
    - Three or more dashes: ---
    - Three or more asterisks: ***
    - Three or more equals: ===
    - Three or more tildes: ~~~

    Args:
        text: Multi-line text with separators

    Returns:
        List of individual prompt strings
    """
    try:
        normalized = re.sub(r"[-*=~]{3,}\n", "---\n", text)

        parts = normalized.split("---\n")

        prompts = []
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                prompts.append(cleaned)

        if not prompts and text.strip():
            prompts = [text.strip()]

        logger.info(f"Split text into {len(prompts)} prompts")
        return prompts

    except Exception as e:
        logger.error(f"Error splitting prompts: {e}")
        if text.strip():
            return [text.strip()]
        return []


def encode_prompts(prompts: List[str], clip_encoder) -> List[Any]:
    """
    Encode a list of prompts using CLIP encoder.

    Args:
        prompts: List of text prompts
        clip_encoder: CLIP encoder instance

    Returns:
        List of encoded conditioning tensors
    """
    encoded = []

    try:
        from nodes import CLIPTextEncode

        encoder = CLIPTextEncode()

        for i, prompt in enumerate(prompts):
            try:
                conditioning = encoder.encode(clip_encoder, prompt)[0]
                encoded.append(conditioning)
                logger.debug(f"Encoded prompt {i + 1}/{len(prompts)}")
            except Exception as e:
                logger.error(f"Failed to encode prompt {i + 1}: {e}")
                encoded.append(None)

        encoded = [e for e in encoded if e is not None]

        logger.info(f"Successfully encoded {len(encoded)}/{len(prompts)} prompts")

    except ImportError:
        logger.error("CLIPTextEncode not available, returning mock encodings")
        encoded = [{"mock": prompt} for prompt in prompts]
    except Exception as e:
        logger.error(f"Error encoding prompts: {e}")

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
