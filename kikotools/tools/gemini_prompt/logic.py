"""Logic for Gemini API integration and prompt generation."""

import base64
import io
import json
import os
from typing import Optional, Tuple

import numpy as np
from PIL import Image

from .prompts import PROMPT_TEMPLATES


def tensor_to_pil(tensor: np.ndarray) -> Image.Image:
    """Convert ComfyUI tensor to PIL Image.

    Args:
        tensor: Input tensor in ComfyUI format (B, H, W, C)

    Returns:
        PIL Image object
    """
    # ComfyUI tensors are in [0, 1] range
    if tensor.ndim == 4:
        # Take first image from batch
        tensor = tensor[0]

    # Convert to uint8
    image_array = (tensor * 255).astype(np.uint8)

    # Convert to PIL
    return Image.fromarray(image_array, mode="RGB")


def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string.

    Args:
        image: PIL Image object
        format: Image format (PNG or JPEG)

    Returns:
        Base64 encoded string
    """
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def get_api_key() -> Optional[str]:
    """Get Gemini API key from environment or config.

    Returns:
        API key string or None if not found
    """
    # Check environment variable first
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        # Check for config file in ComfyUI directory
        try:
            config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "gemini_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config = json.load(f)
                    api_key = config.get("api_key")
        except Exception:
            pass

    return api_key


def analyze_image_with_gemini(
    image: np.ndarray,
    prompt_type: str,
    api_key: Optional[str] = None,
    custom_prompt: Optional[str] = None,
    model_name: str = "gemini-1.5-flash",
) -> Tuple[str, Optional[str]]:
    """Analyze image using Gemini API and generate appropriate prompt.

    Args:
        image: Input image tensor
        prompt_type: Type of prompt to generate (flux, sdxl, danbooru, video)
        api_key: Gemini API key (optional, will try to get from env/config)
        custom_prompt: Custom system prompt to use instead of templates
        model_name: Gemini model to use (default: gemini-1.5-flash)

    Returns:
        Tuple of (generated_prompt, error_message)
    """
    # Get API key
    if not api_key:
        api_key = get_api_key()

    if not api_key:
        return (
            "",
            "Gemini API key not found. Please set GEMINI_API_KEY environment variable or provide it in the node.",
        )

    # Convert tensor to PIL image
    try:
        pil_image = tensor_to_pil(image)
    except Exception as e:
        return "", f"Failed to convert image: {str(e)}"

    # Get system prompt
    if custom_prompt:
        system_prompt = custom_prompt
    else:
        system_prompt = PROMPT_TEMPLATES.get(prompt_type, PROMPT_TEMPLATES["flux"])

    # Here we would normally make the API call to Gemini
    # For now, we'll import the google-generativeai library
    try:
        import google.generativeai as genai
    except ImportError:
        return (
            "",
            "google-generativeai library not installed. Please run: pip install google-generativeai",
        )

    try:
        # Configure Gemini
        genai.configure(api_key=api_key)

        # Create model
        model = genai.GenerativeModel(model_name)

        # Generate content
        response = model.generate_content(
            [
                system_prompt,
                pil_image,
                "Analyze this image and generate an appropriate prompt according to the instructions.",
            ]
        )

        # Extract text from response
        if response.text:
            return response.text.strip(), None
        else:
            return "", "No response generated from Gemini"

    except Exception as e:
        return "", f"Gemini API error: {str(e)}"


def validate_prompt_type(prompt_type: str) -> bool:
    """Validate if prompt type is supported.

    Args:
        prompt_type: Type of prompt to validate

    Returns:
        True if valid, False otherwise
    """
    return prompt_type in PROMPT_TEMPLATES
