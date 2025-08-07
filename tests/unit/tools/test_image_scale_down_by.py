"""Unit tests for ImageScaleDownBy tool."""

import pytest
import torch
from kikotools.tools.image_scale_down_by.logic import scale_down_image
from kikotools.tools.image_scale_down_by.node import ImageScaleDownByNode


class TestImageScaleDownByLogic:
    """Test the core logic for scaling down images."""

    def test_scale_down_by_half(self):
        """Test scaling down an image by 0.5."""
        # Create a test image (batch=1, height=512, width=512, channels=3)
        image = torch.randn(1, 512, 512, 3)
        scale_by = 0.5

        result = scale_down_image(image, scale_by)

        assert result.shape == (1, 256, 256, 3)

    def test_scale_down_by_quarter(self):
        """Test scaling down an image by 0.25."""
        image = torch.randn(1, 1024, 768, 3)
        scale_by = 0.25

        result = scale_down_image(image, scale_by)

        assert result.shape == (1, 256, 192, 3)

    def test_scale_down_by_custom_factor(self):
        """Test scaling down by a custom factor."""
        image = torch.randn(1, 800, 600, 3)
        scale_by = 0.75

        result = scale_down_image(image, scale_by)

        assert result.shape == (1, 600, 450, 3)

    def test_scale_down_maintains_batch_size(self):
        """Test that batch size is maintained."""
        # Test with batch size > 1
        image = torch.randn(4, 512, 512, 3)
        scale_by = 0.5

        result = scale_down_image(image, scale_by)

        assert result.shape == (4, 256, 256, 3)

    def test_scale_by_one_returns_same_size(self):
        """Test that scale_by=1.0 returns the same size."""
        image = torch.randn(1, 512, 512, 3)
        scale_by = 1.0

        result = scale_down_image(image, scale_by)

        assert result.shape == image.shape

    def test_non_square_image(self):
        """Test scaling non-square images."""
        image = torch.randn(1, 720, 1280, 3)
        scale_by = 0.5

        result = scale_down_image(image, scale_by)

        assert result.shape == (1, 360, 640, 3)

    def test_small_scale_factor(self):
        """Test with very small scale factor."""
        image = torch.randn(1, 1000, 1000, 3)
        scale_by = 0.01

        result = scale_down_image(image, scale_by)

        assert result.shape == (1, 10, 10, 3)


class TestImageScaleDownByNode:
    """Test the ComfyUI node implementation."""

    @pytest.fixture
    def node(self):
        """Create a node instance."""
        return ImageScaleDownByNode()

    def test_input_types(self):
        """Test that INPUT_TYPES is properly defined."""
        input_types = ImageScaleDownByNode.INPUT_TYPES()

        assert "required" in input_types
        assert "images" in input_types["required"]
        assert input_types["required"]["images"] == ("IMAGE",)
        assert "scale_by" in input_types["required"]

        # Check scale_by configuration
        scale_config = input_types["required"]["scale_by"]
        assert scale_config[0] == "FLOAT"
        assert scale_config[1]["default"] == 0.5
        assert scale_config[1]["min"] == 0.01
        assert scale_config[1]["max"] == 1.0
        assert scale_config[1]["step"] == 0.01

    def test_return_types(self):
        """Test that return types are properly defined."""
        assert ImageScaleDownByNode.RETURN_TYPES == ("IMAGE",)
        assert ImageScaleDownByNode.RETURN_NAMES == ("images",)
        assert ImageScaleDownByNode.FUNCTION == "scale_down"

    def test_scale_down_execution(self, node):
        """Test the scale_down method."""
        images = torch.randn(1, 512, 512, 3)
        scale_by = 0.5

        result = node.scale_down(images, scale_by)

        assert isinstance(result, tuple)
        assert len(result) == 1
        assert result[0].shape == (1, 256, 256, 3)

    def test_input_validation_no_images(self, node):
        """Test validation with missing images."""
        with pytest.raises(ValueError, match="Images input is required"):
            node.validate_inputs(images=None, scale_by=0.5)

    def test_input_validation_invalid_tensor_shape(self, node):
        """Test validation with invalid tensor shape."""
        invalid_image = torch.randn(512, 512, 3)  # Missing batch dimension

        with pytest.raises(ValueError, match="Expected image tensor with shape"):
            node.validate_inputs(images=invalid_image, scale_by=0.5)

    def test_input_validation_scale_too_small(self, node):
        """Test validation with scale_by too small."""
        images = torch.randn(1, 512, 512, 3)

        with pytest.raises(ValueError, match="scale_by must be between"):
            node.validate_inputs(images=images, scale_by=0.0)

    def test_input_validation_scale_too_large(self, node):
        """Test validation with scale_by too large."""
        images = torch.randn(1, 512, 512, 3)

        with pytest.raises(ValueError, match="scale_by must be between"):
            node.validate_inputs(images=images, scale_by=1.5)

    def test_category_is_comfyassets(self):
        """Test that the node is in the ComfyAssets category."""
        assert ImageScaleDownByNode.CATEGORY == "ComfyAssets/🖼️ Resolution"

    def test_scale_down_with_batch(self, node):
        """Test scaling down with batch of images."""
        images = torch.randn(3, 640, 480, 3)
        scale_by = 0.25

        result = node.scale_down(images, scale_by)

        assert result[0].shape == (3, 160, 120, 3)

    def test_error_handling(self, node):
        """Test that errors are properly handled."""
        from unittest.mock import patch

        # Mock the scale_down_image function to raise an exception
        with patch(
            "kikotools.tools.image_scale_down_by.node.scale_down_image",
            side_effect=RuntimeError("Test error"),
        ):
            images = torch.randn(1, 512, 512, 3)

            with pytest.raises(ValueError, match="Failed to scale down images"):
                node.scale_down(images, 0.5)
