"""Unit tests for Gemini Prompt Engineer node."""

import pytest
import sys
import numpy as np
from unittest.mock import patch, MagicMock
from PIL import Image

from kikotools.tools.gemini_prompt import GeminiPromptNode
from kikotools.tools.gemini_prompt.logic import (
    tensor_to_pil,
    image_to_base64,
    get_api_key,
    validate_prompt_type,
    analyze_image_with_gemini,
)
from kikotools.tools.gemini_prompt.prompts import (
    PROMPT_OPTIONS,
    PROMPT_TEMPLATES,
    DEFAULT_GEMINI_MODELS,
)


class TestGeminiPromptNode:
    """Test cases for GeminiPromptNode."""

    def test_node_properties(self):
        """Test node has correct properties."""
        assert GeminiPromptNode.CATEGORY == "🫶 ComfyAssets/🧠 Prompts"
        assert GeminiPromptNode.FUNCTION == "generate_prompt"
        assert GeminiPromptNode.RETURN_TYPES == ("STRING", "STRING")
        assert GeminiPromptNode.RETURN_NAMES == ("prompt", "negative_prompt")

    def test_input_types(self):
        """Test INPUT_TYPES configuration."""
        input_types = GeminiPromptNode.INPUT_TYPES()

        # Check required inputs
        assert "required" in input_types
        assert "image" in input_types["required"]
        assert input_types["required"]["image"] == ("IMAGE",)
        assert "prompt_type" in input_types["required"]
        assert input_types["required"]["prompt_type"][0] == PROMPT_OPTIONS
        assert "model" in input_types["required"]
        # Check that model is a list (can be dynamic from API or DEFAULT_GEMINI_MODELS)
        model_list = input_types["required"]["model"][0]
        assert isinstance(model_list, list)
        assert len(model_list) > 0  # Should have at least one model

        # Check optional inputs
        assert "optional" in input_types
        assert "api_key" in input_types["optional"]
        assert "custom_prompt" in input_types["optional"]

    def test_default_gemini_models_structure(self):
        """Test that DEFAULT_GEMINI_MODELS has proper structure."""
        assert isinstance(DEFAULT_GEMINI_MODELS, list)
        assert len(DEFAULT_GEMINI_MODELS) > 0
        # Check at least some expected models are in the defaults
        assert any("gemini" in model.lower() for model in DEFAULT_GEMINI_MODELS)

    @patch("kikotools.tools.gemini_prompt.node.analyze_image_with_gemini")
    def test_generate_prompt_success(self, mock_analyze):
        """Test successful prompt generation."""
        # Setup
        node = GeminiPromptNode()
        test_image = np.random.rand(1, 512, 512, 3).astype(np.float32)
        mock_analyze.return_value = ("A beautiful landscape with mountains", None)

        # Execute
        result = node.generate_prompt(test_image, "flux", "gemini-2.5-flash")

        # Assert
        assert result == ("A beautiful landscape with mountains", "")
        mock_analyze.assert_called_once()

    @patch("kikotools.tools.gemini_prompt.node.analyze_image_with_gemini")
    def test_generate_prompt_sdxl_format(self, mock_analyze):
        """Test SDXL format with positive and negative prompts."""
        # Setup
        node = GeminiPromptNode()
        test_image = np.random.rand(1, 512, 512, 3).astype(np.float32)
        mock_analyze.return_value = (
            "Positive: beautiful landscape, mountains, sunset\nNegative: blurry, low quality",
            None,
        )

        # Execute
        result = node.generate_prompt(test_image, "sdxl", "gemini-2.5-flash")

        # Assert
        assert result == (
            "beautiful landscape, mountains, sunset",
            "blurry, low quality",
        )

    @patch("kikotools.tools.gemini_prompt.node.analyze_image_with_gemini")
    def test_generate_prompt_error(self, mock_analyze):
        """Test error handling in prompt generation."""
        # Setup
        node = GeminiPromptNode()
        test_image = np.random.rand(1, 512, 512, 3).astype(np.float32)
        mock_analyze.return_value = ("", "API key not found")

        # Execute
        result = node.generate_prompt(test_image, "flux", "gemini-2.5-flash")

        # Assert
        assert result[0].startswith("Error:")
        assert result[1] == ""

    def test_invalid_prompt_type(self):
        """Test handling of invalid prompt type."""
        node = GeminiPromptNode()
        test_image = np.random.rand(1, 512, 512, 3).astype(np.float32)

        with pytest.raises(ValueError, match="Invalid prompt type"):
            node.generate_prompt(test_image, "invalid_type", "gemini-2.5-flash")


class TestGeminiLogic:
    """Test cases for Gemini logic functions."""

    def test_tensor_to_pil(self):
        """Test tensor to PIL conversion."""
        # Test 4D tensor
        tensor_4d = np.random.rand(1, 64, 64, 3)
        result = tensor_to_pil(tensor_4d)
        assert isinstance(result, Image.Image)
        assert result.size == (64, 64)
        assert result.mode == "RGB"

        # Test 3D tensor
        tensor_3d = np.random.rand(64, 64, 3)
        result = tensor_to_pil(tensor_3d)
        assert isinstance(result, Image.Image)
        assert result.size == (64, 64)

    def test_image_to_base64(self):
        """Test image to base64 conversion."""
        # Create test image
        image = Image.new("RGB", (64, 64), color="red")

        # Convert to base64
        result = image_to_base64(image)
        assert isinstance(result, str)
        assert len(result) > 0

        # Test JPEG format
        result_jpeg = image_to_base64(image, format="JPEG")
        assert isinstance(result_jpeg, str)
        assert (
            result != result_jpeg
        )  # Different formats should produce different results

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test_key_123"})
    def test_get_api_key_from_env(self):
        """Test getting API key from environment."""
        result = get_api_key()
        assert result == "test_key_123"

    @patch.dict("os.environ", {}, clear=True)
    @patch("os.path.exists")
    @patch("builtins.open")
    def test_get_api_key_from_config(self, mock_open, mock_exists):
        """Test getting API key from config file."""
        # Setup
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = (
            '{"api_key": "config_key_456"}'
        )

        # Execute
        result = get_api_key()

        # Assert
        assert result == "config_key_456"

    def test_validate_prompt_type(self):
        """Test prompt type validation."""
        # Valid types
        for prompt_type in PROMPT_OPTIONS:
            assert validate_prompt_type(prompt_type) is True

        # Invalid types
        assert validate_prompt_type("invalid") is False
        assert validate_prompt_type("") is False
        assert validate_prompt_type(None) is False

    @pytest.mark.skip(reason="Requires google-generativeai library")
    def test_analyze_image_with_gemini_success(self):
        """Test successful image analysis with Gemini."""
        pass  # Skipped as it requires google-generativeai

    def test_analyze_image_no_api_key(self):
        """Test analysis without API key."""
        test_image = np.random.rand(64, 64, 3)

        with patch(
            "kikotools.tools.gemini_prompt.logic.get_api_key", return_value=None
        ):
            result, error = analyze_image_with_gemini(test_image, "flux")

        assert result == ""
        assert "API key not found" in error

    @pytest.mark.skip(reason="Requires google-generativeai library")
    def test_analyze_image_with_custom_prompt(self):
        """Test analysis with custom prompt."""
        pass  # Skipped as it requires google-generativeai


class TestPromptTemplates:
    """Test prompt template configurations."""

    def test_all_prompt_types_have_templates(self):
        """Test that all prompt options have corresponding templates."""
        for prompt_type in PROMPT_OPTIONS:
            assert prompt_type in PROMPT_TEMPLATES
            assert isinstance(PROMPT_TEMPLATES[prompt_type], str)
            assert len(PROMPT_TEMPLATES[prompt_type]) > 0

    def test_prompt_template_content(self):
        """Test that prompt templates contain expected content."""
        # FLUX prompt should mention FLUX
        assert "FLUX" in PROMPT_TEMPLATES["flux"]

        # SDXL prompt should mention positive and negative
        assert "Positive" in PROMPT_TEMPLATES["sdxl"]
        assert "Negative" in PROMPT_TEMPLATES["sdxl"]

        # Danbooru should mention tags and underscores
        assert "tag" in PROMPT_TEMPLATES["danbooru"].lower()
        assert "underscore" in PROMPT_TEMPLATES["danbooru"].lower()

        # Video should mention movement or motion and dynamics
        assert (
            "movement" in PROMPT_TEMPLATES["video"].lower()
            or "motion" in PROMPT_TEMPLATES["video"].lower()
        )
        assert (
            "dynamic" in PROMPT_TEMPLATES["video"].lower()
        )  # Check for dynamics instead of temporal
