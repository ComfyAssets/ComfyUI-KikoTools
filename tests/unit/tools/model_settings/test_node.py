"""Tests for the Model Recommended Settings node."""

from contextlib import ExitStack
from unittest.mock import patch

from kikotools.tools.model_settings import ModelRecommendedSettingsNode
from kikotools.tools.model_settings.node import model_paths
from kikotools.tools.sampler_combo.logic import SAMPLERS, SCHEDULERS

NODE = "kikotools.tools.model_settings.node"
SIDECAR = {
    "file_path": "/m/Moss/fast.safetensors",
    "modelDescription": "<p>Settings 8 steps · CFG 1 · ER SDE · Beta</p>",
    "civitai": {
        "images": [
            {"meta": {"steps": 8, "cfgScale": 1, "sampler": "ER SDE"}},
            {"meta": {"steps": 8, "cfgScale": 1, "sampler": "ER SDE"}},
        ]
    },
}


def _run(sidecar=SIDECAR, overrides=None, **kwargs):
    args = dict(
        model_name="Moss/fast.safetensors",
        steps=25,
        cfg=2.5,
        sampler_name="euler",
        scheduler="simple",
        use_model_steps=True,
        use_model_cfg=True,
        use_model_sampler=True,
        use_model_scheduler=True,
    )
    args.update(kwargs)
    with ExitStack() as stack:
        for name, value in (
            ("model_paths", ["/m/Moss/fast.safetensors"]),
            ("lora_manager_sidecar_root", None),
            ("find_sidecar", sidecar),
            ("load_overrides", overrides or {}),
        ):
            stack.enter_context(patch(f"{NODE}.{name}", return_value=value))
        # the unit-test fallback lists lack er_sde and beta
        stack.enter_context(patch(f"{NODE}.SAMPLERS", ["euler", "er_sde", "dpmpp_2m"]))
        stack.enter_context(patch(f"{NODE}.SCHEDULERS", ["simple", "beta", "karras"]))
        return ModelRecommendedSettingsNode().get_settings(**args)


class TestModelRecommendedSettingsNode:
    def test_outputs_follow_ksampler_order_and_types(self):
        node = ModelRecommendedSettingsNode
        assert node.RETURN_NAMES == (
            "steps",
            "cfg",
            "sampler_name",
            "scheduler",
            "info",
        )
        assert node.RETURN_TYPES[0] == "INT" and node.RETURN_TYPES[1] == "FLOAT"
        assert node.RETURN_TYPES[2] is SAMPLERS
        assert node.RETURN_TYPES[3] is SCHEDULERS

    def test_images_fill_steps_cfg_sampler_and_description_fills_scheduler(self):
        steps, cfg, sampler, scheduler, info = _run()
        assert (steps, cfg, sampler, scheduler) == (8, 1.0, "er_sde", "beta")
        assert info.startswith("Moss/fast.safetensors")

    def test_no_sidecar_uses_widgets(self):
        steps, cfg, sampler, scheduler, info = _run(sidecar=None)
        assert (steps, cfg, sampler, scheduler) == (25, 2.5, "euler", "simple")
        assert "no Civitai info found" in info

    def test_all_switches_off_is_same_settings_for_every_model(self):
        out = _run(
            use_model_steps=False,
            use_model_cfg=False,
            use_model_sampler=False,
            use_model_scheduler=False,
        )
        assert out[:4] == (25, 2.5, "euler", "simple")

    def test_per_model_override_by_stem_or_glob(self):
        overrides = {
            "models": {"fa*": {"steps": 12, "scheduler": "bong_tangent"}},
            "schedulers": {"bong_tangent": "karras"},
        }
        steps, _, _, scheduler, info = _run(overrides=overrides)
        assert steps == 12 and scheduler == "karras"
        assert "substituted karras" in info

    def test_full_path_model_name_is_accepted(self):
        out = _run(model_name="/m/Moss/fast.safetensors")
        assert out[0] == 8

    def test_is_changed_tracks_the_overrides_file(self):
        with patch(f"{NODE}.overrides_mtime", return_value=1.0):
            a = ModelRecommendedSettingsNode.IS_CHANGED(model_name="x")
        with patch(f"{NODE}.overrides_mtime", return_value=2.0):
            b = ModelRecommendedSettingsNode.IS_CHANGED(model_name="x")
        assert a != b


class TestModelPaths:
    def test_absolute_path_to_a_model_file_is_used(self, tmp_path):
        model = tmp_path / "a.safetensors"
        model.write_bytes(b"x")
        assert model_paths(str(model)) == [str(model)]

    def test_absolute_path_that_is_not_a_model_file_is_ignored(self, tmp_path):
        other = tmp_path / "secrets.json"
        other.write_text("{}")
        assert model_paths(str(other)) == []
        assert model_paths(str(tmp_path / "missing.safetensors")) == []
