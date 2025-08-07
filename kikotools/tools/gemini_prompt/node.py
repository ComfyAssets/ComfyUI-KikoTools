"""Gemini Prompt Engineer node implementation."""

import torch

from ...base import ComfyAssetsBaseNode

from .logic import analyze_image_with_gemini, validate_prompt_type
from .prompts import PROMPT_OPTIONS, DEFAULT_GEMINI_MODELS
from .models import get_available_models


class GeminiPromptNode(ComfyAssetsBaseNode):
    """Analyzes images using Gemini AI to generate optimized prompts for various AI models."""

    @classmethod
    def INPUT_TYPES(cls):
        """Define input types for the node."""
        # Get available models dynamically (silent mode for initial load)
        models, _ = get_available_models(silent=True)

        # Use default if no models available
        if not models:
            models = DEFAULT_GEMINI_MODELS

        # Find best default model
        default_model = models[0] if models else "gemini-2.5-flash"

        return {
            "required": {
                "image": ("IMAGE",),
                "prompt_type": (PROMPT_OPTIONS, {"default": "flux"}),
                "model": (models, {"default": default_model}),
            },
            "optional": {
                "api_key": ("STRING", {"default": "", "multiline": False}),
                "custom_prompt": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": True,
                        "placeholder": "Optional: Enter custom system prompt instead of using templates",
                    },
                ),
                "refresh_models": (
                    "BOOLEAN",
                    {"default": False, "label_on": "Refresh", "label_off": "Skip"},
                ),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "negative_prompt")
    FUNCTION = "generate_prompt"
    CATEGORY = "ComfyAssets/🧠 Prompts"

    DESCRIPTION = """
Analyzes images using Google's Gemini AI to generate optimized prompts.

Supports multiple prompt formats:
- FLUX: Detailed artistic prompts with quality markers
- SDXL: Positive/negative prompt pairs with weight emphasis
- Danbooru: Anime-style booru tags with underscores
- Video: Motion and temporal descriptions for video generation

Requires Gemini API key (set GEMINI_API_KEY env var or provide in node).
Install: pip install google-generativeai
"""

    def generate_prompt(
        self,
        image,
        prompt_type,
        model,
        api_key="",
        custom_prompt="",
        refresh_models=False,
    ):
        """Generate prompt from image using Gemini.

        Args:
            image: Input image tensor
            prompt_type: Type of prompt to generate
            model: Gemini model to use
            api_key: Optional API key
            custom_prompt: Optional custom system prompt
            refresh_models: Whether to refresh the model list

        Returns:
            Tuple of (prompt, negative_prompt)
        """
        # Refresh models if requested
        if refresh_models and api_key:
            try:
                from .models import clear_cache

                # Clear cache to force refresh on next node creation
                clear_cache()
                print(
                    "Model cache cleared. Please recreate the node to see updated models."
                )
            except Exception as e:
                print(f"Failed to clear model cache: {e}")

        # Validate prompt type
        if not validate_prompt_type(prompt_type):
            raise ValueError(f"Invalid prompt type: {prompt_type}")

        # Convert torch tensor to numpy if needed
        if isinstance(image, torch.Tensor):
            image_np = image.cpu().numpy()
        else:
            image_np = image

        # If API key is provided, try to refresh model list in background
        if api_key:
            try:
                from .models import get_available_models

                # Try to get fresh models with the provided API key
                fresh_models, _ = get_available_models(api_key=api_key, silent=True)
                if fresh_models and fresh_models != DEFAULT_GEMINI_MODELS:
                    # Models were successfully fetched with this API key
                    pass
            except Exception:
                pass

        # Analyze image with Gemini
        prompt, error = analyze_image_with_gemini(
            image_np,
            prompt_type,
            api_key=api_key or None,
            custom_prompt=custom_prompt or None,
            model_name=model,
        )

        if error:
            # Return error as prompt for visibility
            return (f"Error: {error}", "")

        # Handle different prompt types
        if prompt_type == "sdxl":
            # SDXL returns positive and negative prompts
            lines = prompt.split("\n")
            positive_prompt = ""
            negative_prompt = ""

            for line in lines:
                if line.lower().startswith("positive:"):
                    positive_prompt = (
                        line.replace("Positive:", "").replace("positive:", "").strip()
                    )
                elif line.lower().startswith("negative:"):
                    negative_prompt = (
                        line.replace("Negative:", "").replace("negative:", "").strip()
                    )

            # If format not found, assume entire response is positive prompt
            if not positive_prompt:
                positive_prompt = prompt

            return (positive_prompt, negative_prompt)

        else:
            # Other formats don't use negative prompts
            return (prompt, "")


# Node display name
NODE_DISPLAY_NAME = "Gemini Prompt Engineer"
