"""
Unit tests for Resolution Calculator tool
Following TDD principles - these tests define the expected behavior
"""

import pytest
import torch

# Import the modules we're going to test (they don't exist yet - TDD!)
from kikotools.tools.resolution_calculator.logic import (
    extract_dimensions,
    calculate_scaled_dimensions,
    ensure_divisible_by_8,
)
from kikotools.tools.resolution_calculator.node import ResolutionCalculatorNode


class TestDimensionExtraction:
    """Test dimension extraction from IMAGE and LATENT tensors"""

    def test_extract_dimensions_from_image(self, mock_image_tensor):
        """Test extracting dimensions from IMAGE tensor"""
        # IMAGE tensor format: [batch, height, width, channels]
        # Expected: 832x1216 (width x height)
        width, height = extract_dimensions(image=mock_image_tensor)

        assert width == 832
        assert height == 1216

    def test_extract_dimensions_from_square_image(self, mock_image_tensor_square):
        """Test extracting dimensions from square IMAGE tensor"""
        width, height = extract_dimensions(image=mock_image_tensor_square)

        assert width == 1024
        assert height == 1024

    def test_extract_dimensions_from_latent(self, mock_latent_tensor):
        """Test extracting dimensions from LATENT tensor"""
        # LATENT format: {"samples": [batch, channels, height/8, width/8]}
        # Latent dimensions need to be multiplied by 8
        # Expected: 832x1216 (104*8 x 152*8)
        width, height = extract_dimensions(latent=mock_latent_tensor)

        assert width == 832
        assert height == 1216

    def test_extract_dimensions_from_square_latent(self, mock_latent_tensor_square):
        """Test extracting dimensions from square LATENT tensor"""
        width, height = extract_dimensions(latent=mock_latent_tensor_square)

        assert width == 1024
        assert height == 1024

    def test_extract_dimensions_no_input_raises_error(self):
        """Test that providing no input raises ValueError"""
        with pytest.raises(ValueError, match="Either image or latent must be provided"):
            extract_dimensions()

    def test_extract_dimensions_both_inputs_prefers_image(
        self, mock_image_tensor, mock_latent_tensor
    ):
        """Test that when both inputs provided, image takes precedence"""
        width, height = extract_dimensions(
            image=mock_image_tensor, latent=mock_latent_tensor
        )

        # Should return image dimensions, not latent
        assert width == 832
        assert height == 1216


class TestScaledDimensionsCalculation:
    """Test calculation of scaled dimensions with various scale factors"""

    def test_calculate_scaled_dimensions_2x(self):
        """Test 2x scaling"""
        width, height = calculate_scaled_dimensions(512, 512, 2.0)

        assert width == 1024
        assert height == 1024

    def test_calculate_scaled_dimensions_1_5x(self):
        """Test 1.5x scaling with SDXL portrait dimensions"""
        # Original SDXL portrait: 832x1216
        # 1.5x scale: 1248x1824
        width, height = calculate_scaled_dimensions(832, 1216, 1.5)

        assert width == 1248
        assert height == 1824

    def test_calculate_scaled_dimensions_preserves_aspect_ratio(self):
        """Test that scaling preserves aspect ratio"""
        original_width, original_height = 832, 1216
        scale_factor = 1.5

        new_width, new_height = calculate_scaled_dimensions(
            original_width, original_height, scale_factor
        )

        # Check aspect ratio is preserved (within floating point precision)
        original_ratio = original_width / original_height
        new_ratio = new_width / new_height
        assert abs(original_ratio - new_ratio) < 0.001

    def test_calculate_scaled_dimensions_various_factors(self, sample_scale_factors):
        """Test scaling with various common scale factors"""
        base_width, base_height = 1024, 1024

        for scale_factor in sample_scale_factors:
            width, height = calculate_scaled_dimensions(
                base_width, base_height, scale_factor
            )

            expected_width = int(base_width * scale_factor)
            expected_height = int(base_height * scale_factor)

            # Allow for rounding to nearest multiple of 8
            assert abs(width - expected_width) <= 8
            assert abs(height - expected_height) <= 8


class TestDivisibleBy8Constraint:
    """Test ensuring dimensions are divisible by 8 (ComfyUI requirement)"""

    def test_ensure_divisible_by_8_already_divisible(self):
        """Test dimensions already divisible by 8"""
        width, height = ensure_divisible_by_8(1024, 1024)

        assert width == 1024
        assert height == 1024
        assert width % 8 == 0
        assert height % 8 == 0

    def test_ensure_divisible_by_8_needs_rounding(self):
        """Test rounding to nearest multiple of 8"""
        # 1250 -> 1248 (nearest multiple of 8, rounds down since 1250 % 8 = 2 < 4)
        # 1825 -> 1824 (nearest multiple of 8, rounds down since 1825 % 8 = 1 < 4)
        width, height = ensure_divisible_by_8(1250, 1825)

        assert width == 1248
        assert height == 1824
        assert width % 8 == 0
        assert height % 8 == 0

    def test_ensure_divisible_by_8_needs_rounding_down(self):
        """Test rounding to nearest multiple of 8 (could be down)"""
        # Test with values that should round down
        # 1251 -> 1248 (previous multiple of 8 if we round to nearest)
        # But our algorithm should round to nearest, so:
        # 1251 -> 1256 (closer to 1256 than 1248)
        width, height = ensure_divisible_by_8(1251, 1827)

        assert width % 8 == 0
        assert height % 8 == 0
        # Should be close to original values
        assert abs(width - 1251) <= 8
        assert abs(height - 1827) <= 8

    def test_various_inputs_always_divisible_by_8(self):
        """Test that various inputs always result in dimensions divisible by 8"""
        test_values = [100, 256, 511, 513, 999, 1000, 1023, 1025, 2000]

        for val in test_values:
            width, height = ensure_divisible_by_8(val, val)
            assert width % 8 == 0, f"Width {width} not divisible by 8"
            assert height % 8 == 0, f"Height {height} not divisible by 8"


class TestResolutionCalculatorNode:
    """Test the ComfyUI node interface"""

    def test_node_has_correct_comfyui_attributes(self):
        """Test node has all required ComfyUI attributes"""
        # Check class attributes exist
        assert hasattr(ResolutionCalculatorNode, "INPUT_TYPES")
        assert hasattr(ResolutionCalculatorNode, "RETURN_TYPES")
        assert hasattr(ResolutionCalculatorNode, "RETURN_NAMES")
        assert hasattr(ResolutionCalculatorNode, "FUNCTION")
        assert hasattr(ResolutionCalculatorNode, "CATEGORY")

        # Check category is correct
        assert ResolutionCalculatorNode.CATEGORY == "ComfyAssets/🖼️ Resolution"

        # Check return types
        assert ResolutionCalculatorNode.RETURN_TYPES == ("INT", "INT")
        assert ResolutionCalculatorNode.RETURN_NAMES == ("width", "height")

        # Check function name
        assert ResolutionCalculatorNode.FUNCTION == "calculate_resolution"

    def test_input_types_structure(self):
        """Test INPUT_TYPES has correct structure"""
        input_types = ResolutionCalculatorNode.INPUT_TYPES()

        assert "required" in input_types
        assert "optional" in input_types

        # Check required inputs
        assert "scale_factor" in input_types["required"]
        scale_config = input_types["required"]["scale_factor"]
        assert scale_config[0] == "FLOAT"
        assert "default" in scale_config[1]
        assert "min" in scale_config[1]
        assert "max" in scale_config[1]

        # Check optional inputs
        assert "image" in input_types["optional"]
        assert "latent" in input_types["optional"]
        assert input_types["optional"]["image"][0] == "IMAGE"
        assert input_types["optional"]["latent"][0] == "LATENT"

    def test_calculate_resolution_with_image(self, mock_image_tensor):
        """Test node calculation with IMAGE input"""
        node = ResolutionCalculatorNode()

        width, height = node.calculate_resolution(
            scale_factor=2.0, image=mock_image_tensor
        )

        # Original: 832x1216, 2x scale = 1664x2432
        assert isinstance(width, int)
        assert isinstance(height, int)
        assert width % 8 == 0
        assert height % 8 == 0
        # Should be approximately 2x the original dimensions
        assert 1600 <= width <= 1700  # Allow for rounding
        assert 2400 <= height <= 2500

    def test_calculate_resolution_with_latent(self, mock_latent_tensor):
        """Test node calculation with LATENT input"""
        node = ResolutionCalculatorNode()

        width, height = node.calculate_resolution(
            scale_factor=1.5, latent=mock_latent_tensor
        )

        # Original: 832x1216, 1.5x scale = 1248x1824
        assert isinstance(width, int)
        assert isinstance(height, int)
        assert width % 8 == 0
        assert height % 8 == 0
        # Should be approximately 1.5x the original dimensions
        assert 1200 <= width <= 1300
        assert 1800 <= height <= 1900

    def test_calculate_resolution_no_input_raises_error(self):
        """Test that no input raises appropriate error"""
        node = ResolutionCalculatorNode()

        with pytest.raises(ValueError):
            node.calculate_resolution(scale_factor=2.0)

    def test_calculate_resolution_with_various_scale_factors(
        self, mock_image_tensor_square, sample_scale_factors
    ):
        """Test calculation with various scale factors"""
        node = ResolutionCalculatorNode()

        for scale_factor in sample_scale_factors:
            width, height = node.calculate_resolution(
                scale_factor=scale_factor, image=mock_image_tensor_square
            )

            # All results should be integers divisible by 8
            assert isinstance(width, int)
            assert isinstance(height, int)
            assert width % 8 == 0
            assert height % 8 == 0

            # Results should be reasonable (not too small/large)
            assert 64 <= width <= 8192
            assert 64 <= height <= 8192

    def test_inherits_from_base_node(self):
        """Test that node inherits from ComfyAssetsBaseNode"""
        from kikotools.base import ComfyAssetsBaseNode

        assert issubclass(ResolutionCalculatorNode, ComfyAssetsBaseNode)

        # Test inherited functionality
        node = ResolutionCalculatorNode()
        node_info = node.get_node_info()

        assert node_info["category"] == "ComfyAssets/🖼️ Resolution"
        assert node_info["class_name"] == "ResolutionCalculatorNode"


class TestIntegrationScenarios:
    """Test real-world usage scenarios"""

    def test_sdxl_portrait_upscale_scenario(self):
        """Test the exact scenario from the user example"""
        # Original: 832×1216, upscaled to ~1280×1856 (≈1.53x)

        # Create mock tensor matching the scenario
        mock_tensor = torch.randn(1, 1216, 832, 3)  # [batch, height, width, channels]

        node = ResolutionCalculatorNode()
        width, height = node.calculate_resolution(scale_factor=1.53, image=mock_tensor)

        # Should be close to expected dimensions
        assert abs(width - 1280) <= 16  # Allow some rounding variance
        assert abs(height - 1856) <= 16
        assert width % 8 == 0
        assert height % 8 == 0

    def test_flux_square_upscale_scenario(self):
        """Test FLUX square format upscaling"""
        # FLUX 1024x1024 -> 2x scale
        mock_tensor = torch.randn(1, 1024, 1024, 3)

        node = ResolutionCalculatorNode()
        width, height = node.calculate_resolution(scale_factor=2.0, image=mock_tensor)

        assert width == 2048
        assert height == 2048
        assert width % 8 == 0
        assert height % 8 == 0

    def test_latent_to_upscaler_workflow(self):
        """Test typical workflow: latent -> resolution calc -> upscaler"""
        # Simulate a latent from generation process
        latent_samples = torch.randn(1, 4, 128, 128)  # 1024x1024 equivalent
        mock_latent = {"samples": latent_samples}

        node = ResolutionCalculatorNode()
        width, height = node.calculate_resolution(scale_factor=1.5, latent=mock_latent)

        # Should calculate upscaled dimensions for 1024x1024 * 1.5
        expected_width = 1536  # Will be rounded to nearest 8
        expected_height = 1536

        assert abs(width - expected_width) <= 8
        assert abs(height - expected_height) <= 8
        assert width % 8 == 0
        assert height % 8 == 0
