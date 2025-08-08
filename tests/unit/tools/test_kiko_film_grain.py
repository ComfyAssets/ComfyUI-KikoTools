import pytest
import torch
import numpy as np
from unittest.mock import MagicMock

from kikotools.tools.kiko_film_grain.logic import (
    apply_film_grain,
    generate_grain_texture,
    rgb_to_ycbcr,
    ycbcr_to_rgb,
    apply_gaussian_blur,
)


class TestColorSpaceConversion:
    def test_rgb_to_ycbcr_conversion(self):
        rgb = torch.tensor([[[[1.0, 0.0, 0.0]]]])  # Pure red
        ycbcr = rgb_to_ycbcr(rgb)

        assert ycbcr.shape == rgb.shape
        assert 0.0 <= ycbcr[0, 0, 0, 0] <= 1.0  # Y channel

    def test_ycbcr_to_rgb_conversion(self):
        ycbcr = torch.tensor([[[[0.5, 0.0, 0.0]]]])
        rgb = ycbcr_to_rgb(ycbcr)

        assert rgb.shape == ycbcr.shape
        assert rgb.min() >= 0.0
        assert rgb.max() <= 1.0

    def test_rgb_ycbcr_round_trip(self):
        original = torch.rand(1, 4, 4, 3)
        converted = ycbcr_to_rgb(rgb_to_ycbcr(original))

        # Should be approximately equal after round trip
        assert torch.allclose(original, converted, atol=0.01)


class TestGaussianBlur:
    def test_apply_gaussian_blur_no_blur(self):
        image = torch.rand(1, 10, 10, 3)
        blurred = apply_gaussian_blur(image, kernel_size=1)

        # Kernel size 1 should not blur
        assert torch.allclose(image, blurred, atol=0.001)

    def test_apply_gaussian_blur_with_blur(self):
        # Create sharp edge image
        image = torch.zeros(1, 10, 10, 1)
        image[:, :5, :, :] = 1.0

        blurred = apply_gaussian_blur(image, kernel_size=3)

        # Edge should be smoothed
        edge_original = image[0, 4:6, 5, 0]
        edge_blurred = blurred[0, 4:6, 5, 0]
        # White side near edge should be darker due to blur
        assert edge_blurred[0] < edge_original[0]
        # Black side near edge should be lighter due to blur
        assert edge_blurred[1] > edge_original[1]

    def test_apply_gaussian_blur_preserves_shape(self):
        for shape in [(1, 32, 32, 3), (2, 64, 128, 1), (4, 16, 16, 3)]:
            image = torch.rand(*shape)
            blurred = apply_gaussian_blur(image, kernel_size=5)
            assert blurred.shape == image.shape


class TestGrainGeneration:
    def test_generate_grain_texture_shape(self):
        batch_size = 2
        height = 64
        width = 128
        scale = 2.0

        grain = generate_grain_texture(batch_size, height, width, scale, seed=42)

        expected_height = int(height / scale)
        expected_width = int(width / scale)
        assert grain.shape == (batch_size, expected_height, expected_width, 3)

    def test_generate_grain_texture_deterministic(self):
        grain1 = generate_grain_texture(1, 32, 32, 1.0, seed=123)
        grain2 = generate_grain_texture(1, 32, 32, 1.0, seed=123)

        assert torch.allclose(grain1, grain2)

    def test_generate_grain_texture_different_seeds(self):
        grain1 = generate_grain_texture(1, 32, 32, 1.0, seed=123)
        grain2 = generate_grain_texture(1, 32, 32, 1.0, seed=456)

        assert not torch.allclose(grain1, grain2)

    def test_generate_grain_texture_scale_factor(self):
        height, width = 64, 64
        grain_1x = generate_grain_texture(1, height, width, 1.0, seed=42)
        grain_2x = generate_grain_texture(1, height, width, 2.0, seed=42)

        assert grain_1x.shape[1] == height
        assert grain_2x.shape[1] == height // 2


class TestFilmGrainApplication:
    def test_apply_film_grain_no_effect(self):
        image = torch.rand(1, 32, 32, 3)

        # Zero strength should have no effect
        result = apply_film_grain(
            image, scale=1.0, strength=0.0, saturation=1.0, toe=0.0, seed=42
        )

        assert torch.allclose(image, result, atol=0.001)

    def test_apply_film_grain_with_strength(self):
        image = torch.ones(1, 32, 32, 3) * 0.5

        result = apply_film_grain(
            image, scale=1.0, strength=1.0, saturation=1.0, toe=0.0, seed=42
        )

        # Should add variation
        assert not torch.allclose(image, result)
        # Should remain in valid range
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_apply_film_grain_saturation_effect(self):
        image = torch.ones(1, 32, 32, 3) * 0.5

        # Full saturation
        result_saturated = apply_film_grain(
            image, scale=1.0, strength=1.0, saturation=1.0, toe=0.0, seed=42
        )

        # No saturation (monochrome grain)
        result_desaturated = apply_film_grain(
            image, scale=1.0, strength=1.0, saturation=0.0, toe=0.0, seed=42
        )

        # Calculate color variance
        var_saturated = torch.var(result_saturated, dim=-1).mean()
        var_desaturated = torch.var(result_desaturated, dim=-1).mean()

        # Desaturated should have less color variance
        assert var_desaturated < var_saturated

    def test_apply_film_grain_toe_effect(self):
        image = torch.ones(1, 32, 32, 3) * 0.5

        # No toe
        result_no_toe = apply_film_grain(
            image, scale=1.0, strength=0.5, saturation=1.0, toe=0.0, seed=42
        )

        # With toe (lifts blacks)
        result_with_toe = apply_film_grain(
            image, scale=1.0, strength=0.5, saturation=1.0, toe=0.2, seed=42
        )

        # Toe should generally lift the overall brightness
        assert result_with_toe.mean() > result_no_toe.mean()

    def test_apply_film_grain_batch_processing(self):
        batch_size = 4
        image = torch.rand(batch_size, 32, 32, 3)

        result = apply_film_grain(
            image, scale=1.5, strength=0.5, saturation=0.8, toe=0.1, seed=42
        )

        assert result.shape == image.shape

        # Each image in batch should be different (due to grain)
        for i in range(batch_size - 1):
            assert not torch.allclose(result[i], result[i + 1])

    def test_apply_film_grain_preserves_alpha(self):
        # Image with alpha channel
        image = torch.rand(1, 32, 32, 4)
        original_alpha = image[:, :, :, 3:4].clone()

        result = apply_film_grain(
            image, scale=1.0, strength=1.0, saturation=1.0, toe=0.0, seed=42
        )

        # Alpha channel should be unchanged
        assert torch.allclose(original_alpha, result[:, :, :, 3:4])

    def test_apply_film_grain_scale_interpolation(self):
        image = torch.ones(1, 64, 64, 3) * 0.5

        # Different scales should produce different sized grain
        result_fine = apply_film_grain(
            image, scale=0.5, strength=0.5, saturation=1.0, toe=0.0, seed=42
        )

        result_coarse = apply_film_grain(
            image, scale=2.0, strength=0.5, saturation=1.0, toe=0.0, seed=42
        )

        # Compute local variance to measure grain size
        def compute_local_variance(img, window=3):
            unfold = torch.nn.Unfold(kernel_size=window, stride=1, padding=1)
            img_reshaped = img.permute(0, 3, 1, 2)
            patches = unfold(img_reshaped)
            var = torch.var(patches, dim=1)
            return var.mean()

        var_fine = compute_local_variance(result_fine)
        var_coarse = compute_local_variance(result_coarse)

        # Fine grain should have higher local variance than coarse grain
        # (more rapid changes)
        assert var_fine != var_coarse  # They should be different


class TestEdgeCases:
    def test_handles_empty_batch(self):
        image = torch.rand(0, 32, 32, 3)
        result = apply_film_grain(
            image, scale=1.0, strength=0.5, saturation=1.0, toe=0.0, seed=42
        )
        assert result.shape == image.shape

    def test_handles_single_pixel(self):
        image = torch.rand(1, 1, 1, 3)
        result = apply_film_grain(
            image, scale=1.0, strength=0.5, saturation=1.0, toe=0.0, seed=42
        )
        assert result.shape == image.shape
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_handles_extreme_parameters(self):
        image = torch.rand(1, 32, 32, 3)

        # Maximum strength
        result = apply_film_grain(
            image, scale=2.0, strength=10.0, saturation=2.0, toe=0.5, seed=42
        )
        assert result.min() >= 0.0
        assert result.max() <= 1.0

        # Minimum values
        result = apply_film_grain(
            image, scale=0.25, strength=0.0, saturation=0.0, toe=-0.2, seed=42
        )
        assert result.min() >= 0.0
        assert result.max() <= 1.0
