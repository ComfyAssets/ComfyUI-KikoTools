"""Tests for Plot Parameters node."""

import pytest
import torch
from unittest.mock import Mock, patch
from kikotools.tools.xyz_helpers.plot_sampler_params import PlotParametersNode
from kikotools.tools.xyz_helpers.plot_sampler_params.logic import (
    sort_parameters,
    group_by_value,
    identify_changing_parameters,
    filter_changing_params,
    format_parameter_text,
    wrap_prompt_text,
    calculate_grid_dimensions,
    validate_plot_parameters,
)


class TestPlotParametersLogic:
    """Test the logic functions for Plot Parameters."""

    def test_sort_parameters(self):
        """Test sorting parameters."""
        params = [
            {"seed": 3, "steps": 20},
            {"seed": 1, "steps": 30},
            {"seed": 2, "steps": 10},
        ]

        # Sort by seed
        sorted_params, indices = sort_parameters(params, "seed")
        assert sorted_params[0]["seed"] == 1
        assert sorted_params[1]["seed"] == 2
        assert sorted_params[2]["seed"] == 3
        assert indices == [1, 2, 0]

        # Sort by steps
        sorted_params, indices = sort_parameters(params, "steps")
        assert sorted_params[0]["steps"] == 10
        assert sorted_params[1]["steps"] == 20
        assert sorted_params[2]["steps"] == 30

        # No sorting
        sorted_params, indices = sort_parameters(params, "none")
        assert sorted_params == params
        assert indices == [0, 1, 2]

    def test_group_by_value(self):
        """Test grouping by value."""
        params = [
            {"sampler": "euler", "seed": 1},
            {"sampler": "ddim", "seed": 2},
            {"sampler": "euler", "seed": 3},
            {"sampler": "ddim", "seed": 4},
        ]

        grouped, indices, num_groups = group_by_value(params, "sampler")
        assert num_groups == 2
        # Check that same samplers are grouped
        assert grouped[0]["sampler"] == grouped[2]["sampler"]
        assert grouped[1]["sampler"] == grouped[3]["sampler"]

    def test_identify_changing_parameters(self):
        """Test identifying changing parameters."""
        params = [
            {"seed": 1, "steps": 20, "sampler": "euler"},
            {"seed": 2, "steps": 20, "sampler": "ddim"},
            {"seed": 3, "steps": 20, "sampler": "euler"},
        ]

        changing = identify_changing_parameters(params)
        assert changing["seed"] == True  # Seed changes
        assert changing["steps"] == False  # Steps don't change
        assert changing["sampler"] == True  # Sampler changes

    def test_filter_changing_params(self):
        """Test filtering to only changing parameters."""
        params = [
            {"seed": 1, "steps": 20, "sampler": "euler"},
            {"seed": 2, "steps": 20, "sampler": "ddim"},
        ]

        filtered = filter_changing_params(params)
        assert "seed" in filtered[0]
        assert "sampler" in filtered[0]
        assert "steps" not in filtered[0]  # Steps don't change

    def test_format_parameter_text_full(self):
        """Test formatting parameter text in full mode."""
        param = {
            "time": 2.5,
            "seed": 12345,
            "steps": 20,
            "width": 512,
            "height": 512,
            "denoise": 1.0,
            "sampler": "euler",
            "scheduler": "normal",
            "guidance": 7.0,
            "max_shift": 1.15,
            "base_shift": 0.5,
        }

        text = format_parameter_text(param, "full")
        assert "time: 2.50s" in text
        assert "seed: 12345" in text
        assert "steps: 20" in text
        assert "512×512" in text

    def test_format_parameter_text_changes_only(self):
        """Test formatting parameter text in changes only mode."""
        param = {"seed": 12345, "sampler": "euler", "prompt": "test prompt"}

        text = format_parameter_text(param, "changes only")
        assert "seed: 12345" in text
        assert "sampler: euler" in text
        assert "prompt" not in text  # Prompt handled separately

    def test_wrap_prompt_text(self):
        """Test wrapping prompt text."""
        prompt = "This is a very long prompt that needs to be wrapped"

        # Full mode
        lines = wrap_prompt_text(prompt, 20, "full")
        assert len(lines) > 1
        assert all(len(line) <= 20 for line in lines)

        # Excerpt mode
        long_prompt = " ".join(["word"] * 100)
        lines = wrap_prompt_text(long_prompt, 50, "excerpt")
        full_text = " ".join(lines)
        assert "..." in full_text

    def test_calculate_grid_dimensions(self):
        """Test calculating grid dimensions."""
        # Auto mode
        rows, cols = calculate_grid_dimensions(9, -1)
        assert rows == 3
        assert cols == 3

        # Fixed columns
        rows, cols = calculate_grid_dimensions(10, 3)
        assert rows == 4
        assert cols == 3

        # Auto square
        rows, cols = calculate_grid_dimensions(16, 0)
        assert rows == 4
        assert cols == 4

    def test_validate_plot_parameters(self):
        """Test validating plot parameters."""
        # Valid
        assert validate_plot_parameters((5, 256, 256, 3), 5, "none", "none", -1) == True

        # Mismatch
        assert (
            validate_plot_parameters((5, 256, 256, 3), 3, "none", "none", -1) == False
        )


class TestPlotParametersNode:
    """Test the Plot Parameters node."""

    @pytest.fixture
    def node(self):
        """Create a node instance."""
        return PlotParametersNode()

    @pytest.fixture
    def mock_images(self):
        """Create mock images tensor."""
        return torch.rand(4, 256, 256, 3)

    @pytest.fixture
    def mock_params(self):
        """Create mock parameters."""
        return [
            {
                "time": 2.0,
                "seed": 1,
                "steps": 20,
                "width": 256,
                "height": 256,
                "sampler": "euler",
                "scheduler": "normal",
                "guidance": 7.0,
                "denoise": 1.0,
                "max_shift": 1.0,
                "base_shift": 0.5,
            }
            for i in range(4)
        ]

    def test_input_types(self):
        """Test that INPUT_TYPES returns correct structure."""
        input_types = PlotParametersNode.INPUT_TYPES()
        assert "required" in input_types

        required = input_types["required"]
        assert "images" in required
        assert "params" in required
        assert "order_by" in required
        assert "cols_value" in required
        assert "cols_num" in required
        assert "add_prompt" in required
        assert "add_params" in required

    def test_plot_parameters_basic(self, node, mock_images, mock_params):
        """Test basic plot creation."""
        with patch(
            "kikotools.tools.xyz_helpers.plot_sampler_params.node.ImageFont.truetype"
        ):
            result = node.plot_parameters(
                mock_images,
                mock_params,
                order_by="none",
                cols_value="none",
                cols_num=-1,
                add_prompt="false",
                add_params="false",
            )

            assert isinstance(result, tuple)
            assert len(result) == 1
            assert isinstance(result[0], torch.Tensor)

    def test_node_properties(self):
        """Test node properties."""
        assert PlotParametersNode.CATEGORY == "ComfyAssets/🧰 xyz-helpers"
        assert PlotParametersNode.FUNCTION == "plot_parameters"
        assert PlotParametersNode.RETURN_TYPES == ("IMAGE",)
        assert PlotParametersNode.RETURN_NAMES == ("image",)
