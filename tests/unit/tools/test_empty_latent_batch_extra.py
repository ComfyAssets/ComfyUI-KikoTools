"""Additional behavioural tests for EmptyLatentBatchNode."""

import pytest

from kikotools.tools.empty_latent_batch.node import EmptyLatentBatchNode
from kikotools.tools.width_height_selector.presets import PRESET_METADATA


@pytest.fixture
def node():
    return EmptyLatentBatchNode()


class TestPresetNameExtraction:
    def test_custom(self, node):
        assert node._extract_preset_name("custom") == "custom"

    def test_plain_preset(self, node):
        assert node._extract_preset_name("1024×1024") == "1024×1024"

    def test_formatted_option_from_input_types_roundtrips(self, node):
        options = EmptyLatentBatchNode.INPUT_TYPES()["required"]["preset"][0]
        assert options[0] == "custom"
        for option in options[1:]:
            name = node._extract_preset_name(option)
            assert name in PRESET_METADATA

    def test_unknown_formatted_falls_back_to_custom(self, node):
        assert node._extract_preset_name("nope - 1:1 - X") == "custom"
        assert node._extract_preset_name("garbage") == "custom"


class TestCreateEmptyLatent:
    def test_formatted_preset_overrides_width_height(self, node):
        option = next(
            o
            for o in EmptyLatentBatchNode.INPUT_TYPES()["required"]["preset"][0]
            if o.startswith("832×1216")
        )
        latent, w, h, b = node.create_empty_latent(option, 64, 64, 2)
        assert (w, h, b) == (832, 1216, 2)
        assert latent["samples"].shape == (2, 4, 152, 104)

    def test_custom_dimensions_rounded_and_reported(self, node):
        latent, w, h, _ = node.create_empty_latent("custom", 1030, 1030, 1)
        assert (w, h) == (1032, 1032)
        assert latent["samples"].shape == (1, 4, 129, 129)

    def test_latent_is_zeros(self, node):
        latent, *_ = node.create_empty_latent("custom", 64, 64, 1)
        assert float(latent["samples"].abs().sum()) == 0.0

    def test_out_of_range_dimensions_are_clamped(self, node):
        _, w, h, _ = node.create_empty_latent("custom", 1, 99999, 1)
        assert (w, h) == (64, 8192)

    @pytest.mark.parametrize("batch", [0, -3])
    def test_non_positive_batch_raises(self, node, batch):
        with pytest.raises(ValueError, match="Batch size must be positive"):
            node.create_empty_latent("custom", 512, 512, batch)

    def test_large_batch_is_allowed(self, node):
        latent, _, _, b = node.create_empty_latent("custom", 64, 64, 65)
        assert b == 65 and latent["samples"].shape[0] == 65


class TestValidateInputs:
    def test_valid(self, node):
        assert node.validate_inputs("custom", 512, 512, 4) is True

    def test_valid_formatted_preset(self, node):
        assert node.validate_inputs("1024×1024 - 1:1 (1.0MP) - SDXL", 0, 0, 1) is True

    @pytest.mark.parametrize("batch", [0, 65])
    def test_batch_bounds(self, node, batch):
        assert node.validate_inputs("custom", 512, 512, batch) is False

    def test_bad_preset_parses_as_custom_so_uses_dimensions(self, node):
        assert node.validate_inputs("garbage", 512, 512, 1) is True

    def test_custom_with_zero_dimensions_is_clamped_valid(self, node):
        # sanitisation clamps 0 up to the 64 minimum, so this is accepted
        assert node.validate_inputs("custom", 0, 0, 1) is True


class TestInfoHelpers:
    def test_latent_info(self, node):
        info = node.get_latent_info(64, 64, 1)
        assert "1 × 4 × 8 × 8" in info and "64×64" in info

    def test_latent_info_sanitises(self, node):
        assert "1032×1032" in node.get_latent_info(1030, 1030, 1)

    @pytest.mark.parametrize(
        "w,h,b,suffix",
        [
            (64, 64, 1, "KB"),  # 1*4*8*8*4 = 1024 bytes -> 1.0 KB
            (1024, 1024, 1, "KB"),  # 262144 bytes = 256 KB
            (1024, 1024, 8, "MB"),
            (8192, 8192, 64, "GB"),
        ],
    )
    def test_memory_estimate_units(self, node, w, h, b, suffix):
        assert node.get_memory_estimate(w, h, b).endswith(suffix)

    def test_memory_estimate_value(self, node):
        assert node.get_memory_estimate(1024, 1024, 1) == "256.0 KB"
        assert node.get_memory_estimate(1024, 1024, 8) == "2.0 MB"

    def test_memory_estimate_bytes_branch(self, node, monkeypatch):
        from kikotools.tools.empty_latent_batch import node as mod

        monkeypatch.setattr(mod, "sanitize_dimensions", lambda w, h: (8, 8))
        assert node.get_memory_estimate(8, 8, 1) == "16 bytes"


class TestDunder:
    def test_str_and_repr(self, node):
        assert str(node) == "EmptyLatentBatchNode"
        assert "EmptyLatentBatchNode(" in repr(node)
