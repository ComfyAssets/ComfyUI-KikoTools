"""Tests for Empty Latent Batch node and logic."""

import pytest
import torch

from kikotools.tools.empty_latent_batch.node import EmptyLatentBatchNode
from kikotools.tools.empty_latent_batch.logic import (
    create_empty_latent_batch,
    validate_dimensions,
    sanitize_dimensions,
)


class TestEmptyLatentBatchLogic:
    """Test the logic functions for empty latent batch creation."""

    def test_create_empty_latent_batch_basic(self):
        """Test basic empty latent creation."""
        result = create_empty_latent_batch(512, 512, 1)

        assert "samples" in result
        samples = result["samples"]
        assert isinstance(samples, torch.Tensor)
        assert samples.shape == (1, 4, 64, 64)  # 512/8 = 64
        assert torch.all(samples == 0)  # Should be all zeros

    def test_create_empty_latent_batch_with_batch_size(self):
        """Test empty latent creation with larger batch size."""
        batch_size = 4
        result = create_empty_latent_batch(1024, 768, batch_size)

        assert "samples" in result
        samples = result["samples"]
        assert isinstance(samples, torch.Tensor)
        assert samples.shape == (4, 4, 96, 128)  # 768/8=96, 1024/8=128
        assert torch.all(samples == 0)

    def test_create_empty_latent_batch_invalid_dimensions(self):
        """Test error handling for invalid dimensions."""
        with pytest.raises(ValueError, match="Width and height must be positive"):
            create_empty_latent_batch(0, 512, 1)

        with pytest.raises(ValueError, match="Width and height must be positive"):
            create_empty_latent_batch(512, -100, 1)

    def test_create_empty_latent_batch_not_divisible_by_8(self):
        """Test error handling for dimensions not divisible by 8."""
        with pytest.raises(ValueError, match="must be divisible by 8"):
            create_empty_latent_batch(513, 512, 1)

        with pytest.raises(ValueError, match="must be divisible by 8"):
            create_empty_latent_batch(512, 515, 1)

    def test_create_empty_latent_batch_invalid_batch_size(self):
        """Test error handling for invalid batch size."""
        with pytest.raises(ValueError, match="Batch size must be positive"):
            create_empty_latent_batch(512, 512, 0)

        with pytest.raises(ValueError, match="Batch size must be positive"):
            create_empty_latent_batch(512, 512, -1)

    def test_validate_dimensions_valid(self):
        """Test dimension validation with valid inputs."""
        assert validate_dimensions(512, 512) is True
        assert validate_dimensions(1024, 768) is True
        assert validate_dimensions(64, 64) is True  # Minimum size
        assert validate_dimensions(8192, 8192) is True  # Maximum size

    def test_validate_dimensions_invalid(self):
        """Test dimension validation with invalid inputs."""
        assert validate_dimensions(0, 512) is False  # Zero dimension
        assert validate_dimensions(512, -100) is False  # Negative dimension
        assert validate_dimensions(513, 512) is False  # Not divisible by 8
        assert validate_dimensions(32, 32) is False  # Too small
        assert validate_dimensions(8200, 8200) is False  # Too large

    def test_sanitize_dimensions_basic(self):
        """Test basic dimension sanitization."""
        width, height = sanitize_dimensions(512, 512)
        assert width == 512
        assert height == 512

    def test_sanitize_dimensions_not_divisible_by_8(self):
        """Test sanitization of dimensions not divisible by 8."""
        width, height = sanitize_dimensions(513, 515)
        assert width == 520  # Rounds up to nearest multiple of 8
        assert height == 520

        width, height = sanitize_dimensions(517, 519)
        assert width == 520  # Rounds up to nearest multiple of 8
        assert height == 520

    def test_sanitize_dimensions_too_small(self):
        """Test sanitization of dimensions that are too small."""
        width, height = sanitize_dimensions(32, 16)
        assert width == 64  # Minimum size
        assert height == 64

    def test_sanitize_dimensions_too_large(self):
        """Test sanitization of dimensions that are too large."""
        width, height = sanitize_dimensions(10000, 9000)
        assert width == 8192  # Maximum size
        assert height == 8192


class TestEmptyLatentBatchNode:
    """Test the EmptyLatentBatchNode ComfyUI node."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = EmptyLatentBatchNode()

    def test_input_types_structure(self):
        """Test that INPUT_TYPES returns proper structure."""
        input_types = EmptyLatentBatchNode.INPUT_TYPES()

        assert "required" in input_types
        required = input_types["required"]

        assert "width" in required
        assert "height" in required
        assert "batch_size" in required

        # Check width parameter
        width_spec = required["width"]
        assert width_spec[0] == "INT"
        assert width_spec[1]["default"] == 1024
        assert width_spec[1]["min"] == 64
        assert width_spec[1]["max"] == 8192
        assert width_spec[1]["step"] == 8

    def test_node_attributes(self):
        """Test node class attributes."""
        assert EmptyLatentBatchNode.RETURN_TYPES == ("LATENT", "INT", "INT", "INT")
        assert EmptyLatentBatchNode.RETURN_NAMES == (
            "latent",
            "width",
            "height",
            "batch_size",
        )
        assert EmptyLatentBatchNode.FUNCTION == "create_empty_latent"
        assert EmptyLatentBatchNode.CATEGORY == "🫶 ComfyAssets/📦 Latents"

    def test_create_empty_latent_basic(self):
        """Test basic empty latent creation through node."""
        result = self.node.create_empty_latent("custom", 512, 512, 1)

        assert isinstance(result, tuple)
        assert len(result) == 4  # Returns (latent, width, height, batch_size)

        latent_dict, width, height, batch_size = result
        assert isinstance(latent_dict, dict)
        assert "samples" in latent_dict
        assert width == 512
        assert height == 512
        assert batch_size == 1

        samples = latent_dict["samples"]
        assert isinstance(samples, torch.Tensor)
        assert samples.shape == (1, 4, 64, 64)

    def test_create_empty_latent_with_batch(self):
        """Test empty latent creation with batch size."""
        input_batch_size = 3
        result = self.node.create_empty_latent("custom", 1024, 768, input_batch_size)

        latent_dict, width, height, batch_size = result
        assert width == 1024
        assert height == 768
        assert batch_size == 3
        samples = latent_dict["samples"]
        assert samples.shape == (3, 4, 96, 128)  # batch=3, 768/8=96, 1024/8=128

    def test_create_empty_latent_dimension_adjustment(self):
        """Test that dimensions are adjusted when not divisible by 8."""
        # Input dimensions not divisible by 8
        result = self.node.create_empty_latent("custom", 513, 515, 1)

        latent_dict, width, height, batch_size = result
        # Dimensions should be rounded UP to nearest multiple of 8
        assert width == 520  # 513 -> 520
        assert height == 520  # 515 -> 520
        assert batch_size == 1
        samples = latent_dict["samples"]
        # Should be adjusted to 520x520 -> 65x65 latent
        assert samples.shape == (1, 4, 65, 65)

    def test_validate_inputs_valid(self):
        """Test input validation with valid parameters."""
        assert self.node.validate_inputs("custom", 512, 512, 1) is True
        assert self.node.validate_inputs("custom", 1024, 768, 4) is True

    def test_validate_inputs_invalid_batch_size(self):
        """Test input validation with invalid batch size."""
        assert self.node.validate_inputs("custom", 512, 512, 0) is False
        assert self.node.validate_inputs("custom", 512, 512, 100) is False  # Too large

    def test_get_latent_info(self):
        """Test latent info generation."""
        info = self.node.get_latent_info(512, 512, 2)
        assert "Empty latent batch" in info
        assert "2 × 4 × 64 × 64" in info
        assert "512×512" in info

    def test_get_memory_estimate(self):
        """Test memory estimation."""
        estimate = self.node.get_memory_estimate(512, 512, 1)
        assert "KB" in estimate or "MB" in estimate

        # Larger batch should show larger estimate
        large_estimate = self.node.get_memory_estimate(1024, 1024, 8)
        assert "MB" in large_estimate

    def test_node_registration_mappings(self):
        """Test that node registration mappings are properly defined."""
        from kikotools.tools.empty_latent_batch.node import (
            NODE_CLASS_MAPPINGS,
            NODE_DISPLAY_NAME_MAPPINGS,
        )

        assert "EmptyLatentBatch" in NODE_CLASS_MAPPINGS
        assert NODE_CLASS_MAPPINGS["EmptyLatentBatch"] == EmptyLatentBatchNode

        assert "EmptyLatentBatch" in NODE_DISPLAY_NAME_MAPPINGS
        assert NODE_DISPLAY_NAME_MAPPINGS["EmptyLatentBatch"] == "Empty Latent Batch"

    def test_node_inheritance(self):
        """Test that node properly inherits from base class."""
        from kikotools.base.base_node import ComfyAssetsBaseNode

        assert isinstance(self.node, ComfyAssetsBaseNode)
        assert hasattr(self.node, "handle_error")
        assert hasattr(self.node, "log_info")
        assert hasattr(self.node, "validate_inputs")
