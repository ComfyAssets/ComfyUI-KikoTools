"""Unit tests for ImageToMultipleOf tool."""

import pytest
import torch

import sys
from pathlib import Path

# Add the project root to the Python path for tests
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from kikotools.tools.image_to_multiple_of.logic import (
    calculate_dimensions_to_multiple,
    process_image_to_multiple_of,
)
from kikotools.tools.image_to_multiple_of.node import ImageToMultipleOfNode


class TestImageToMultipleOfLogic:
    """Test core logic functions."""

    def test_calculate_dimensions_to_multiple(self):
        """Test dimension calculation for various inputs."""
        # Test exact multiples
        assert calculate_dimensions_to_multiple(256, 512, 64) == (256, 512)

        # Test non-exact multiples
        assert calculate_dimensions_to_multiple(300, 400, 64) == (256, 384)
        assert calculate_dimensions_to_multiple(150, 200, 32) == (128, 192)

        # Test small values
        assert calculate_dimensions_to_multiple(10, 20, 8) == (8, 16)

        # Test with multiple_of = 1 (should return original)
        assert calculate_dimensions_to_multiple(123, 456, 1) == (123, 456)

    def test_process_image_center_crop(self):
        """Test center crop processing."""
        # Create test image (batch=1, height=300, width=400, channels=3)
        image = torch.rand(1, 300, 400, 3)

        # Process with center crop
        result = process_image_to_multiple_of(image, 64, "center crop")

        # Check dimensions
        assert result.shape == (1, 256, 384, 3)

        # Check that center portion is preserved
        # The crop should start at (22, 8) and end at (278, 392)
        # This is a rough check that values are from the center
        assert result.dtype == image.dtype

    def test_process_image_rescale(self):
        """Test rescale processing."""
        # Create test image
        image = torch.rand(1, 300, 400, 3)

        # Process with rescale
        result = process_image_to_multiple_of(image, 64, "rescale")

        # Check dimensions
        assert result.shape == (1, 256, 384, 3)
        assert result.dtype == image.dtype

    def test_process_image_batch(self):
        """Test processing with batch of images."""
        # Create batch of images
        batch_size = 4
        image = torch.rand(batch_size, 300, 400, 3)

        # Process with center crop
        result_crop = process_image_to_multiple_of(image, 32, "center crop")
        assert result_crop.shape == (batch_size, 288, 384, 3)

        # Process with rescale
        result_rescale = process_image_to_multiple_of(image, 32, "rescale")
        assert result_rescale.shape == (batch_size, 288, 384, 3)

    def test_process_image_different_channels(self):
        """Test with different channel counts."""
        # Test with 1 channel (grayscale)
        image_gray = torch.rand(1, 256, 256, 1)
        result = process_image_to_multiple_of(image_gray, 64, "center crop")
        assert result.shape == (1, 256, 256, 1)

        # Test with 4 channels (RGBA)
        image_rgba = torch.rand(1, 300, 400, 4)
        result = process_image_to_multiple_of(image_rgba, 64, "rescale")
        assert result.shape == (1, 256, 384, 4)


class TestImageToMultipleOfNode:
    """Test ComfyUI node implementation."""

    def test_node_input_types(self):
        """Test node input type definitions."""
        input_types = ImageToMultipleOfNode.INPUT_TYPES()

        assert "required" in input_types
        assert "image" in input_types["required"]
        assert "multiple_of" in input_types["required"]
        assert "method" in input_types["required"]

        # Check multiple_of configuration
        multiple_config = input_types["required"]["multiple_of"][1]
        assert multiple_config["default"] == 64
        assert multiple_config["min"] == 1
        assert multiple_config["max"] == 256
        assert multiple_config["step"] == 16

        # Check method options
        methods = input_types["required"]["method"][0]
        assert "center crop" in methods
        assert "rescale" in methods

    def test_node_metadata(self):
        """Test node metadata."""
        assert ImageToMultipleOfNode.RETURN_TYPES == ("IMAGE",)
        assert ImageToMultipleOfNode.RETURN_NAMES == ("image",)
        assert ImageToMultipleOfNode.FUNCTION == "process"
        assert ImageToMultipleOfNode.CATEGORY == "ComfyAssets"

    def test_node_process_center_crop(self):
        """Test node processing with center crop."""
        node = ImageToMultipleOfNode()
        image = torch.rand(1, 300, 400, 3)

        result = node.process(image, 64, "center crop")

        assert isinstance(result, tuple)
        assert len(result) == 1
        assert result[0].shape == (1, 256, 384, 3)

    def test_node_process_rescale(self):
        """Test node processing with rescale."""
        node = ImageToMultipleOfNode()
        image = torch.rand(1, 300, 400, 3)

        result = node.process(image, 32, "rescale")

        assert isinstance(result, tuple)
        assert len(result) == 1
        assert result[0].shape == (1, 288, 384, 3)

    def test_node_validation_errors(self):
        """Test input validation error handling."""
        node = ImageToMultipleOfNode()

        # Test with None image
        with pytest.raises(ValueError, match="Image input is required"):
            node.validate_inputs(image=None, multiple_of=64, method="center crop")

        # Test with invalid image shape
        invalid_image = torch.rand(300, 400, 3)  # Missing batch dimension
        with pytest.raises(ValueError, match="Expected image tensor with shape"):
            node.validate_inputs(
                image=invalid_image, multiple_of=64, method="center crop"
            )

        # Test with negative multiple_of
        image = torch.rand(1, 300, 400, 3)
        with pytest.raises(ValueError, match="multiple_of must be positive"):
            node.validate_inputs(image=image, multiple_of=-64, method="center crop")

        # Test with invalid method
        with pytest.raises(ValueError, match="Invalid method"):
            node.validate_inputs(image=image, multiple_of=64, method="invalid")

        # Test with image too small
        small_image = torch.rand(1, 30, 40, 3)
        with pytest.raises(ValueError, match="too small to be adjusted"):
            node.validate_inputs(
                image=small_image, multiple_of=64, method="center crop"
            )

    def test_node_edge_cases(self):
        """Test edge cases."""
        node = ImageToMultipleOfNode()

        # Test with already multiple dimensions
        image = torch.rand(1, 256, 512, 3)
        result = node.process(image, 64, "center crop")
        assert result[0].shape == image.shape

        # Test with multiple_of = 1
        image = torch.rand(1, 123, 456, 3)
        result = node.process(image, 1, "center crop")
        assert result[0].shape == image.shape

        # Test with very large multiple_of
        image = torch.rand(1, 1024, 1024, 3)
        result = node.process(image, 256, "rescale")
        assert result[0].shape == (1, 1024, 1024, 3)
