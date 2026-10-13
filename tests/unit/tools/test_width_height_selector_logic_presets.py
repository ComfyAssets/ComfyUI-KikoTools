"""Behavioural tests for width_height_selector logic and presets."""

import pytest

from kikotools.tools.width_height_selector import logic, presets
from kikotools.tools.width_height_selector.presets import PresetMetadata


class TestGetPresetDimensions:
    def test_known_preset(self):
        assert logic.get_preset_dimensions("1024×1024", 1, 2) == (1024, 1024)

    def test_custom_uses_given_values(self):
        assert logic.get_preset_dimensions("custom", 333, 444) == (333, 444)

    def test_unknown_preset_falls_back_to_custom_values(self):
        assert logic.get_preset_dimensions("nope", 333, 444) == (333, 444)


class TestSwapAndAspect:
    def test_swap(self):
        assert logic.apply_swap_logic(1, 2, True) == (2, 1)
        assert logic.apply_swap_logic(1, 2, False) == (1, 2)

    @pytest.mark.parametrize(
        "w,h,expected",
        [
            (1920, 1080, "16:9"),
            (1024, 1024, "1:1"),
            (0, 5, "Invalid"),
            (5, -1, "Invalid"),
        ],
    )
    def test_aspect_ratio(self, w, h, expected):
        assert logic.calculate_aspect_ratio(w, h) == expected


class TestValidateAndSanitize:
    @pytest.mark.parametrize(
        "w,h,ok",
        [
            (1024, 1024, True),
            (64, 8192, True),
            (0, 64, False),
            (-8, 64, False),
            (1025, 1024, False),
            (1024, 1030, False),
            (56, 64, False),
            (8200, 64, False),
            (64, 8200, False),
        ],
    )
    def test_validate_dimensions(self, w, h, ok):
        assert logic.validate_dimensions(w, h) is ok

    def test_sanitize_clamps_and_rounds(self):
        assert logic.sanitize_dimensions(10, 10) == (64, 64)
        assert logic.sanitize_dimensions(99999, 99999) == (8192, 8192)
        assert logic.sanitize_dimensions(1027, 1028) == (1024, 1032)

    def test_sanitized_output_is_always_valid(self):
        for raw in (-5, 0, 63, 65, 1001, 5000, 20000):
            w, h = logic.sanitize_dimensions(raw, raw)
            assert logic.validate_dimensions(w, h)


class TestDimensionInfo:
    def test_info_for_preset_without_swap(self):
        info = logic.get_dimension_info("832×1216", 0, 0, False)
        assert info["width"] == 832 and info["height"] == 1216
        assert info["is_portrait"] and not info["is_landscape"]
        assert info["is_valid"] is True
        assert info["aspect_ratio"] == "13:19"
        assert info["megapixels"] == 1.01
        assert info["swap_applied"] is False

    def test_info_with_swap_custom(self):
        info = logic.get_dimension_info("custom", 1920, 1080, True)
        assert (info["width"], info["height"]) == (1080, 1920)
        assert info["is_portrait"]
        assert info["preset_used"] == "custom"

    def test_square_and_invalid(self):
        info = logic.get_dimension_info("custom", 100, 100, False)
        assert info["is_square"] and not info["is_valid"]


class TestStringHelpers:
    def test_format(self):
        assert logic.format_dimension_string(1920, 1080) == "1920×1080"

    @pytest.mark.parametrize("s", ["1920×1080", "1920x1080", " 1920 x 1080 "])
    def test_parse_ok(self, s):
        assert logic.parse_dimension_string(s) == (1920, 1080)

    @pytest.mark.parametrize("s", ["1920", "1x2x3", "axb", "×", ""])
    def test_parse_errors(self, s):
        with pytest.raises(ValueError):
            logic.parse_dimension_string(s)

    def test_roundtrip(self):
        assert logic.parse_dimension_string(
            logic.format_dimension_string(640, 480)
        ) == (640, 480)


class TestScaleAndSuggestions:
    def test_scale_factor_average(self):
        assert logic.get_optimal_scale_factor(100, 100, 200, 400) == pytest.approx(3.0)

    def test_scale_factor_invalid_current(self):
        assert logic.get_optimal_scale_factor(0, 10, 5, 5) == 1.0
        assert logic.get_optimal_scale_factor(10, -1, 5, 5) == 1.0

    def test_suggestions_closest_ratio_first(self):
        result = logic.suggest_similar_presets(1024, 1024, 3)
        assert len(result) == 3
        assert result[0] in presets.PRESET_OPTIONS
        w, h = presets.PRESET_OPTIONS[result[0]]
        assert w == h

    def test_suggestions_respect_limit_and_skip_custom(self):
        result = logic.suggest_similar_presets(1920, 1080, 5)
        assert len(result) == 5 and "custom" not in result

    def test_suggestions_invalid_dims(self):
        assert logic.suggest_similar_presets(0, 10) == []
        assert logic.suggest_similar_presets(10, -1) == []


class TestPresetsModule:
    def test_aspect_ratio_helper(self):
        assert presets.calculate_aspect_ratio(1920, 1080) == (
            "16:9",
            pytest.approx(16 / 9),
        )

    def test_group_filters(self):
        sdxl = presets.get_presets_by_model_group("SDXL")
        assert sdxl and all(m.model_group == "SDXL" for m in sdxl.values())
        assert presets.get_presets_by_model_group("Nope") == {}

    def test_aspect_filter(self):
        squares = presets.get_presets_by_aspect_ratio("1:1")
        assert "1024×1024" in squares

    def test_category_filter(self):
        portraits = presets.get_presets_by_category("Portrait")
        assert "832×1216" in portraits

    def test_metadata_lookup_and_default(self):
        assert presets.get_preset_metadata("1024×1024").width == 1024
        default = presets.get_preset_metadata("missing")
        assert (default.width, default.height, default.category) == (0, 0, "Custom")

    def test_category_lookup(self):
        assert presets.get_preset_category("832×1216") == "Portrait"
        assert presets.get_preset_category("???") == "Unknown"

    def test_category_lookup_via_category_table(self, monkeypatch):
        monkeypatch.setattr(presets, "PRESET_METADATA", {})
        monkeypatch.setattr(presets, "PRESET_CATEGORIES", {"Special": ["x"]})
        assert presets.get_preset_category("x") == "Special"

    def test_model_recommendation(self):
        assert presets.get_model_recommendation("1024×1024") == "Optimized for SDXL"
        assert presets.get_model_recommendation("?") == "Custom dimensions"

    def test_shipped_presets_valid(self):
        assert presets.validate_preset_dimensions() is True
        assert presets.validate_metadata_consistency() is True
        assert set(presets.PRESET_OPTIONS) >= {"custom"}

    def test_preset_options_match_metadata(self):
        for name, meta in presets.PRESET_METADATA.items():
            assert presets.PRESET_OPTIONS[name] == (meta.width, meta.height)

    def _patch(self, monkeypatch, meta):
        monkeypatch.setattr(presets, "PRESET_METADATA", {"bad": meta})

    def test_validation_rejects_non_multiple_of_8(self, monkeypatch):
        self._patch(
            monkeypatch, PresetMetadata(1001, 1024, "1:1", 1.0, 1.0, "g", "c", "d")
        )
        assert presets.validate_preset_dimensions() is False

    def test_validation_rejects_out_of_bounds(self, monkeypatch):
        self._patch(
            monkeypatch, PresetMetadata(16, 1024, "1:1", 1.0, 1.0, "g", "c", "d")
        )
        assert presets.validate_preset_dimensions() is False

    def test_consistency_rejects_bad_aspect(self, monkeypatch):
        self._patch(
            monkeypatch, PresetMetadata(1024, 512, "1:1", 1.0, 0.5, "g", "c", "d")
        )
        assert presets.validate_metadata_consistency() is False

    def test_consistency_rejects_bad_megapixels(self, monkeypatch):
        self._patch(
            monkeypatch, PresetMetadata(1024, 1024, "1:1", 1.0, 9.0, "g", "c", "d")
        )
        assert presets.validate_metadata_consistency() is False
