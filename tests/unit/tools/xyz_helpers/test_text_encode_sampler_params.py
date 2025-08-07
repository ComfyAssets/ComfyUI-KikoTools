"""Tests for Text Encode Sampler Params node."""

import pytest
from kikotools.tools.xyz_helpers.text_encode_sampler_params import (
    TextEncodeSamplerParamsNode,
)
from kikotools.tools.xyz_helpers.text_encode_sampler_params.logic import (
    split_prompts,
    create_sampler_params_conditioning,
    validate_prompt_format,
    get_prompt_statistics,
)


class TestTextEncodeSamplerParamsLogic:
    """Test the logic functions for Text Encode Sampler Params."""

    def test_split_prompts_with_dashes(self):
        """Test splitting prompts with dash separators."""
        text = "First prompt\n---\nSecond prompt\n---\nThird prompt"
        prompts = split_prompts(text)
        assert len(prompts) == 3
        assert prompts[0] == "First prompt"
        assert prompts[1] == "Second prompt"
        assert prompts[2] == "Third prompt"

    def test_split_prompts_with_various_separators(self):
        """Test with different separator types."""
        text = "First\n***\nSecond\n===\nThird\n~~~\nFourth"
        prompts = split_prompts(text)
        assert len(prompts) == 4

    def test_split_prompts_with_extra_separators(self):
        """Test with longer separators."""
        text = "First\n--------\nSecond\n*********\nThird"
        prompts = split_prompts(text)
        assert len(prompts) == 3

    def test_split_prompts_no_separator(self):
        """Test with no separator."""
        text = "Single prompt without separator"
        prompts = split_prompts(text)
        assert len(prompts) == 1
        assert prompts[0] == "Single prompt without separator"

    def test_split_prompts_empty_sections(self):
        """Test with empty sections between separators."""
        text = "First\n---\n\n---\nThird"
        prompts = split_prompts(text)
        assert len(prompts) == 2
        assert prompts[0] == "First"
        assert prompts[1] == "Third"

    def test_create_sampler_params_conditioning(self):
        """Test creating conditioning dictionary."""
        prompts = ["prompt1", "prompt2"]
        encoded = [{"mock": "encoded1"}, {"mock": "encoded2"}]

        result = create_sampler_params_conditioning(prompts, encoded)
        assert result["text"] == prompts
        assert result["encoded"] == encoded
        assert result["count"] == 2

    def test_validate_prompt_format(self):
        """Test prompt format validation."""
        assert validate_prompt_format("Valid prompt") == True
        assert validate_prompt_format("") == False
        assert validate_prompt_format("   ") == False

        # Test very long prompt
        long_prompt = "a" * 10001
        assert validate_prompt_format(long_prompt) == False

    def test_get_prompt_statistics(self):
        """Test getting prompt statistics."""
        prompts = ["short", "medium prompt", "this is a longer prompt"]
        stats = get_prompt_statistics(prompts)

        assert stats["count"] == 3
        assert stats["min_chars"] == 5
        assert stats["max_chars"] == 23
        assert stats["total_chars"] == 41

    def test_get_prompt_statistics_empty(self):
        """Test statistics with empty prompts."""
        stats = get_prompt_statistics([])
        assert stats["count"] == 0
        assert stats["total_chars"] == 0


class TestTextEncodeSamplerParamsNode:
    """Test the Text Encode Sampler Params node."""

    @pytest.fixture
    def node(self):
        """Create a node instance."""
        return TextEncodeSamplerParamsNode()

    @pytest.fixture
    def mock_clip(self):
        """Create a mock CLIP encoder."""

        class MockCLIP:
            pass

        return MockCLIP()

    def test_input_types(self):
        """Test that INPUT_TYPES returns correct structure."""
        input_types = TextEncodeSamplerParamsNode.INPUT_TYPES()
        assert "required" in input_types

        required = input_types["required"]
        assert "text" in required
        assert "clip" in required
        assert required["text"][0] == "STRING"
        assert required["clip"][0] == "CLIP"

    def test_encode_prompts_single(self, node, mock_clip):
        """Test encoding a single prompt."""
        text = "Single prompt without separator"
        result = node.encode_prompts(text, mock_clip)

        assert isinstance(result, tuple)
        assert len(result) == 1
        conditioning = result[0]
        assert "text" in conditioning
        assert "encoded" in conditioning

    def test_encode_prompts_multiple(self, node, mock_clip):
        """Test encoding multiple prompts."""
        text = "First prompt\n---\nSecond prompt\n---\nThird prompt"
        result = node.encode_prompts(text, mock_clip)

        assert isinstance(result, tuple)
        conditioning = result[0]
        assert len(conditioning["text"]) == 3

    def test_node_properties(self):
        """Test node properties."""
        assert TextEncodeSamplerParamsNode.CATEGORY == "ComfyAssets/🧰 xyz-helpers"
        assert TextEncodeSamplerParamsNode.FUNCTION == "encode_prompts"
        assert TextEncodeSamplerParamsNode.RETURN_TYPES == ("CONDITIONING",)
        assert TextEncodeSamplerParamsNode.RETURN_NAMES == ("conditioning",)
