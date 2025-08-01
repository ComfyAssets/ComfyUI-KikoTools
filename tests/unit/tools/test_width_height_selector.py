"""Tests for Width Height Selector tool."""

from kikotools.tools.width_height_selector.node import WidthHeightSelectorNode
from kikotools.tools.width_height_selector.logic import (
    get_preset_dimensions,
    calculate_aspect_ratio,
    validate_dimensions,
)
from kikotools.tools.width_height_selector.presets import (
    PRESET_OPTIONS,
    PRESET_METADATA,
    SDXL_PRESETS,
    FLUX_PRESETS,
    ULTRA_WIDE_PRESETS,
    get_preset_metadata,
    get_presets_by_model_group,
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
        """Test SDXL square preset (supports both raw and formatted)."""
        # Test raw preset
        result = self.node.get_dimensions(
            preset="1024×1024",
            width=512,  # Should be ignored
            height=512,  # Should be ignored
        )
        assert result == (1024, 1024)

        # Test formatted preset
        result = self.node.get_dimensions(
            preset="1024×1024 - 1:1 (1.1MP) - SDXL",
            width=512,  # Should be ignored
            height=512,  # Should be ignored
        )
        assert result == (1024, 1024)

    def test_sdxl_portrait_preset(self):
        """Test SDXL portrait preset (supports both raw and formatted)."""
        # Test raw preset
        result = self.node.get_dimensions(preset="832×1216", width=512, height=512)
        assert result == (832, 1216)

        # Test formatted preset if available
        formatted_preset = "832×1216 - 13:19 (1.0MP) - SDXL"
        result = self.node.get_dimensions(preset=formatted_preset, width=512, height=512)
        assert result == (832, 1216)

    def test_sdxl_landscape_preset(self):
        """Test SDXL landscape preset (supports both raw and formatted)."""
        # Test raw preset
        result = self.node.get_dimensions(preset="1216×832", width=512, height=512)
        assert result == (1216, 832)

        # Test formatted preset if available
        formatted_preset = "1216×832 - 19:13 (1.0MP) - SDXL"
        result = self.node.get_dimensions(preset=formatted_preset, width=512, height=512)
        assert result == (1216, 832)

    def test_flux_preset(self):
        """Test FLUX preset (supports both raw and formatted)."""
        # Test raw preset
        result = self.node.get_dimensions(preset="1920×1080", width=512, height=512)
        assert result == (1920, 1080)

        # Test formatted preset
        formatted_preset = "1920×1080 - 16:9 (2.1MP) - FLUX"
        result = self.node.get_dimensions(preset=formatted_preset, width=512, height=512)
        assert result == (1920, 1080)

    def test_ultra_wide_preset(self):
        """Test ultra-wide preset (supports both raw and formatted)."""
        # Test raw preset
        result = self.node.get_dimensions(preset="2560×1080", width=512, height=512)
        assert result == (2560, 1080)

        # Test formatted preset if available
        formatted_preset = "2560×1080 - 64:27 (2.8MP) - Ultra-Wide"
        result = self.node.get_dimensions(preset=formatted_preset, width=512, height=512)
        assert result == (2560, 1080)

    def test_all_presets_available(self):
        """Test that all presets are available in INPUT_TYPES."""
        input_types = self.node.INPUT_TYPES()
        available_presets = input_types["required"]["preset"][0]

        # Check that custom is available
        assert "custom" in available_presets

        # Check that formatted presets are available (with metadata)
        # Extract raw preset names from formatted options
        raw_presets = []
        for option in available_presets:
            if option == "custom":
                raw_presets.append(option)
            elif " - " in option:
                raw_presets.append(option.split(" - ")[0])
            else:
                raw_presets.append(option)

        # Check that all major preset categories are available
        assert "1024×1024" in raw_presets  # SDXL square
        assert "832×1216" in raw_presets  # SDXL portrait
        assert "1216×832" in raw_presets  # SDXL landscape
        assert "1920×1080" in raw_presets  # FLUX
        assert "2560×1080" in raw_presets  # Ultra-wide

    def test_invalid_preset_fallback(self):
        """Test handling of invalid preset."""
        # Should fall back to custom dimensions
        result = self.node.get_dimensions(preset="invalid_preset", width=800, height=600)
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
                assert height % 8 == 0, f"{preset_name} height {height} not divisible by 8"

    def test_preset_dimensions_within_limits(self):
        """Test that all preset dimensions are within acceptable limits."""
        for preset_dict in [SDXL_PRESETS, FLUX_PRESETS, ULTRA_WIDE_PRESETS]:
            for preset_name, (width, height) in preset_dict.items():
                assert 64 <= width <= 8192, f"{preset_name} width {width} out of range"
                assert 64 <= height <= 8192, f"{preset_name} height {height} out of range"


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


class TestPresetMetadata:
    """Test preset metadata functionality."""

    def test_preset_metadata_structure(self):
        """Test that metadata has correct structure."""
        for preset_name, metadata in PRESET_METADATA.items():
            assert hasattr(metadata, "width")
            assert hasattr(metadata, "height")
            assert hasattr(metadata, "aspect_ratio")
            assert hasattr(metadata, "aspect_decimal")
            assert hasattr(metadata, "megapixels")
            assert hasattr(metadata, "model_group")
            assert hasattr(metadata, "category")
            assert hasattr(metadata, "description")

    def test_metadata_aspect_ratios(self):
        """Test that aspect ratios are correctly calculated."""
        for preset_name, metadata in PRESET_METADATA.items():
            expected_decimal = metadata.width / metadata.height
            assert abs(metadata.aspect_decimal - expected_decimal) < 0.001

            # Common aspect ratios should match expected values
            if preset_name == "1024×1024":
                assert metadata.aspect_ratio == "1:1"
                assert metadata.aspect_decimal == 1.0
            elif preset_name == "1920×1080":
                assert metadata.aspect_ratio == "16:9"
                assert abs(metadata.aspect_decimal - 1.778) < 0.01

    def test_metadata_megapixels(self):
        """Test that megapixel calculations are correct."""
        for preset_name, metadata in PRESET_METADATA.items():
            expected_mp = (metadata.width * metadata.height) / 1_000_000
            assert abs(metadata.megapixels - expected_mp) < 0.1

    def test_model_groups(self):
        """Test that model groups are properly assigned."""
        sdxl_presets = get_presets_by_model_group("SDXL")
        flux_presets = get_presets_by_model_group("FLUX")
        ultra_wide_presets = get_presets_by_model_group("Ultra-Wide")

        assert len(sdxl_presets) > 0
        assert len(flux_presets) > 0
        assert len(ultra_wide_presets) > 0

        # Check specific presets are in correct groups
        assert "1024×1024" in [k for k, v in sdxl_presets.items()]
        assert "1920×1080" in [k for k, v in flux_presets.items()]
        assert "2560×1080" in [k for k, v in ultra_wide_presets.items()]

    def test_get_preset_metadata_function(self):
        """Test get_preset_metadata function."""
        # Valid preset
        metadata = get_preset_metadata("1024×1024")
        assert metadata.width == 1024
        assert metadata.height == 1024
        assert metadata.model_group == "SDXL"

        # Invalid preset returns default
        metadata = get_preset_metadata("invalid_preset")
        assert metadata.width == 0
        assert metadata.height == 0
        assert metadata.model_group == "Custom"


class TestNodeMetadataIntegration:
    """Test node integration with metadata."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = WidthHeightSelectorNode()

    def test_get_preset_info_with_metadata(self):
        """Test that preset info includes metadata."""
        info = self.node.get_preset_info("1024×1024")
        assert "1:1" in info  # Aspect ratio
        assert "1.0MP" in info or "1.1MP" in info  # Megapixels
        assert "SDXL" in info  # Description

    def test_get_presets_by_model_static(self):
        """Test static method for getting presets by model."""
        sdxl_presets = self.node.get_presets_by_model("SDXL")
        assert isinstance(sdxl_presets, dict)
        assert len(sdxl_presets) > 0

        # Check that returned values are metadata objects
        for preset_name, metadata in sdxl_presets.items():
            assert metadata.model_group == "SDXL"

    def test_get_preset_metadata_static(self):
        """Test static method for getting preset metadata."""
        metadata_dict = self.node.get_preset_metadata_static("1920×1080")

        assert metadata_dict["width"] == 1920
        assert metadata_dict["height"] == 1080
        assert metadata_dict["aspect_ratio"] == "16:9"
        assert metadata_dict["model_group"] == "FLUX"

    def test_get_model_groups(self):
        """Test static method for getting model groups."""
        groups = self.node.get_model_groups()
        assert "SDXL" in groups
        assert "FLUX" in groups
        assert "Ultra-Wide" in groups


class TestMetadataValidation:
    """Test metadata validation functions."""

    def test_dimensions_validation(self):
        """Test dimensions validation from metadata."""
        from kikotools.tools.width_height_selector.presets import (
            validate_preset_dimensions,
        )

        assert validate_preset_dimensions() is True

    def test_metadata_consistency_validation(self):
        """Test metadata consistency validation."""
        from kikotools.tools.width_height_selector.presets import (
            validate_metadata_consistency,
        )

        assert validate_metadata_consistency() is True


class TestFormattedPresets:
    """Test formatted preset functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = WidthHeightSelectorNode()

    def test_formatted_preset_generation(self):
        """Test that INPUT_TYPES generates formatted presets."""
        input_types = self.node.INPUT_TYPES()
        available_presets = input_types["required"]["preset"][0]

        # Should have custom first
        assert available_presets[0] == "custom"

        # Should have formatted presets with metadata
        formatted_count = 0
        for option in available_presets[1:]:  # Skip custom
            if " - " in option and "MP" in option:
                formatted_count += 1

        assert formatted_count > 0, "No formatted presets found"
        assert formatted_count == len(PRESET_METADATA), "Not all presets are formatted"

    def test_preset_name_extraction(self):
        """Test extraction of raw preset names from formatted strings."""
        test_cases = [
            ("custom", "custom"),
            ("1024×1024 - 1:1 (1.1MP) - SDXL", "1024×1024"),
            ("1920×1080 - 16:9 (2.1MP) - FLUX", "1920×1080"),
            ("832×1216 - 13:19 (1.0MP) - SDXL", "832×1216"),
            ("1024×1024", "1024×1024"),  # Raw preset name
            ("invalid_preset", "custom"),  # Invalid fallback
        ]

        for formatted_preset, expected in test_cases:
            result = self.node._extract_preset_name(formatted_preset)
            assert result == expected, f"Expected {expected}, got {result} for input {formatted_preset}"

    def test_formatted_preset_dimensions(self):
        """Test that formatted presets return correct dimensions."""
        # Test with formatted preset string
        formatted_preset = "1024×1024 - 1:1 (1.1MP) - SDXL"
        result = self.node.get_dimensions(formatted_preset, 512, 512)
        assert result == (1024, 1024)

        # Test with FLUX formatted preset
        formatted_preset = "1920×1080 - 16:9 (2.1MP) - FLUX"
        result = self.node.get_dimensions(formatted_preset, 512, 512)
        assert result == (1920, 1080)

    def test_formatted_preset_validation(self):
        """Test validation of formatted presets."""
        # Valid formatted preset
        assert self.node.validate_inputs("1024×1024 - 1:1 (1.1MP) - SDXL", 1024, 1024)

        # Valid raw preset
        assert self.node.validate_inputs("1024×1024", 1024, 1024)

        # Custom preset
        assert self.node.validate_inputs("custom", 1024, 1024)

        # Invalid formatted preset should still work (fallback to custom)
        assert self.node.validate_inputs("invalid - formatted", 1024, 1024)

    def test_backwards_compatibility(self):
        """Test that raw preset names still work."""
        # Raw preset names should still work for backwards compatibility
        raw_presets = ["1024×1024", "1920×1080", "832×1216"]

        for raw_preset in raw_presets:
            if raw_preset in PRESET_OPTIONS:
                result = self.node.get_dimensions(raw_preset, 512, 512)
                expected = PRESET_OPTIONS[raw_preset]
                assert result == expected, f"Raw preset {raw_preset} failed"

    def test_formatted_preset_metadata_accuracy(self):
        """Test that formatted presets contain accurate metadata."""
        input_types = self.node.INPUT_TYPES()
        formatted_presets = [opt for opt in input_types["required"]["preset"][0] if " - " in opt]

        for formatted_preset in formatted_presets:
            # Extract components
            parts = formatted_preset.split(" - ")
            assert len(parts) == 3, f"Formatted preset should have 3 parts: {formatted_preset}"

            resolution = parts[0]
            aspect_and_mp = parts[1]
            model_group = parts[2]

            # Verify resolution exists in metadata
            assert resolution in PRESET_METADATA, f"Resolution {resolution} not in metadata"

            # Verify metadata matches format
            metadata = PRESET_METADATA[resolution]
            assert metadata.model_group == model_group, f"Model group mismatch for {resolution}"
            assert metadata.aspect_ratio in aspect_and_mp, f"Aspect ratio not in {aspect_and_mp}"
            assert f"{metadata.megapixels:.1f}MP" in aspect_and_mp, f"Megapixels not in {aspect_and_mp}"
