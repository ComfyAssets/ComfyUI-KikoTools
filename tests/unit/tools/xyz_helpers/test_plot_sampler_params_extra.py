"""Additional behavioural tests for plot_sampler_params logic and node."""

import logging

import pytest
import torch

from kikotools.tools.xyz_helpers.plot_sampler_params import logic
from kikotools.tools.xyz_helpers.plot_sampler_params.node import PlotParametersNode


def make_params(n, **overrides):
    out = []
    for i in range(n):
        p = {
            "time": 1.0 + i,
            "seed": i,
            "steps": 20,
            "denoise": 1.0,
            "sampler": "euler",
            "scheduler": "simple",
            "guidance": 3.5,
            "max_shift": 1.15,
            "base_shift": 0.5,
            "width": 64,
            "height": 64,
            "prompt": "a cat sitting on a very long sofa " * 6,
        }
        p.update(overrides)
        out.append(p)
    return out


class TestSortAndGroup:
    def test_sort_none_keeps_order(self):
        params = [{"seed": 3}, {"seed": 1}]
        assert logic.sort_parameters(params, "none") == (params, [0, 1])

    def test_sort_returns_original_indices(self):
        params = [{"seed": 3}, {"seed": 1}, {"seed": 2}]
        sorted_params, idx = logic.sort_parameters(params, "seed")
        assert [p["seed"] for p in sorted_params] == [1, 2, 3]
        assert idx == [1, 2, 0]

    def test_sort_missing_key_defaults_to_zero(self):
        params = [{"seed": 5}, {}]
        _, idx = logic.sort_parameters(params, "seed")
        assert idx == [1, 0]

    def test_sort_incomparable_values_falls_back(self):
        params = [{"seed": "a"}, {"seed": 1}]
        result, idx = logic.sort_parameters(params, "seed")
        assert result == params and idx == [0, 1]

    def test_group_none(self):
        params = [{"a": 1}]
        assert logic.group_by_value(params, "none") == (params, [0], -1)

    def test_group_interleaves_columns(self):
        params = [
            {"sampler": "a", "n": 0},
            {"sampler": "a", "n": 1},
            {"sampler": "b", "n": 2},
            {"sampler": "b", "n": 3},
        ]
        out, idx, groups = logic.group_by_value(params, "sampler")
        assert groups == 2
        assert idx == [0, 2, 1, 3]
        assert [p["n"] for p in out] == [0, 2, 1, 3]

    def test_group_missing_key_goes_to_unknown(self):
        out, idx, groups = logic.group_by_value([{"x": 1}, {"x": 2}], "sampler")
        assert groups == 1 and idx == [0, 1]

    def test_group_unhashable_value_falls_back(self):
        params = [{"k": [1]}, {"k": [2]}]
        assert logic.group_by_value(params, "k") == (params, [0, 1], -1)

    def test_group_empty_params_falls_back(self):
        assert logic.group_by_value([], "sampler") == ([], [], -1)


class TestChangingParams:
    def test_empty(self):
        assert logic.identify_changing_parameters([]) == {}

    def test_detects_changes_and_ignores_time(self):
        params = [
            {"time": 1, "seed": 1, "steps": 20},
            {"time": 2, "seed": 2, "steps": 20},
        ]
        changing = logic.identify_changing_parameters(params)
        assert changing == {"seed": True, "steps": False}

    def test_list_and_dict_values_compared_by_content(self):
        params = [
            {"a": [1, 2], "b": {"x": 1}},
            {"a": [1, 2], "b": {"x": 2}},
        ]
        changing = logic.identify_changing_parameters(params)
        assert changing == {"a": False, "b": True}

    def test_prompt_always_included(self):
        changing = logic.identify_changing_parameters(
            [{"prompt": "same"}, {"prompt": "same"}]
        )
        assert changing["prompt"] is True

    def test_filter_keeps_only_changing(self):
        params = [{"seed": 1, "steps": 20}, {"seed": 2, "steps": 20}]
        assert logic.filter_changing_params(params) == [{"seed": 1}, {"seed": 2}]


class TestFormatting:
    def test_changes_only_skips_prompt(self):
        text = logic.format_parameter_text({"seed": 1, "prompt": "p"}, "changes only")
        assert text == "seed: 1"

    def test_full_with_defaults_na(self):
        text = logic.format_parameter_text({})
        assert "denoise: N/A" in text
        assert "time:" not in text

    def test_full_with_time_line(self):
        text = logic.format_parameter_text(make_params(1)[0])
        first = text.split("\n")[0]
        assert first.startswith("time: 1.00s, seed: 0, steps: 20, size: 64×64")

    def test_lora_short_path_and_batch(self):
        text = logic.format_parameter_text(
            {"lora": "a.safetensors", "lora_strength": 0.8, "lora_batch": "2/3"}
        )
        assert text.split("\n")[-1] == "LoRA: a, str: 0.8 [2/3]"

    def test_lora_long_path_shows_parent_and_filename(self):
        text = logic.format_parameter_text(
            {"lora": "C:\\models\\loras\\style\\x.safetensors", "lora_strength": 1}
        )
        assert "LoRA: style/x, str: 1" in text

    def test_empty_lora_omitted(self):
        assert "LoRA" not in logic.format_parameter_text({"lora": ""})

    def test_wrap_empty(self):
        assert logic.wrap_prompt_text("", 10) == []

    def test_wrap_full_respects_width(self):
        lines = logic.wrap_prompt_text("word " * 20, 12)
        assert len(lines) > 1 and all(len(l) <= 12 for l in lines)

    def test_wrap_excerpt_truncates_to_64_words(self):
        lines = logic.wrap_prompt_text(" ".join(["w"] * 100), 1000, "excerpt")
        assert lines[0].endswith("...")
        assert len(lines[0].rstrip(".").split()) == 64

    def test_wrap_excerpt_short_prompt_unchanged(self):
        assert logic.wrap_prompt_text("a b c", 100, "excerpt") == ["a b c"]

    def test_text_dimensions(self):
        assert logic.calculate_text_dimensions("a\nb\nc", 20, 512) == (30, 12, 3)


class TestGridAndValidation:
    @pytest.mark.parametrize("cols", [-1, 0])
    def test_auto_grid(self, cols):
        assert logic.calculate_grid_dimensions(9, cols) == (3, 3)

    def test_auto_grid_single_image(self):
        assert logic.calculate_grid_dimensions(1, -1) == (1, 1)

    def test_explicit_columns_capped_by_count(self):
        assert logic.calculate_grid_dimensions(3, 10) == (1, 3)
        assert logic.calculate_grid_dimensions(5, 2) == (3, 2)

    def test_validate_mismatch(self):
        assert (
            logic.validate_plot_parameters((3, 8, 8, 3), 2, "none", "none", -1) is False
        )

    def test_validate_warns_but_passes(self, caplog):
        with caplog.at_level(logging.WARNING):
            ok = logic.validate_plot_parameters((1, 8, 8, 3), 1, "bogus", "bogus", 5000)
        assert ok is True
        assert len(caplog.records) == 3


class TestPlotNode:
    @pytest.fixture
    def node(self):
        return PlotParametersNode()

    def images(self, n, size=64):
        return torch.rand(n, size, size, 3)

    def test_mismatched_lengths_raise(self, node):
        with pytest.raises(ValueError):
            node.plot_parameters(
                self.images(2), make_params(3), "none", "none", -1, "false", "false"
            )

    def test_no_text_no_grid_stacks_batch(self, node):
        (out,) = node.plot_parameters(
            self.images(3), make_params(3), "none", "none", -1, "false", "false"
        )
        assert out.shape == (3, 64, 64, 3)

    def test_params_text_extends_height(self, node):
        (out,) = node.plot_parameters(
            self.images(2), make_params(2), "none", "none", -1, "false", "true"
        )
        assert out.shape[0] == 2 and out.shape[1] > 64 and out.shape[2] == 64

    def test_prompt_text_added_and_heights_equalised(self, node):
        params = make_params(2)
        params[1]["prompt"] = "short"
        (out,) = node.plot_parameters(
            self.images(2), params, "none", "none", -1, "true", "false"
        )
        assert out.shape[0] == 2 and out.shape[1] > 64

    def test_excerpt_prompt(self, node):
        (out,) = node.plot_parameters(
            self.images(1), make_params(1), "none", "none", -1, "excerpt", "false"
        )
        assert out.shape[1] > 64

    def test_changes_only_mode(self, node):
        (out,) = node.plot_parameters(
            self.images(2), make_params(2), "none", "none", -1, "false", "changes only"
        )
        assert out.shape[0] == 2

    def test_sort_reorders_images(self, node):
        imgs = torch.zeros(3, 64, 64, 3)
        for i in range(3):
            imgs[i] = i / 10
        params = [{"seed": 3}, {"seed": 1}, {"seed": 2}]
        (out,) = node.plot_parameters(
            imgs, params, "seed", "none", -1, "false", "false"
        )
        assert out[:, 0, 0, 0].tolist() == pytest.approx([0.1, 0.2, 0.0])

    def test_grid_creation_with_padding(self, node):
        (out,) = node.plot_parameters(
            self.images(3), make_params(3), "none", "none", 2, "false", "false"
        )
        assert out.shape == (1, 128, 128, 3)

    def test_square_layout_for_cols_zero(self, node):
        (out,) = node.plot_parameters(
            self.images(4), make_params(4), "none", "none", 0, "false", "false"
        )
        assert out.shape == (1, 128, 128, 3)

    def test_group_by_value_sets_columns(self, node):
        params = make_params(4)
        params[0]["sampler"] = params[1]["sampler"] = "a"
        params[2]["sampler"] = params[3]["sampler"] = "b"
        (out,) = node.plot_parameters(
            self.images(4), params, "none", "sampler", 5, "false", "false"
        )
        assert out.shape == (1, 128, 128, 3)

    def test_nan_values_cleaned(self, node):
        imgs = self.images(1)
        imgs[0, 0, 0, 0] = float("nan")
        (out,) = node.plot_parameters(
            imgs, make_params(1), "none", "none", -1, "false", "false"
        )
        assert torch.isfinite(out).all()
        assert out.min() >= 0 and out.max() <= 1

    def test_font_fallback_when_truetype_missing(self, node, monkeypatch):
        monkeypatch.setattr(node, "_get_font_path", lambda: "/does/not/exist.ttf")
        (out,) = node.plot_parameters(
            self.images(1), make_params(1), "none", "none", -1, "false", "true"
        )
        assert out.shape[1] > 64

    def test_get_font_path_returns_string_default(self, node, monkeypatch):
        import os

        monkeypatch.setattr(os.path, "exists", lambda p: False)
        assert node._get_font_path() == "arial.ttf"

    def test_get_font_path_returns_first_existing(self, node, monkeypatch):
        import os

        monkeypatch.setattr(os.path, "exists", lambda p: p.endswith("cour.ttf"))
        assert node._get_font_path().endswith("cour.ttf")

    def test_very_narrow_images_do_not_crash_on_zero_font_size(self, node):
        (out,) = node.plot_parameters(
            torch.rand(1, 8, 8, 3), make_params(1), "none", "none", -1, "false", "false"
        )
        assert out.shape == (1, 8, 8, 3)
