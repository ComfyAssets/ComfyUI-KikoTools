"""Additional behavioural tests for gemini_prompt (models, logic, node)."""

import json
import sys
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from kikotools.tools.gemini_prompt import logic, models
from kikotools.tools.gemini_prompt.node import GeminiPromptNode
from kikotools.tools.gemini_prompt.prompts import DEFAULT_GEMINI_MODELS


@pytest.fixture
def cache_file(tmp_path, monkeypatch):
    path = tmp_path / "cache.json"
    monkeypatch.setattr(models, "CACHE_FILE", str(path))
    return path


def fake_genai(model_specs):
    genai = MagicMock()
    genai.list_models.return_value = [
        SimpleNamespace(
            name=f"models/{name}",
            display_name=display,
            supported_generation_methods=methods,
        )
        for name, display, methods in model_specs
    ]
    return genai


class TestSortModels:
    def test_newer_versions_come_first(self):
        result = models._sort_models(
            ["gemini-1.5-pro", "gemini-2.5-pro", "gemini-2.0-pro"]
        )
        assert result == ["gemini-2.5-pro", "gemini-2.0-pro", "gemini-1.5-pro"]

    def test_stable_before_experimental_and_preview(self):
        result = models._sort_models(
            ["gemini-2.5-pro-preview", "gemini-2.5-pro-exp", "gemini-2.5-pro"]
        )
        assert result[0] == "gemini-2.5-pro"

    def test_flash_variants_penalised(self):
        result = models._sort_models(
            [
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash-thinking",
                "gemini-2.5-flash-tts",
                "gemini-2.5-flash",
            ]
        )
        assert result[0] == "gemini-2.5-flash"
        assert result[-1] != "gemini-2.5-flash"

    def test_empty_list(self):
        assert models._sort_models([]) == []


class TestCache:
    def test_load_returns_none_when_missing(self, cache_file):
        assert models._load_cache() is None

    def test_save_then_load_roundtrip(self, cache_file):
        models._save_cache(["a"], {"a": "A"})
        data = models._load_cache()
        assert data["models"] == ["a"]
        assert data["descriptions"] == {"a": "A"}

    def test_expired_cache_is_ignored(self, cache_file):
        cache_file.write_text(
            json.dumps(
                {
                    "models": ["old"],
                    "descriptions": {},
                    "timestamp": time.time() - models.CACHE_DURATION - 10,
                }
            )
        )
        assert models._load_cache() is None

    def test_corrupt_cache_is_ignored(self, cache_file):
        cache_file.write_text("{not json")
        assert models._load_cache() is None

    def test_save_failure_is_swallowed(self, tmp_path, monkeypatch):
        monkeypatch.setattr(models, "CACHE_FILE", str(tmp_path / "nodir" / "c.json"))
        models._save_cache(["a"], {})  # must not raise

    def test_clear_cache_removes_file(self, cache_file):
        models._save_cache(["a"], {})
        assert cache_file.exists()
        models.clear_cache()
        assert not cache_file.exists()

    def test_clear_cache_when_missing_is_noop(self, cache_file):
        models.clear_cache()

    def test_clear_cache_remove_error_is_swallowed(self, cache_file):
        cache_file.write_text("{}")
        with patch.object(models.os, "remove", side_effect=OSError("nope")):
            models.clear_cache()


class TestFetchModelsFromApi:
    def test_missing_sdk_returns_empty(self):
        with patch.dict(sys.modules, {"google.generativeai": None, "google": None}):
            assert models._fetch_models_from_api("k") == ([], {})

    def test_no_api_key_returns_empty(self):
        genai = fake_genai([])
        google = MagicMock(generativeai=genai)
        with (
            patch.dict(sys.modules, {"google": google, "google.generativeai": genai}),
            patch.object(logic, "get_api_key", return_value=None),
        ):
            assert models._fetch_models_from_api(None, silent=True) == ([], {})

    def test_api_key_taken_from_logic_when_not_given(self):
        genai = fake_genai([("gemini-2.5-pro", "Pro", ["generateContent"])])
        google = MagicMock(generativeai=genai)
        with (
            patch.dict(sys.modules, {"google": google, "google.generativeai": genai}),
            patch.object(logic, "get_api_key", return_value="envkey"),
        ):
            names, _ = models._fetch_models_from_api(None)
        genai.configure.assert_called_once_with(api_key="envkey")
        assert names == ["gemini-2.5-pro"]

    def test_filters_to_generate_content_and_strips_prefix(self):
        genai = fake_genai(
            [
                ("gemini-1.5-pro", "Pro 1.5", ["generateContent"]),
                ("embedding-001", "Embed", ["embedContent"]),
                ("gemini-2.5-flash", "Flash", ["generateContent", "countTokens"]),
            ]
        )
        google = MagicMock(generativeai=genai)
        with patch.dict(sys.modules, {"google": google, "google.generativeai": genai}):
            names, desc = models._fetch_models_from_api("k")
        assert names == ["gemini-2.5-flash", "gemini-1.5-pro"]
        assert desc == {"gemini-1.5-pro": "Pro 1.5", "gemini-2.5-flash": "Flash"}

    def test_api_error_returns_empty(self):
        genai = MagicMock()
        genai.list_models.side_effect = RuntimeError("boom")
        google = MagicMock(generativeai=genai)
        with patch.dict(sys.modules, {"google": google, "google.generativeai": genai}):
            assert models._fetch_models_from_api("k") == ([], {})


class TestGetAvailableModels:
    def test_uses_fresh_cache_without_calling_api(self, cache_file):
        models._save_cache(["cached"], {"cached": "C"})
        with patch.object(models, "_fetch_models_from_api") as fetch:
            result = models.get_available_models("k")
        fetch.assert_not_called()
        assert result == (["cached"], {"cached": "C"})

    def test_fetches_and_caches(self, cache_file):
        with patch.object(
            models, "_fetch_models_from_api", return_value=(["m"], {"m": "M"})
        ):
            assert models.get_available_models("k") == (["m"], {"m": "M"})
        assert models._load_cache()["models"] == ["m"]

    def test_falls_back_to_defaults_when_empty(self, cache_file):
        with patch.object(models, "_fetch_models_from_api", return_value=([], {})):
            assert models.get_available_models("k") == (DEFAULT_GEMINI_MODELS, {})
        assert not cache_file.exists()

    def test_falls_back_to_defaults_on_exception(self, cache_file):
        with patch.object(models, "_fetch_models_from_api", side_effect=Exception("x")):
            assert models.get_available_models("k")[0] == DEFAULT_GEMINI_MODELS


class TestLogicExtra:
    def test_get_api_key_config_file_read(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        cfg = tmp_path / "gemini_config.json"
        cfg.write_text(json.dumps({"api_key": "from-file"}))
        with patch.object(logic.os.path, "join", return_value=str(cfg)):
            assert logic.get_api_key() == "from-file"

    def test_get_api_key_bad_config_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        cfg = tmp_path / "gemini_config.json"
        cfg.write_text("garbage")
        with patch.object(logic.os.path, "join", return_value=str(cfg)):
            assert logic.get_api_key() is None

    def test_tensor_conversion_failure_reported(self):
        out, err = logic.analyze_image_with_gemini(
            np.zeros((4, 4, 5)), "flux", api_key="k"
        )
        assert out == ""
        assert "Failed to convert image" in err

    def test_missing_sdk_reported(self):
        img = np.zeros((1, 4, 4, 3), dtype=np.float32)
        with patch.dict(sys.modules, {"google.generativeai": None, "google": None}):
            out, err = logic.analyze_image_with_gemini(img, "flux", api_key="k")
        assert out == "" and "not installed" in err

    def _run(self, response=None, error=None, **kwargs):
        genai = MagicMock()
        model = genai.GenerativeModel.return_value
        if error:
            model.generate_content.side_effect = error
        else:
            model.generate_content.return_value = response
        google = MagicMock(generativeai=genai)
        img = np.zeros((1, 4, 4, 3), dtype=np.float32)
        with patch.dict(sys.modules, {"google": google, "google.generativeai": genai}):
            result = logic.analyze_image_with_gemini(img, "flux", api_key="k", **kwargs)
        return result, genai

    def test_success_strips_text_and_uses_model(self):
        (out, err), genai = self._run(
            SimpleNamespace(text="  hello \n"), model_name="gemini-x"
        )
        assert (out, err) == ("hello", None)
        genai.configure.assert_called_once_with(api_key="k")
        genai.GenerativeModel.assert_called_once_with("gemini-x")

    def test_custom_prompt_is_sent_as_system_prompt(self):
        (_, _), genai = self._run(SimpleNamespace(text="x"), custom_prompt="BE TERSE")
        sent = genai.GenerativeModel.return_value.generate_content.call_args[0][0]
        assert sent[0] == "BE TERSE"

    def test_unknown_prompt_type_falls_back_to_flux_template(self):
        genai = MagicMock()
        genai.GenerativeModel.return_value.generate_content.return_value = (
            SimpleNamespace(text="x")
        )
        google = MagicMock(generativeai=genai)
        img = np.zeros((1, 4, 4, 3), dtype=np.float32)
        with patch.dict(sys.modules, {"google": google, "google.generativeai": genai}):
            logic.analyze_image_with_gemini(img, "nonsense", api_key="k")
        sent = genai.GenerativeModel.return_value.generate_content.call_args[0][0]
        assert sent[0] == logic.PROMPT_TEMPLATES["flux"]

    def test_empty_response(self):
        (out, err), _ = self._run(SimpleNamespace(text=""))
        assert out == "" and "No response" in err

    def test_api_exception(self):
        (out, err), _ = self._run(error=RuntimeError("quota"))
        assert out == "" and "Gemini API error: quota" in err


class TestNodeExtra:
    def _image(self):
        return torch.zeros(1, 4, 4, 3)

    def test_input_types_defaults_to_first_model(self):
        with patch(
            "kikotools.tools.gemini_prompt.node.get_available_models",
            return_value=(["m1", "m2"], {}),
        ):
            spec = GeminiPromptNode.INPUT_TYPES()
        assert spec["required"]["model"] == (["m1", "m2"], {"default": "m1"})

    def test_input_types_with_no_models_uses_defaults(self):
        with patch(
            "kikotools.tools.gemini_prompt.node.get_available_models",
            return_value=([], {}),
        ):
            spec = GeminiPromptNode.INPUT_TYPES()
        assert spec["required"]["model"][0] == DEFAULT_GEMINI_MODELS

    def test_torch_tensor_converted_to_numpy_and_blank_args_become_none(self):
        node = GeminiPromptNode()
        with patch(
            "kikotools.tools.gemini_prompt.node.analyze_image_with_gemini",
            return_value=("p", None),
        ) as analyze:
            result = node.generate_prompt(self._image(), "flux", "m")
        assert result == ("p", "")
        args, kwargs = analyze.call_args
        assert isinstance(args[0], np.ndarray)
        assert kwargs["api_key"] is None
        assert kwargs["custom_prompt"] is None
        assert kwargs["model_name"] == "m"

    def test_numpy_image_passes_through(self):
        node = GeminiPromptNode()
        arr = np.zeros((1, 4, 4, 3), dtype=np.float32)
        with patch(
            "kikotools.tools.gemini_prompt.node.analyze_image_with_gemini",
            return_value=("p", None),
        ) as analyze:
            node.generate_prompt(arr, "flux", "m")
        assert analyze.call_args[0][0] is arr

    def test_refresh_with_api_key_clears_cache(self):
        node = GeminiPromptNode()
        with (
            patch("kikotools.tools.gemini_prompt.models.clear_cache") as clear,
            patch(
                "kikotools.tools.gemini_prompt.models.get_available_models",
                return_value=(["x"], {}),
            ),
            patch(
                "kikotools.tools.gemini_prompt.node.analyze_image_with_gemini",
                return_value=("p", None),
            ),
        ):
            node.generate_prompt(
                self._image(), "flux", "m", api_key="k", refresh_models=True
            )
        clear.assert_called_once()

    def test_refresh_failure_does_not_break_generation(self):
        node = GeminiPromptNode()
        with (
            patch(
                "kikotools.tools.gemini_prompt.models.clear_cache",
                side_effect=RuntimeError("x"),
            ),
            patch(
                "kikotools.tools.gemini_prompt.models.get_available_models",
                side_effect=RuntimeError("y"),
            ),
            patch(
                "kikotools.tools.gemini_prompt.node.analyze_image_with_gemini",
                return_value=("p", None),
            ),
        ):
            result = node.generate_prompt(
                self._image(), "flux", "m", api_key="k", refresh_models=True
            )
        assert result == ("p", "")

    def test_sdxl_without_markers_returns_whole_text_as_positive(self):
        node = GeminiPromptNode()
        with patch(
            "kikotools.tools.gemini_prompt.node.analyze_image_with_gemini",
            return_value=("just a prompt", None),
        ):
            assert node.generate_prompt(self._image(), "sdxl", "m") == (
                "just a prompt",
                "",
            )

    def test_sdxl_splits_positive_and_negative(self):
        node = GeminiPromptNode()
        with patch(
            "kikotools.tools.gemini_prompt.node.analyze_image_with_gemini",
            return_value=("Positive: cat\nNegative: blurry", None),
        ):
            assert node.generate_prompt(self._image(), "sdxl", "m") == (
                "cat",
                "blurry",
            )
