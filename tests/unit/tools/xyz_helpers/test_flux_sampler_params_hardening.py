"""Hardening and node-level tests for Flux Sampler Params."""

import math
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
import torch

from kikotools.tools.xyz_helpers.flux_sampler_params import FluxSamplerParamsNode
from kikotools.tools.xyz_helpers.flux_sampler_params.logic import (
    is_schnell_model,
    parse_seed_string,
    parse_steps_list,
    parse_string_to_list,
    validate_flux_params,
)


def _model(guidance_embed):
    model = Mock()
    model.model.model_config.unet_config = {"guidance_embed": guidance_embed}
    return model


class TestParsing:
    def test_float_list_bad_token_names_field_and_token(self):
        with pytest.raises(ValueError, match=r"guidance.*'x'"):
            parse_string_to_list("1.0, x", field="guidance")

    def test_float_list_alone_bad(self):
        with pytest.raises(ValueError, match="abc"):
            parse_string_to_list("abc")

    def test_float_list_rejects_nan_inf(self):
        with pytest.raises(ValueError):
            parse_string_to_list("nan")
        with pytest.raises(ValueError):
            parse_string_to_list("inf")

    def test_float_list_empty_is_empty(self):
        assert parse_string_to_list("  ") == []
        assert parse_string_to_list("1, ,2") == [1.0, 2.0]

    def test_steps_list_ints(self):
        assert parse_steps_list("20, 30.0") == [20, 30]

    def test_steps_list_rejects_fraction_and_nonpositive(self):
        with pytest.raises(ValueError, match="steps.*20.5"):
            parse_steps_list("20.5")
        with pytest.raises(ValueError, match="steps"):
            parse_steps_list("0")
        with pytest.raises(ValueError, match="steps.*abc"):
            parse_steps_list("abc")

    def test_seed_invalid_token_raises(self):
        with pytest.raises(ValueError, match="12.5"):
            parse_seed_string("1, 12.5")

    def test_seed_question_mark_is_exact_token(self):
        with pytest.raises(ValueError, match="1\\?"):
            parse_seed_string("1?")

    def test_seed_random_and_fixed(self):
        seeds = parse_seed_string("7, ?\n8")
        assert seeds[0] == 7 and seeds[2] == 8 and 0 <= seeds[1] <= 999999

    def test_seed_negative_rejected(self):
        with pytest.raises(ValueError, match="-5"):
            parse_seed_string("-5")

    def test_seed_empty_is_single_random(self):
        seeds = parse_seed_string("  ")
        assert len(seeds) == 1

    def test_validate_raises_naming_field(self):
        with pytest.raises(ValueError, match="denoise"):
            validate_flux_params("20", "3.5", "", "", "oops")
        with pytest.raises(ValueError, match="steps"):
            validate_flux_params("abc", "3.5", "", "", "1.0")


class TestSchnellDetection:
    def test_dev_has_guidance_embed(self):
        assert is_schnell_model(_model(True)) is False

    def test_schnell_lacks_guidance_embed(self):
        assert is_schnell_model(_model(False)) is True

    def test_missing_key_defaults_to_dev(self):
        model = Mock()
        model.model.model_config.unet_config = {}
        assert is_schnell_model(model) is False

    def test_unexpected_objects_default_to_dev(self):
        assert is_schnell_model(Mock()) is False
        assert is_schnell_model(None) is False
        assert is_schnell_model(object()) is False


class TestIsChanged:
    def test_random_seed_is_nan(self):
        assert math.isnan(FluxSamplerParamsNode.IS_CHANGED(seed="1, ?"))

    def test_empty_seed_is_nan(self):
        assert math.isnan(FluxSamplerParamsNode.IS_CHANGED(seed=""))

    def test_fixed_seed_is_stable(self):
        a = FluxSamplerParamsNode.IS_CHANGED(seed="1,2", steps="20")
        b = FluxSamplerParamsNode.IS_CHANGED(seed="1,2", steps="20")
        assert a == b
        assert a != FluxSamplerParamsNode.IS_CHANGED(seed="1,2", steps="30")

    def test_nan_never_equal_so_reruns(self):
        a = FluxSamplerParamsNode.IS_CHANGED(seed="?")
        assert a != a


@pytest.fixture
def comfy_env():
    """Fake ComfyUI modules; sampling returns a tiny latent."""
    samplers = MagicMock()
    samplers.KSampler.SAMPLERS = ["euler", "ddim"]
    samplers.KSampler.SCHEDULERS = ["simple", "normal"]
    custom = MagicMock()
    sample_calls = []

    def sample(noise, guider, sampler, sigmas, latent):
        sample_calls.append(noise)
        return (None, {"samples": torch.zeros(1, 4, 8, 8)})

    custom.SamplerCustomAdvanced.return_value.sample.side_effect = sample
    adv = MagicMock()
    nodes_mod = MagicMock()
    comfy = MagicMock()
    comfy.samplers = samplers
    mods = {
        "comfy": comfy,
        "comfy.samplers": samplers,
        "comfy.model_base": MagicMock(),
        "comfy.model_management": MagicMock(),
        "comfy.utils": MagicMock(),
        "comfy_extras": MagicMock(),
        "comfy_extras.nodes_custom_sampler": custom,
        "comfy_extras.nodes_model_advanced": adv,
        "node_helpers": MagicMock(),
        "nodes": nodes_mod,
    }
    with patch.dict(sys.modules, mods):
        yield {"adv": adv, "nodes": nodes_mod, "calls": sample_calls}


@pytest.fixture
def latent():
    return {"samples": torch.zeros(1, 4, 8, 8)}


def _run(node, model, latent, **over):
    args = dict(
        model=model,
        conditioning={"text": ["p1"], "encoded": ["c1"]},
        latent_image=latent,
        seed="1",
        sampler="euler",
        scheduler="simple",
        steps="10",
        guidance="3.5",
        max_shift="",
        base_shift="",
        denoise="1.0",
    )
    args.update(over)
    return node.process_batch(**args)


class TestProcessBatch:
    def test_happy_path_dev(self, comfy_env, latent):
        out, params = _run(FluxSamplerParamsNode(), _model(True), latent)
        assert len(params) == 1
        assert params[0]["seed"] == 1 and params[0]["steps"] == 10
        assert params[0]["prompt"] == "p1"
        assert params[0]["width"] == 64
        comfy_env["adv"].ModelSamplingFlux.return_value.patch.assert_called_once()
        comfy_env[
            "adv"
        ].ModelSamplingAuraFlow.return_value.patch_aura.assert_not_called()

    def test_schnell_uses_aura_patch_and_zero_max_shift(self, comfy_env, latent):
        _, params = _run(FluxSamplerParamsNode(), _model(False), latent)
        comfy_env[
            "adv"
        ].ModelSamplingAuraFlow.return_value.patch_aura.assert_called_once()
        assert params[0]["max_shift"] == 0.0

    def test_batches_cartesian_product(self, comfy_env, latent):
        out, params = _run(
            FluxSamplerParamsNode(),
            _model(True),
            latent,
            seed="1,2",
            sampler="euler,ddim",
            steps="5,10",
        )
        assert len(params) == 8
        assert out["samples"].shape[0] == 8

    def test_plain_conditioning(self, comfy_env, latent):
        _, params = _run(
            FluxSamplerParamsNode(), _model(True), latent, conditioning="raw"
        )
        assert params[0]["prompt"] is None

    @pytest.mark.parametrize(
        "field,value",
        [
            ("steps", "abc"),
            ("steps", "20,x"),
            ("guidance", "high"),
            ("denoise", "zz"),
            ("seed", "12.5"),
        ],
    )
    def test_bad_input_raises_naming_field(self, comfy_env, latent, field, value):
        with pytest.raises(ValueError, match=value.split(",")[-1]):
            _run(FluxSamplerParamsNode(), _model(True), latent, **{field: value})

    def test_empty_lora_list_raises(self, comfy_env, latent):
        with pytest.raises(ValueError, match="(?i)lora"):
            _run(
                FluxSamplerParamsNode(),
                _model(True),
                latent,
                loras={"loras": [], "strengths": []},
            )

    def test_loras_applied_with_strengths(self, comfy_env, latent):
        loader = comfy_env["nodes"].LoraLoader.return_value
        loader.load_lora.return_value = (Mock(),)
        loras = {
            "loras": ["a.safetensors", "b.safetensors"],
            "strengths": [[0.5, 1.0], [0.7]],
            "batch_info": {"index": 0, "total": 2},
        }
        _, params = _run(FluxSamplerParamsNode(), _model(True), latent, loras=loras)
        assert [(p["lora"], p["lora_strength"]) for p in params] == [
            ("a.safetensors", 0.5),
            ("a.safetensors", 1.0),
            ("b.safetensors", 0.7),
        ]
        assert params[0]["lora_batch"] == "Batch 1/2"
        assert loader.load_lora.call_count == 3

    def test_missing_comfy_modules_raises(self, latent):
        with patch.dict(sys.modules, {"comfy.samplers": None}):
            with pytest.raises(ValueError, match="(?i)not available"):
                _run(FluxSamplerParamsNode(), _model(True), latent)
