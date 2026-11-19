"""Tests for Model Recommended Settings logic."""

import json

from kikotools.tools.model_settings.logic import (
    find_sidecar,
    from_description,
    from_images,
    map_sampler,
    resolve,
    sources_from_sidecar,
)

SAMPLERS = ["euler", "euler_ancestral", "dpmpp_2m", "dpmpp_2m_sde", "er_sde", "uni_pc"]
SCHEDULERS = ["simple", "normal", "karras", "exponential", "beta", "sgm_uniform"]
WIDGETS = {"steps": 25, "cfg": 2.5, "sampler": "euler", "scheduler": "simple"}
ALL_ON = {"steps": True, "cfg": True, "sampler": True, "scheduler": True}


def _img(steps=None, cfg=None, sampler=None, scheduler=None):
    return {
        "meta": {
            "steps": steps,
            "cfgScale": cfg,
            "sampler": sampler,
            "scheduler": scheduler,
        }
    }


class TestMapSampler:
    def test_civitai_names_map_to_comfy_names(self):
        assert map_sampler("Euler") == ("euler", None)
        assert map_sampler("Euler a") == ("euler_ancestral", None)
        assert map_sampler("ER SDE") == ("er_sde", None)
        assert map_sampler("UniPC") == ("uni_pc", None)

    def test_scheduler_suffix_is_split_off(self):
        assert map_sampler("DPM++ 2M Karras") == ("dpmpp_2m", "karras")
        assert map_sampler("DPM++ 2M SDE Karras") == (
            "dpmpp_2m_sde",
            "karras",
        )

    def test_comfy_names_pass_through(self):
        assert map_sampler("er_sde") == ("er_sde", None)

    def test_unknown_sampler_is_returned_normalized(self):
        assert map_sampler("res_2s") == ("res_2s", None)


class TestFromImages:
    def test_takes_the_most_common_value_per_field(self):
        images = [
            _img(8, 1, "ER SDE"),
            _img(8, 1, "ER SDE"),
            _img(10, 1, "Euler", "simple"),
        ]
        assert from_images(images) == {
            "steps": 8,
            "cfg": 1.0,
            "sampler": "er_sde",
            "scheduler": "simple",
        }

    def test_ignores_zero_steps_and_missing_meta(self):
        images = [_img(0, 1, "Euler"), {"meta": None}, {}, _img(12, 1, "Euler")]
        assert from_images(images)["steps"] == 12

    def test_scheduler_from_sampler_suffix(self):
        assert from_images([_img(30, 6, "DPM++ 2M Karras")]) == {
            "steps": 30,
            "cfg": 6.0,
            "sampler": "dpmpp_2m",
            "scheduler": "karras",
        }

    def test_no_images_gives_nothing(self):
        assert from_images([]) == {}


class TestFromDescription:
    def test_bullet_settings_line(self):
        text = "<p>⚙️ Settings 8 steps · CFG 1 · ER SDE · Beta · 1024×1024</p>"
        assert from_description(text, SAMPLERS, SCHEDULERS) == {
            "steps": 8,
            "cfg": 1.0,
            "sampler": "er_sde",
            "scheduler": "beta",
        }

    def test_labelled_settings(self):
        text = "Recommended Settings Steps: 25 (Optimized) CFG Scale: 3.5 Sampler: Euler Simple"
        assert from_description(text, SAMPLERS, SCHEDULERS) == {
            "steps": 25,
            "cfg": 3.5,
            "sampler": "euler",
            "scheduler": "simple",
        }

    def test_prose_words_are_not_read_as_schedulers(self):
        text = "A simple, normal model. Use 30 steps."
        assert from_description(text, SAMPLERS, SCHEDULERS) == {"steps": 30}

    def test_empty_text(self):
        assert from_description("", SAMPLERS, SCHEDULERS) == {}


class TestResolve:
    def test_override_beats_images_beats_description_beats_widget(self):
        values, info = resolve(
            [
                ("override", {"cfg": 1.5}),
                ("Civitai images", {"steps": 8, "cfg": 1.0}),
                ("description", {"steps": 10, "scheduler": "beta"}),
            ],
            WIDGETS,
            ALL_ON,
            SAMPLERS,
            SCHEDULERS,
            {},
        )
        assert values == {
            "steps": 8,
            "cfg": 1.5,
            "sampler": "euler",
            "scheduler": "beta",
        }
        assert "cfg 1.5 (override)" in info
        assert "steps 8 (Civitai images)" in info
        assert "sampler euler (widget)" in info

    def test_switched_off_field_uses_the_widget(self):
        values, info = resolve(
            [("Civitai images", {"steps": 8, "cfg": 1.0})],
            WIDGETS,
            dict(ALL_ON, cfg=False),
            SAMPLERS,
            SCHEDULERS,
            {},
        )
        assert values["steps"] == 8 and values["cfg"] == 2.5
        assert "cfg 2.5 (widget)" in info

    def test_missing_scheduler_uses_substitution(self):
        values, info = resolve(
            [("description", {"scheduler": "bong_tangent"})],
            WIDGETS,
            ALL_ON,
            SAMPLERS,
            SCHEDULERS,
            {"schedulers": {"bong_tangent": "beta"}},
        )
        assert values["scheduler"] == "beta"
        assert "bong_tangent is not installed, substituted beta" in info

    def test_missing_scheduler_without_substitution_uses_widget(self):
        values, info = resolve(
            [("description", {"scheduler": "bong_tangent"})],
            WIDGETS,
            ALL_ON,
            SAMPLERS,
            SCHEDULERS,
            {"schedulers": {"bong_tangent": "also_missing"}},
        )
        assert values["scheduler"] == "simple"
        assert "bong_tangent is not installed, using the widget" in info

    def test_missing_sampler_uses_widget(self):
        values, _ = resolve(
            [("Civitai images", {"sampler": "res_2s"})],
            WIDGETS,
            ALL_ON,
            SAMPLERS,
            SCHEDULERS,
            {},
        )
        assert values["sampler"] == "euler"


class TestFindSidecar:
    def _write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def test_sidecar_next_to_the_model(self, tmp_path):
        model = tmp_path / "Moss" / "a.safetensors"
        self._write(tmp_path / "Moss" / "a.metadata.json", {"civitai": {"id": 1}})
        assert find_sidecar([str(model)], None)["civitai"]["id"] == 1

    def test_civitai_info_next_to_the_model(self, tmp_path):
        model = tmp_path / "a.safetensors"
        self._write(tmp_path / "a.civitai.info", {"images": [], "id": 2})
        assert find_sidecar([str(model)], None) == {"civitai": {"images": [], "id": 2}}

    def test_central_sidecar_prefers_matching_file_path(self, tmp_path):
        model = "/models/diffusion_models/Moss/a.safetensors"
        root = tmp_path / "sidecars"
        self._write(
            root / "x" / "a.metadata.json",
            {"file_path": "/other/a.safetensors", "n": 1},
        )
        self._write(
            root / "y" / "Moss" / "a.metadata.json", {"file_path": model, "n": 2}
        )
        assert find_sidecar([model], str(root))["n"] == 2

    def test_central_sidecar_falls_back_to_stem_match(self, tmp_path):
        root = tmp_path / "sidecars"
        self._write(
            root / "x" / "a.metadata.json",
            {"file_path": "/elsewhere/a.safetensors", "n": 1},
        )
        assert find_sidecar(["/models/a.safetensors"], str(root))["n"] == 1

    def test_nothing_found(self, tmp_path):
        assert find_sidecar([str(tmp_path / "a.safetensors")], str(tmp_path)) is None


class TestSourcesFromSidecar:
    IMAGES = [_img(18, 3, "Euler", "simple")]

    def test_recommended_settings_in_the_description_come_first(self):
        sidecar = {
            "modelDescription": "Recommended Settings Steps: 25 CFG Scale: 3.5",
            "civitai": {"images": self.IMAGES},
        }
        sources = sources_from_sidecar(sidecar, SAMPLERS, SCHEDULERS)
        assert [name for name, _ in sources] == ["description", "Civitai images"]
        values, _ = resolve(sources, WIDGETS, ALL_ON, SAMPLERS, SCHEDULERS, {})
        assert (values["steps"], values["cfg"]) == (25, 3.5)

    def test_images_come_first_when_nothing_is_called_recommended(self):
        sidecar = {
            "civitai": {"description": "Trained for 30 steps.", "images": self.IMAGES}
        }
        sources = sources_from_sidecar(sidecar, SAMPLERS, SCHEDULERS)
        assert [name for name, _ in sources] == ["Civitai images", "description"]
