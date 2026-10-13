"""Behavioural tests for KikoEmbeddingAutocomplete node and suggestion API."""

from unittest.mock import MagicMock

import pytest

from kikotools.tools.embedding_autocomplete import node as node_mod
from kikotools.tools.embedding_autocomplete.node import (
    KikoEmbeddingAutocomplete,
    KikoEmbeddingAutocompleteAPI,
)


@pytest.fixture
def fake_paths(monkeypatch):
    fp = MagicMock()
    files = {
        "embeddings": ["easynegative.pt", "sub/BadHands.safetensors", "other.pt"],
        "loras": ["detail.safetensors", "easy_style.safetensors"],
    }
    fp.get_filename_list.side_effect = lambda kind: files[kind]
    monkeypatch.setattr(node_mod, "folder_paths", fp)
    return fp


@pytest.fixture
def no_paths(monkeypatch):
    monkeypatch.setattr(node_mod, "folder_paths", None)


class TestNodeBasics:
    def test_input_types_hidden_unique_id(self):
        spec = KikoEmbeddingAutocomplete.INPUT_TYPES()
        assert spec["required"] == {}
        assert spec["hidden"] == {"unique_id": "UNIQUE_ID"}

    def test_validate_inputs_accepts_anything(self):
        assert KikoEmbeddingAutocomplete.VALIDATE_INPUTS(foo=1) is True

    def test_update_settings_returns_empty_tuple(self):
        assert KikoEmbeddingAutocomplete().update_settings(unique_id="7") == ()

    def test_settings_defaults_are_consistent(self):
        for key, spec in KikoEmbeddingAutocomplete.SETTINGS.items():
            assert "default" in spec, key
            if spec["type"] == "combo":
                assert spec["default"] in spec["options"]


class TestListing:
    def test_get_embeddings_strips_extension(self, fake_paths):
        result = KikoEmbeddingAutocomplete().get_embeddings()
        assert [e["name"] for e in result] == [
            "easynegative",
            "sub/BadHands",
            "other",
        ]
        assert result[0] == {
            "name": "easynegative",
            "file": "easynegative.pt",
            "type": "embedding",
            "display": "embedding:easynegative",
            "value": "embedding:easynegative",
        }

    def test_get_loras_format(self, fake_paths):
        result = KikoEmbeddingAutocomplete().get_loras()
        assert result[0]["value"] == "<lora:detail:1.0>"
        assert all(r["type"] == "lora" for r in result)

    def test_without_comfyui_lists_are_empty(self, no_paths):
        n = KikoEmbeddingAutocomplete()
        assert n.get_embeddings() == []
        assert n.get_loras() == []

    def test_listing_errors_are_swallowed(self, fake_paths):
        fake_paths.get_filename_list.side_effect = RuntimeError("disk")
        n = KikoEmbeddingAutocomplete()
        assert n.get_embeddings() == []
        assert n.get_loras() == []

    def test_refresh_cache_populates_both(self, fake_paths):
        n = KikoEmbeddingAutocomplete()
        assert n.embeddings_cache is None
        n.refresh_cache()
        assert len(n.embeddings_cache) == 3
        assert len(n.loras_cache) == 2


class TestIsChanged:
    def test_refresh_flag_forces_nan(self):
        value = KikoEmbeddingAutocomplete.IS_CHANGED(refresh=True)
        assert value != value

    def test_without_comfyui_is_zero(self, no_paths):
        assert KikoEmbeddingAutocomplete.IS_CHANGED() == 0

    def test_uses_folder_mtimes(self, fake_paths, tmp_path):
        a = tmp_path / "emb"
        b = tmp_path / "lor"
        a.mkdir()
        b.mkdir()
        fake_paths.get_folder_paths.side_effect = lambda k: [
            str(a if k == "embeddings" else b)
        ]
        import os

        assert KikoEmbeddingAutocomplete.IS_CHANGED() == pytest.approx(
            os.path.getmtime(a) + os.path.getmtime(b)
        )

    def test_missing_folders_fall_back_to_zero(self, fake_paths):
        fake_paths.get_folder_paths.side_effect = lambda k: ["/definitely/not/here"]
        assert KikoEmbeddingAutocomplete.IS_CHANGED() == 0


class TestSuggestions:
    api = KikoEmbeddingAutocompleteAPI

    def test_prefix_match_case_insensitive(self, fake_paths):
        result = self.api.get_suggestions("EASY")
        # equal priority -> ordered by name
        assert [(r["type"], r["name"]) for r in result] == [
            ("lora", "easy_style"),
            ("embedding", "easynegative"),
        ]

    def test_substring_match_ranked_below_prefix(self, fake_paths):
        result = self.api.get_suggestions("hands")
        assert [r["name"] for r in result] == ["sub/BadHands"]
        assert result[0]["priority"] == -1

    def test_exact_match_first(self, fake_paths):
        result = self.api.get_suggestions("detail")
        assert result[0]["priority"] == 1
        assert result[0]["value"] == "<lora:detail:1.0>"

    def test_case_sensitive_mode(self, fake_paths):
        assert self.api.get_suggestions("EASY", case_sensitive=True) == []
        names = [
            r["name"] for r in self.api.get_suggestions("easy", case_sensitive=True)
        ]
        assert names == ["easy_style", "easynegative"]

    def test_exclude_types(self, fake_paths):
        only_emb = self.api.get_suggestions("e", include_loras=False)
        assert {r["type"] for r in only_emb} == {"embedding"}
        only_lora = self.api.get_suggestions("e", include_embeddings=False)
        assert {r["type"] for r in only_lora} == {"lora"}

    def test_max_results_limits_output(self, fake_paths):
        assert len(self.api.get_suggestions("e", max_results=1)) == 1

    def test_empty_prefix_matches_everything(self, fake_paths):
        assert len(self.api.get_suggestions("")) == 5

    def test_no_match(self, fake_paths):
        assert self.api.get_suggestions("zzz") == []

    def test_without_comfyui(self, no_paths):
        assert self.api.get_suggestions("a") == []

    def test_errors_swallowed(self, fake_paths):
        fake_paths.get_filename_list.side_effect = RuntimeError("x")
        assert self.api.get_suggestions("a") == []
