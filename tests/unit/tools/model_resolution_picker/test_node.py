import asyncio
import json
import logging

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


def test_execution_rounds_to_family_step_and_marks_latent():
    latent, w, h = ModelResolutionPickerNode().create("HunyuanImage 2.1", 70, 1000, 2)
    assert (w, h) == (64, 992)
    assert latent["samples"].shape == (2, 4, 124, 8)
    assert latent["downscale_ratio_spacial"] == 8


def test_exact_sizes_pass_through():
    _, w, h = ModelResolutionPickerNode().create("Flux.2 / Klein / MOSS", 1248, 832, 1)
    assert (w, h) == (1248, 832)


def test_unknown_label_keeps_size_and_warns(caplog):
    with caplog.at_level(logging.WARNING):
        _, w, h = ModelResolutionPickerNode().create("Renamed Family", 1000, 1000, 1)
    assert (w, h) == (1000, 1000)
    assert "Renamed Family" in caplog.text


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
