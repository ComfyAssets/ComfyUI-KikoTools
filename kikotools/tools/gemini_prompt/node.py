"""Gemini Prompt Engineer node implementation."""

import torch

from ...base import ComfyAssetsBaseNode

from .logic import analyze_image_with_gemini, validate_prompt_type, refresh_gemini_models
from .prompts import PROMPT_OPTIONS, GEMINI_MODELS, load_models_from_cache


class GeminiPromptNode(ComfyAssetsBaseNode):
    """Analyzes images using Gemini AI to generate optimized prompts for various AI models."""

    @classmethod
    def INPUT_TYPES(cls):
        """Define input types for the node."""
        # Load fresh model list from cache
        models, _ = load_models_from_cache()
        if not models:
            models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]
        
        # Find best default model
        default_model = "gemini-1.5-flash"
        if "gemini-2.0-flash" in models:
            default_model = "gemini-2.0-flash"
        elif "gemini-1.5-flash" in models:
            default_model = "gemini-1.5-flash"
        elif models:
            default_model = models[0]
            
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
                "refresh_models": ("BOOLEAN", {"default": False, "label_on": "Refresh", "label_off": "Skip"}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "negative_prompt")
    FUNCTION = "generate_prompt"
    CATEGORY = "ComfyAssets"

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

    def generate_prompt(self, image, prompt_type, model, api_key="", custom_prompt="", refresh_models=False):
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
            models, descriptions, error = refresh_gemini_models(api_key)
            if error:
                print(f"Failed to refresh models: {error}")
            else:
                print(f"Successfully refreshed model list: {len(models)} models found")
        # Validate prompt type
        if not validate_prompt_type(prompt_type):
            raise ValueError(f"Invalid prompt type: {prompt_type}")

        # Convert torch tensor to numpy if needed
        if isinstance(image, torch.Tensor):
            image_np = image.cpu().numpy()
        else:
            image_np = image

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
                if line.startswith("Positive:"):
                    positive_prompt = line.replace("Positive:", "").strip()
                elif line.startswith("Negative:"):
                    negative_prompt = line.replace("Negative:", "").strip()

            # If format not found, assume entire response is positive prompt
            if not positive_prompt:
                positive_prompt = prompt

            return (positive_prompt, negative_prompt)

        else:
            # Other formats don't use negative prompts
            return (prompt, "")


# Node display name
NODE_DISPLAY_NAME = "Gemini Prompt Engineer"
