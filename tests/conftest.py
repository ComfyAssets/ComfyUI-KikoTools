"""
pytest configuration and fixtures for ComfyUI-KikoTools testing
Provides mock ComfyUI environments and test data
"""

import pytest
import torch
import numpy as np
from typing import Dict, Any
from unittest.mock import MagicMock


@pytest.fixture
def mock_image_tensor():
    """
    Create a mock IMAGE tensor in ComfyUI format
    Shape: [batch, height, width, channels]
    """
    # Standard SDXL portrait format: 832x1216
    return torch.randn(1, 1216, 832, 3)


@pytest.fixture
def mock_image_tensor_square():
    """
    Create a mock square IMAGE tensor
    Shape: [batch, height, width, channels] - 1024x1024
    """
    return torch.randn(1, 1024, 1024, 3)


@pytest.fixture
def mock_latent_tensor():
    """
    Create a mock LATENT tensor in ComfyUI format
    ComfyUI latents are dictionaries with 'samples' key
    Latent dimensions are 1/8 of image dimensions
    Shape: [batch, channels, height/8, width/8]
    """
    # SDXL portrait latent: 104x152 (832/8 x 1216/8)
    samples = torch.randn(1, 4, 152, 104)
    return {"samples": samples}


@pytest.fixture
def mock_latent_tensor_square():
    """
    Create a mock square LATENT tensor
    Shape: [batch, channels, height/8, width/8] - 128x128 (1024/8)
    """
    samples = torch.randn(1, 4, 128, 128)
    return {"samples": samples}


@pytest.fixture
def sample_scale_factors():
    """
    Common scale factors for testing
    """
    return [1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0]


@pytest.fixture
def expected_sdxl_resolutions():
    """
    Expected SDXL-optimized resolutions for testing validation
    """
    return {
        # Square
        "1024x1024": (1024, 1024),
        # Portrait
        "896x1152": (896, 1152),
        "832x1216": (832, 1216),
        "768x1344": (768, 1344),
        "640x1536": (640, 1536),
        # Landscape
        "1152x896": (1152, 896),
        "1216x832": (1216, 832),
        "1344x768": (1344, 768),
        "1536x640": (1536, 640),
    }


@pytest.fixture
def mock_comfyui_node():
    """
    Mock ComfyUI node structure for testing
    """
    mock_node = MagicMock()
    mock_node.INPUT_TYPES = MagicMock(return_value={"required": {}, "optional": {}})
    mock_node.RETURN_TYPES = ("INT", "INT")
    mock_node.RETURN_NAMES = ("width", "height")
    mock_node.FUNCTION = "calculate_resolution"
    mock_node.CATEGORY = "ComfyAssets"
    return mock_node


def assert_divisible_by_8(width: int, height: int) -> None:
    """
    Helper function to assert dimensions are divisible by 8
    ComfyUI requirement for proper tensor operations
    """
    assert width % 8 == 0, f"Width {width} must be divisible by 8"
    assert height % 8 == 0, f"Height {height} must be divisible by 8"


def assert_reasonable_dimensions(
    width: int, height: int, min_size: int = 64, max_size: int = 8192
) -> None:
    """
    Helper function to assert dimensions are within reasonable bounds
    """
    assert (
        min_size <= width <= max_size
    ), f"Width {width} out of reasonable range [{min_size}, {max_size}]"
    assert (
        min_size <= height <= max_size
    ), f"Height {height} out of reasonable range [{min_size}, {max_size}]"


# Make helper functions available as pytest fixtures
@pytest.fixture
def assert_div_by_8():
    return assert_divisible_by_8


@pytest.fixture
def assert_reasonable_dims():
    return assert_reasonable_dimensions
