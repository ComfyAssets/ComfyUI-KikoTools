"""Tests for Local Image Loader refs helpers (loading and size matching)."""

import pytest
import torch
from PIL import Image

from kikotools.tools.local_image_loader.logic import (
    load_ref_image,
    match_refs_to_first,
)


def _img(h, w, value=0.5):
    return torch.full((1, h, w, 3), value, dtype=torch.float32)


class TestMatchRefsToFirst:
    def test_empty_list_returns_empty_list(self):
        assert match_refs_to_first([]) == []

    def test_single_image_is_unchanged(self):
        image = _img(64, 48)
        result = match_refs_to_first([image])
        assert len(result) == 1
        assert result[0].shape == (1, 64, 48, 3)
        assert torch.equal(result[0], image)

    def test_same_sizes_are_left_untouched(self):
        a, b = _img(32, 32, 0.1), _img(32, 32, 0.9)
        result = match_refs_to_first([a, b])
        assert result[0] is a and result[1] is b

    def test_does_not_mutate_input_list(self):
        images = [_img(32, 32), _img(64, 16)]
        match_refs_to_first(images)
        assert images[1].shape == (1, 64, 16, 3)

    def test_wider_photo_is_cover_cropped_to_canvas(self):
        result = match_refs_to_first([_img(40, 40), _img(40, 120)])
        assert result[1].shape == (1, 40, 40, 3)

    def test_taller_photo_is_cover_cropped_to_canvas(self):
        result = match_refs_to_first([_img(40, 40), _img(120, 40)])
        assert result[1].shape == (1, 40, 40, 3)

    def test_canvas_is_first_image_exact_size_without_rounding(self):
        result = match_refs_to_first([_img(37, 53), _img(100, 100), _img(10, 200)])
        assert all(r.shape == (1, 37, 53, 3) for r in result)

    def test_crop_is_centered(self):
        wide = torch.zeros(1, 20, 60, 3)
        wide[:, :, 20:40, :] = 1.0  # middle third white
        result = match_refs_to_first([_img(20, 20), wide])
        assert result[1].shape == (1, 20, 20, 3)
        assert result[1].min() > 0.99

    def test_values_stay_in_unit_range(self):
        noisy = torch.rand(1, 90, 30, 3)
        noisy[:, ::2] = 1.0
        noisy[:, 1::2] = 0.0
        result = match_refs_to_first([_img(16, 16), noisy])
        assert result[1].min() >= 0.0 and result[1].max() <= 1.0

    @pytest.mark.parametrize(
        "canvas,other",
        [
            ((33, 47), (101, 7)),
            ((1, 1), (5, 3)),
            ((7, 5), (1, 1)),
            ((50, 31), (31, 50)),
        ],
    )
    def test_odd_sizes_never_end_up_off_by_one(self, canvas, other):
        result = match_refs_to_first([_img(*canvas), _img(*other)])
        assert result[1].shape == (1, canvas[0], canvas[1], 3)


class TestLoadRefImage:
    def test_returns_float_rgb_tensor(self, tmp_path):
        path = tmp_path / "a.png"
        Image.new("RGB", (6, 4), (255, 0, 0)).save(path)
        tensor = load_ref_image(str(path))
        assert tensor.shape == (1, 4, 6, 3)
        assert tensor.dtype == torch.float32
        assert tensor[0, 0, 0, 0] == 1.0 and tensor[0, 0, 0, 1] == 0.0

    def test_alpha_is_dropped(self, tmp_path):
        path = tmp_path / "a.png"
        Image.new("RGBA", (3, 3), (0, 255, 0, 10)).save(path)
        assert load_ref_image(str(path)).shape == (1, 3, 3, 3)

    def test_exif_orientation_is_applied(self, tmp_path):
        path = tmp_path / "a.jpg"
        img = Image.new("RGB", (8, 4), (10, 20, 30))
        exif = img.getexif()
        exif[0x0112] = 6  # rotate 90 degrees to display
        img.save(path, exif=exif)
        assert load_ref_image(str(path)).shape == (1, 8, 4, 3)
