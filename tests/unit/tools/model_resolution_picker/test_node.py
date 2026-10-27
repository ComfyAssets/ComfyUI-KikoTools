import asyncio
import json
import logging
from unittest import mock

from kikotools.tools.model_resolution_picker import families
from kikotools.tools.model_resolution_picker.node import (
    ModelResolutionPickerNode,
    get_families,
)


def test_inputs_and_outputs():
    inputs = ModelResolutionPickerNode.INPUT_TYPES()["required"]
    assert inputs["model"][1]["default"] == "SDXL"
    assert "HunyuanImage 2.1" in inputs["model"][0]
    width = inputs["width"][1]
    assert (width["default"], width["min"], width["max"], width["step"]) == (
        1024,
        64,
        8192,
        8,
    )
    assert ModelResolutionPickerNode.RETURN_TYPES == ("LATENT", "INT", "INT")
    assert ModelResolutionPickerNode.CATEGORY == "🫶 ComfyAssets/🖼️ Resolution"


def test_resolution_options_come_from_shipped_families():
    options, config = ModelResolutionPickerNode.INPUT_TYPES()["required"]["resolution"]
    assert options[0] == "custom"
    assert config["default"] == "custom"
    assert "1216×832 - 3:2 (1.0MP)" in options
    assert options[1:] == sorted(set(options[1:]))


def test_resolution_input_sits_between_model_and_width():
    assert list(ModelResolutionPickerNode.INPUT_TYPES()["required"])[:3] == [
        "model",
        "resolution",
        "width",
    ]


def test_resolution_label_overrides_width_height():
    _, w, h = ModelResolutionPickerNode().create(
        "SDXL", "1216×832 - 3:2 (1.0MP)", 1024, 1024, 1
    )
    assert (w, h) == (1216, 832)


def test_custom_uses_width_height():
    _, w, h = ModelResolutionPickerNode().create("SDXL", "custom", 1024, 768, 1)
    assert (w, h) == (1024, 768)


def test_unparseable_resolution_behaves_like_custom():
    _, w, h = ModelResolutionPickerNode().create("SDXL", "stale text", 1024, 768, 1)
    assert (w, h) == (1024, 768)


def test_validate_inputs_accepts_unlisted_resolution():
    assert ModelResolutionPickerNode.VALIDATE_INPUTS("SDXL", "9999×1 - 1:1 (0.0MP)")


def test_execution_rounds_to_family_step_and_marks_latent():
    latent, w, h = ModelResolutionPickerNode().create(
        "HunyuanImage 2.1", "custom", 70, 1000, 2
    )
    assert (w, h) == (64, 992)
    assert latent["samples"].shape == (2, 4, 124, 8)
    assert latent["downscale_ratio_spacial"] == 8


def test_exact_sizes_pass_through():
    _, w, h = ModelResolutionPickerNode().create(
        "Flux.2 / Klein / MOSS", "custom", 1248, 832, 1
    )
    assert (w, h) == (1248, 832)


def test_unknown_label_keeps_size_and_warns(caplog):
    with caplog.at_level(logging.WARNING):
        _, w, h = ModelResolutionPickerNode().create(
            "Renamed Family", "custom", 1003, 1003, 1
        )
    assert (w, h) == (1000, 1000)  # fallback step 8
    assert "Renamed Family" in caplog.text


def test_validate_inputs_accepts_any_label():
    assert ModelResolutionPickerNode.VALIDATE_INPUTS("Renamed Family", "stale") is True


def test_alias_label_resolves_to_its_family():
    sdxl = families.resolve_family("SDXL")
    patched = sdxl._replace(aliases=("SDXL 1.0",))
    others = tuple(f for f in families.FAMILIES if f.label != "SDXL")
    with mock.patch.object(families, "FAMILIES", (patched,) + others):
        assert families.resolve_family("SDXL 1.0").label == "SDXL"
        latent, w, h = ModelResolutionPickerNode().create(
            "SDXL 1.0", "custom", 1216, 832, 1
        )
    assert (w, h) == (1216, 832)
    assert latent["samples"].shape[-2:] == (104, 152)


def test_families_route_returns_payload():
    response = asyncio.run(get_families(None))
    assert response.status == 200
    assert json.loads(response.text)["default"] == "SDXL"


def test_registered_in_kikotools():
    from kikotools import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

    assert NODE_CLASS_MAPPINGS["ModelResolutionPicker"] is ModelResolutionPickerNode
    assert (
        NODE_DISPLAY_NAME_MAPPINGS["ModelResolutionPicker"] == "Model Resolution Picker"
    )
