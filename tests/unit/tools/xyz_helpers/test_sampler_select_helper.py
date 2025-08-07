"""Tests for Sampler Select Helper node."""

import pytest
from kikotools.tools.xyz_helpers.sampler_select_helper import SamplerSelectHelperNode
from kikotools.tools.xyz_helpers.sampler_select_helper.logic import (
    process_sampler_selection,
    validate_sampler_names,
    get_sampler_groups,
    get_default_samplers,
)


class TestSamplerSelectHelperLogic:
    """Test the logic functions for Sampler Select Helper."""

    def test_process_sampler_selection_with_selections(self):
        """Test processing sampler selections."""
        result = process_sampler_selection(
            euler=True, dpmpp_2m=True, ddim=False, uni_pc=True
        )
        assert result == "euler, dpmpp_2m, uni_pc"

    def test_process_sampler_selection_no_selections(self):
        """Test with no selections."""
        result = process_sampler_selection(euler=False, dpmpp_2m=False)
        assert result == ""

    def test_validate_sampler_names(self):
        """Test validating sampler names."""
        valid = validate_sampler_names("euler, dpmpp_2m, invalid_sampler")
        assert "euler" in valid
        assert "dpmpp_2m" in valid
        assert "invalid_sampler" not in valid

    def test_get_sampler_groups(self):
        """Test getting sampler groups."""
        groups = get_sampler_groups()
        assert "Euler" in groups
        assert "DPM" in groups
        assert "DPM++" in groups
        assert "Other" in groups

    def test_get_default_samplers(self):
        """Test getting default samplers."""
        defaults = get_default_samplers()
        assert len(defaults) > 0
        assert "euler" in defaults


class TestSamplerSelectHelperNode:
    """Test the Sampler Select Helper node."""

    @pytest.fixture
    def node(self):
        """Create a node instance."""
        return SamplerSelectHelperNode()

    def test_input_types(self):
        """Test that INPUT_TYPES returns correct structure."""
        input_types = SamplerSelectHelperNode.INPUT_TYPES()
        assert "required" in input_types

        # Check that samplers are in required inputs
        required = input_types["required"]
        assert "euler" in required
        assert required["euler"][0] == "BOOLEAN"

    def test_select_samplers_with_selections(self, node):
        """Test selecting samplers."""
        result = node.select_samplers(
            euler=True, dpmpp_2m=True, ddim=False, uni_pc=True, lms=False
        )
        assert isinstance(result, tuple)
        assert len(result) == 1
        selected = result[0]
        assert "euler" in selected
        assert "dpmpp_2m" in selected
        assert "uni_pc" in selected
        assert "ddim" not in selected

    def test_select_samplers_no_selection(self, node):
        """Test with no samplers selected."""
        result = node.select_samplers(euler=False, dpmpp_2m=False)
        assert result == ("",)

    def test_node_properties(self):
        """Test node properties."""
        assert SamplerSelectHelperNode.CATEGORY == "ComfyAssets/🧰 xyz-helpers"
        assert SamplerSelectHelperNode.FUNCTION == "select_samplers"
        assert SamplerSelectHelperNode.RETURN_TYPES == ("STRING",)
        assert SamplerSelectHelperNode.RETURN_NAMES == ("selected_samplers",)
