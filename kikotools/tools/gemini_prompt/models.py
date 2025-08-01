"""Dynamic model fetching and caching for Gemini API."""

import json
import os
import time
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Cache settings
CACHE_DURATION = 3600 * 24  # 24 hours in seconds
CACHE_FILE = os.path.join(os.path.dirname(__file__), ".gemini_models_cache.json")


def get_available_models(
    api_key: Optional[str] = None, silent: bool = False
) -> Tuple[List[str], Dict[str, str]]:
    """Fetch available Gemini models that support generateContent.

    Args:
        api_key: Optional API key. If not provided, will try to get from environment.
        silent: If True, suppress error logging (useful for initial load).

    Returns:
        Tuple of (model_names_list, model_descriptions_dict)
    """
    # Check cache first
    cached_data = _load_cache()
    if cached_data:
        return cached_data["models"], cached_data["descriptions"]

    # Try to fetch from API
    try:
        models, descriptions = _fetch_models_from_api(api_key, silent=silent)
        if models:
            _save_cache(models, descriptions)
            return models, descriptions
    except Exception as e:
        if not silent:
            logger.warning(f"Failed to fetch models from API: {e}")

    # Fall back to defaults
    from .prompts import DEFAULT_GEMINI_MODELS

    return DEFAULT_GEMINI_MODELS, {}


def _fetch_models_from_api(
    api_key: Optional[str] = None, silent: bool = False
) -> Tuple[List[str], Dict[str, str]]:
    """Fetch models from Gemini API.

    Args:
        api_key: Optional API key.
        silent: If True, suppress error logging.

    Returns:
        Tuple of (model_names_list, model_descriptions_dict)
    """
    try:
        import google.generativeai as genai
    except ImportError:
        if not silent:
            logger.error("google-generativeai not installed")
        return [], {}

    # Get API key
    if not api_key:
        from .logic import get_api_key

        api_key = get_api_key()

    if not api_key:
        if not silent:
            logger.debug("No API key available for fetching models")
        return [], {}

    try:
        genai.configure(api_key=api_key)

        models = []
        descriptions = {}

        # Fetch all models
        for model in genai.list_models():
            # Only include models that support generateContent
            if "generateContent" in model.supported_generation_methods:
                # Remove "models/" prefix from name
                model_name = model.name.replace("models/", "")
                models.append(model_name)
                descriptions[model_name] = model.display_name

        # Sort models by priority (newer versions first)
        models = _sort_models(models)

        return models, descriptions

    except Exception as e:
        if not silent:
            logger.error(f"Error fetching models from API: {e}")
        return [], {}


def _sort_models(models: List[str]) -> List[str]:
    """Sort models by version and capability.

    Prioritizes:
    1. Newer versions (2.5 > 2.0 > 1.5)
    2. Non-experimental models
    3. Flash models for general use
    """

    def sort_key(model: str):
        # Priority scoring
        score = 0

        # Version priority
        if "2.5" in model:
            score += 1000
        elif "2.0" in model:
            score += 800
        elif "1.5" in model:
            score += 600

        # Model type priority
        if "pro" in model and "preview" not in model and "exp" not in model:
            score += 100
        elif "flash" in model and "preview" not in model and "exp" not in model:
            score += 90

        # Penalize experimental/preview models
        if "exp" in model or "experimental" in model:
            score -= 50
        if "preview" in model:
            score -= 30

        # Penalize specific variants
        if "thinking" in model:
            score -= 100
        if "tts" in model:
            score -= 100
        if "lite" in model:
            score -= 20

        return -score  # Negative for descending sort

    return sorted(models, key=sort_key)


def _load_cache() -> Optional[Dict]:
    """Load cached model data if available and not expired."""
    if not os.path.exists(CACHE_FILE):
        return None

    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)

        # Check if cache is expired
        if time.time() - data.get("timestamp", 0) > CACHE_DURATION:
            return None

        return data
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return None


def _save_cache(models: List[str], descriptions: Dict[str, str]) -> None:
    """Save model data to cache."""
    try:
        data = {
            "models": models,
            "descriptions": descriptions,
            "timestamp": time.time(),
        }

        with open(CACHE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save cache: {e}")


def clear_cache() -> None:
    """Clear the model cache."""
    if os.path.exists(CACHE_FILE):
        try:
            os.remove(CACHE_FILE)
        except Exception as e:
            logger.warning(f"Failed to clear cache: {e}")
