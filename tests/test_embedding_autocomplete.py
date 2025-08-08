"""Basic tests for KikoEmbeddingAutocomplete."""

import sys
from unittest.mock import MagicMock

# Mock ComfyUI's folder_paths module
sys.modules['folder_paths'] = MagicMock()
sys.modules['folder_paths'].get_filename_list = MagicMock(return_value=[])
sys.modules['folder_paths'].get_folder_paths = MagicMock(return_value=["/mock/path"])
sys.modules['folder_paths'].base_path = "/mock/base"


def test_import():
    """Test that the module can be imported."""
    from kikotools.tools.embedding_autocomplete import KikoEmbeddingAutocomplete
    assert KikoEmbeddingAutocomplete is not None
    assert KikoEmbeddingAutocomplete.DISPLAY_NAME == "Embedding Autocomplete"
    assert KikoEmbeddingAutocomplete.CATEGORY == "ComfyAssets"


def test_settings_defined():
    """Test that settings are properly defined."""
    from kikotools.tools.embedding_autocomplete import KikoEmbeddingAutocomplete
    
    settings = KikoEmbeddingAutocomplete.SETTINGS
    assert "enabled" in settings
    assert "trigger_chars" in settings
    assert "max_suggestions" in settings
    assert "show_embeddings" in settings
    assert "show_loras" in settings
    assert "case_sensitive" in settings
    
    # Check settings structure
    assert settings["enabled"]["type"] == "boolean"
    assert settings["enabled"]["default"] is True
    assert settings["trigger_chars"]["type"] == "combo"
    assert settings["trigger_chars"]["options"] == [1, 2, 3, 4]


def test_input_types():
    """Test INPUT_TYPES class method."""
    from kikotools.tools.embedding_autocomplete import KikoEmbeddingAutocomplete
    
    input_types = KikoEmbeddingAutocomplete.INPUT_TYPES()
    assert "required" in input_types
    assert "optional" in input_types
    assert "refresh" in input_types["optional"]


def test_api_suggestions():
    """Test the API suggestions method."""
    from kikotools.tools.embedding_autocomplete.node import KikoEmbeddingAutocompleteAPI
    
    # Mock folder_paths to return some test files
    sys.modules['folder_paths'].get_filename_list = MagicMock(
        side_effect=lambda x: ["test1.pt", "test2.safetensors"] if x == "embeddings" else ["lora1.pt", "lora2.safetensors"]
    )
    
    # Test with embeddings
    suggestions = KikoEmbeddingAutocompleteAPI.get_suggestions(
        prefix="test",
        include_embeddings=True,
        include_loras=False
    )
    
    assert len(suggestions) == 2
    assert suggestions[0]["type"] == "embedding"
    assert suggestions[0]["name"] == "test1"
    
    # Test with LoRAs
    suggestions = KikoEmbeddingAutocompleteAPI.get_suggestions(
        prefix="lora",
        include_embeddings=False,
        include_loras=True
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