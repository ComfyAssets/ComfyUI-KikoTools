"""Tests for Width Height Selector tool."""

import pytest
from unittest.mock import Mock
from kikotools.tools.width_height_selector.node import WidthHeightSelectorNode
from kikotools.tools.width_height_selector.logic import (
    get_preset_dimensions,
    calculate_aspect_ratio,
    validate_dimensions,
)
from kikotools.tools.width_height_selector.presets import (
    PRESET_OPTIONS,
    SDXL_PRESETS,
    FLUX_PRESETS,
    ULTRA_WIDE_PRESETS,
)


class TestWidthHeightSelectorNode:
    """Test the WidthHeightSelectorNode class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = WidthHeightSelectorNode()

    def test_node_structure(self):
        """Test that node has required ComfyUI structure."""
        # Test INPUT_TYPES
        input_types = self.node.INPUT_TYPES()
        assert "required" in input_types
        assert "preset" in input_types["required"]
        assert "width" in input_types["required"]
        assert "height" in input_types["required"]

        # Test return types
        assert self.node.RETURN_TYPES == ("INT", "INT")
        assert self.node.RETURN_NAMES == ("width", "height")
        assert self.node.FUNCTION == "get_dimensions"
        assert self.node.CATEGORY == "ComfyAssets"

    def test_custom_dimensions(self):
        """Test custom dimensions."""
        result = self.node.get_dimensions(preset="custom", width=1920, height=1080)
        assert result == (1920, 1080)

    def test_sdxl_square_preset(self):
        """Test SDXL square preset."""
        result = self.node.get_dimensions(
            preset="1024×1024",
            width=512,  # Should be ignored
            height=512,  # Should be ignored
        )
        assert result == (1024, 1024)

    def test_sdxl_portrait_preset(self):
        """Test SDXL portrait preset."""
        result = self.node.get_dimensions(preset="832×1216", width=512, height=512)
        assert result == (832, 1216)

    def test_sdxl_landscape_preset(self):
        """Test SDXL landscape preset."""
        result = self.node.get_dimensions(preset="1216×832", width=512, height=512)
        assert result == (1216, 832)

    def test_flux_preset(self):
        """Test FLUX preset."""
        result = self.node.get_dimensions(preset="1920×1080", width=512, height=512)
        assert result == (1920, 1080)

    def test_ultra_wide_preset(self):
        """Test ultra-wide preset."""
        result = self.node.get_dimensions(preset="2560×1080", width=512, height=512)
        assert result == (2560, 1080)

    def test_all_presets_available(self):
        """Test that all presets are available in INPUT_TYPES."""
        input_types = self.node.INPUT_TYPES()
        available_presets = input_types["required"]["preset"][0]

        # Check that all major preset categories are available
        assert "custom" in available_presets
        assert "1024×1024" in available_presets  # SDXL square
        assert "832×1216" in available_presets  # SDXL portrait
        assert "1216×832" in available_presets  # SDXL landscape
        assert "1920×1080" in available_presets  # FLUX
        assert "2560×1080" in available_presets  # Ultra-wide

    def test_invalid_preset_fallback(self):
        """Test handling of invalid preset."""
        # Should fall back to custom dimensions
        result = self.node.get_dimensions(
            preset="invalid_preset", width=800, height=600
        )
        assert result == (800, 600)


class TestPresetLogic:
    """Test the preset logic functions."""

    def test_get_preset_dimensions_custom(self):
        """Test getting custom dimensions."""
        width, height = get_preset_dimensions("custom", 1920, 1080)
        assert width == 1920
        assert height == 1080

    def test_get_preset_dimensions_sdxl(self):
        """Test getting SDXL preset dimensions."""
        width, height = get_preset_dimensions("1024×1024", 512, 512)
        assert width == 1024
        assert height == 1024

    def test_get_preset_dimensions_flux(self):
        """Test getting FLUX preset dimensions."""
        width, height = get_preset_dimensions("1920×1080", 512, 512)
        assert width == 1920
        assert height == 1080

    def test_get_preset_dimensions_invalid(self):
        """Test getting dimensions for invalid preset."""
        width, height = get_preset_dimensions("invalid", 800, 600)
        assert width == 800
        assert height == 600


class TestDimensionValidation:
    """Test dimension validation."""

    def test_validate_dimensions_valid(self):
        """Test validation of valid dimensions."""
        assert validate_dimensions(1024, 1024) is True
        assert validate_dimensions(1920, 1080) is True
        assert validate_dimensions(832, 1216) is True

    def test_validate_dimensions_divisible_by_8(self):
        """Test that dimensions must be divisible by 8."""
        assert validate_dimensions(1024, 1024) is True  # Both divisible by 8
        assert validate_dimensions(1025, 1024) is False  # Width not divisible by 8
        assert validate_dimensions(1024, 1025) is False  # Height not divisible by 8
        assert validate_dimensions(1025, 1025) is False  # Neither divisible by 8

    def test_validate_dimensions_minimum_size(self):
        """Test minimum dimension requirements."""
        assert validate_dimensions(64, 64) is True  # Minimum allowed
        assert validate_dimensions(32, 64) is False  # Width too small
        assert validate_dimensions(64, 32) is False  # Height too small
        assert validate_dimensions(32, 32) is False  # Both too small

    def test_validate_dimensions_maximum_size(self):
        """Test maximum dimension requirements."""
        assert validate_dimensions(8192, 8192) is True  # Maximum allowed
        assert validate_dimensions(8200, 8192) is False  # Width too large
        assert validate_dimensions(8192, 8200) is False  # Height too large
        assert validate_dimensions(8200, 8200) is False  # Both too large


class TestPresetDefinitions:
    """Test preset definitions."""

    def test_sdxl_presets_structure(self):
        """Test SDXL presets are properly defined."""
        assert "1024×1024" in SDXL_PRESETS
        assert "832×1216" in SDXL_PRESETS
        assert "1216×832" in SDXL_PRESETS

        # Check dimensions are tuples
        for preset, dims in SDXL_PRESETS.items():
            assert isinstance(dims, tuple)
            assert len(dims) == 2
            assert isinstance(dims[0], int)
            assert isinstance(dims[1], int)

    def test_flux_presets_structure(self):
        """Test FLUX presets are properly defined."""
        assert "1920×1080" in FLUX_PRESETS
        assert "1536×1536" in FLUX_PRESETS

        # Check dimensions are tuples
        for preset, dims in FLUX_PRESETS.items():
            assert isinstance(dims, tuple)
            assert len(dims) == 2
            assert isinstance(dims[0], int)
            assert isinstance(dims[1], int)

    def test_ultra_wide_presets_structure(self):
        """Test ultra-wide presets are properly defined."""
        assert "2560×1080" in ULTRA_WIDE_PRESETS

        # Check dimensions are tuples
        for preset, dims in ULTRA_WIDE_PRESETS.items():
            assert isinstance(dims, tuple)
            assert len(dims) == 2
            assert isinstance(dims[0], int)
            assert isinstance(dims[1], int)

    def test_preset_options_combined(self):
        """Test that PRESET_OPTIONS combines all presets correctly."""
        assert "custom" in PRESET_OPTIONS

        # Check SDXL presets are included
        for preset in SDXL_PRESETS:
            assert preset in PRESET_OPTIONS

        # Check FLUX presets are included
        for preset in FLUX_PRESETS:
            assert preset in PRESET_OPTIONS

        # Check ultra-wide presets are included
        for preset in ULTRA_WIDE_PRESETS:
            assert preset in PRESET_OPTIONS

    def test_all_presets_divisible_by_8(self):
        """Test that all preset dimensions are divisible by 8."""
        for preset_dict in [SDXL_PRESETS, FLUX_PRESETS, ULTRA_WIDE_PRESETS]:
            for preset_name, (width, height) in preset_dict.items():
                assert width % 8 == 0, f"{preset_name} width {width} not divisible by 8"
                assert (
                    height % 8 == 0
                ), f"{preset_name} height {height} not divisible by 8"

    def test_preset_dimensions_within_limits(self):
        """Test that all preset dimensions are within acceptable limits."""
        for preset_dict in [SDXL_PRESETS, FLUX_PRESETS, ULTRA_WIDE_PRESETS]:
            for preset_name, (width, height) in preset_dict.items():
                assert 64 <= width <= 8192, f"{preset_name} width {width} out of range"
                assert (
                    64 <= height <= 8192
                ), f"{preset_name} height {height} out of range"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zero_dimensions(self):
        """Test handling of zero dimensions."""
        assert validate_dimensions(0, 1024) is False
        assert validate_dimensions(1024, 0) is False
        assert validate_dimensions(0, 0) is False

    def test_negative_dimensions(self):
        """Test handling of negative dimensions."""
        assert validate_dimensions(-100, 1024) is False
        assert validate_dimensions(1024, -100) is False
        assert validate_dimensions(-100, -100) is False

    def test_very_large_dimensions(self):
        """Test handling of very large dimensions."""
        assert validate_dimensions(10000, 1024) is False
        assert validate_dimensions(1024, 10000) is False
        assert validate_dimensions(10000, 10000) is False

    def test_aspect_ratio_edge_cases(self):
        """Test aspect ratio calculation edge cases."""
        # Very wide aspect ratio
        ratio = calculate_aspect_ratio(3840, 1080)
        assert ratio == "32:9"

        # Very tall aspect ratio
        ratio = calculate_aspect_ratio(1080, 3840)
        assert ratio == "9:32"

        # Prime number dimensions
        ratio = calculate_aspect_ratio(1920, 1080)
        assert ratio == "16:9"
