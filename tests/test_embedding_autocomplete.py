"""Basic tests for KikoEmbeddingAutocomplete."""

import sys
from unittest.mock import MagicMock, patch


def test_import():
    """Test that the module can be imported."""
    from kikotools.tools.embedding_autocomplete import KikoEmbeddingAutocomplete

    assert KikoEmbeddingAutocomplete is not None
    assert (
        KikoEmbeddingAutocomplete.DISPLAY_NAME
        == "🫶 Embedding Autocomplete Settings"
    )
    assert KikoEmbeddingAutocomplete.CATEGORY == "ComfyAssets"


def test_settings_defined():
    """Test that settings are properly defined."""
    from kikotools.tools.embedding_autocomplete import KikoEmbeddingAutocomplete

    settings = KikoEmbeddingAutocomplete.SETTINGS
    assert "enabled" in settings
    assert "min_chars" in settings  # Changed from trigger_chars
    assert "max_suggestions" in settings
    assert "show_embeddings" in settings
    assert "show_loras" in settings
    assert "embedding_trigger" in settings
    assert "lora_trigger" in settings
    assert "quick_trigger" in settings
    assert "sort_by_directory" in settings

    # Check settings structure
    assert settings["enabled"]["type"] == "boolean"
    assert settings["enabled"]["default"] is True
    assert settings["min_chars"]["type"] == "combo"
    assert settings["min_chars"]["options"] == [1, 2, 3, 4, 5]


def test_input_types():
    """Test INPUT_TYPES class method."""
    from kikotools.tools.embedding_autocomplete import KikoEmbeddingAutocomplete

    input_types = KikoEmbeddingAutocomplete.INPUT_TYPES()
    assert "required" in input_types
    assert "hidden" in input_types
    assert input_types["required"] == {}  # No required inputs
    assert "unique_id" in input_types["hidden"]


def test_api_suggestions():
    """Test the API suggestions method."""
    from kikotools.tools.embedding_autocomplete.node import (
        KikoEmbeddingAutocompleteAPI,
        folder_paths,
    )

    # Mock folder_paths if it exists (will be None in tests)
    with patch("kikotools.tools.embedding_autocomplete.node.folder_paths") as mock_fp:
        mock_fp.get_filename_list = MagicMock(
            side_effect=lambda x: (
                ["test1.pt", "test2.safetensors"]
                if x == "embeddings"
                else ["lora1.pt", "lora2.safetensors"]
            )
        )

        # Test with embeddings
        suggestions = KikoEmbeddingAutocompleteAPI.get_suggestions(
            prefix="test", include_embeddings=True, include_loras=False
        )

        assert len(suggestions) == 2
        assert suggestions[0]["type"] == "embedding"
        assert suggestions[0]["name"] == "test1"

        # Test with LoRAs
        suggestions = KikoEmbeddingAutocompleteAPI.get_suggestions(
            prefix="lora", include_embeddings=False, include_loras=True
        )

        assert len(suggestions) == 2
        assert suggestions[0]["type"] == "lora"
        assert "<lora:" in suggestions[0]["value"]


if __name__ == "__main__":
    test_import()
    test_settings_defined()
    test_input_types()
    test_api_suggestions()
    print("All tests passed!")
