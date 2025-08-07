"""Tests for Scheduler Select Helper node."""

import pytest
from kikotools.tools.xyz_helpers.scheduler_select_helper import (
    SchedulerSelectHelperNode,
)
from kikotools.tools.xyz_helpers.scheduler_select_helper.logic import (
    process_scheduler_selection,
    validate_scheduler_names,
    get_scheduler_categories,
    get_default_schedulers,
    get_scheduler_description,
)


class TestSchedulerSelectHelperLogic:
    """Test the logic functions for Scheduler Select Helper."""

    def test_process_scheduler_selection_with_selections(self):
        """Test processing scheduler selections."""
        result = process_scheduler_selection(
            normal=True, karras=True, exponential=False, simple=True
        )
        assert result == "normal, karras, simple"

    def test_process_scheduler_selection_no_selections(self):
        """Test with no selections."""
        result = process_scheduler_selection(normal=False, karras=False)
        assert result == ""

    def test_validate_scheduler_names(self):
        """Test validating scheduler names."""
        valid = validate_scheduler_names("normal, karras, invalid_scheduler")
        assert "normal" in valid
        assert "karras" in valid
        assert "invalid_scheduler" not in valid

    def test_get_scheduler_categories(self):
        """Test getting scheduler categories."""
        categories = get_scheduler_categories()
        assert "Standard" in categories
        assert "Uniform" in categories
        assert "Advanced" in categories

    def test_get_default_schedulers(self):
        """Test getting default schedulers."""
        defaults = get_default_schedulers()
        assert len(defaults) > 0
        assert "normal" in defaults
        assert "karras" in defaults

    def test_get_scheduler_description(self):
        """Test getting scheduler descriptions."""
        desc = get_scheduler_description("karras")
        assert "Karras" in desc

        desc = get_scheduler_description("normal")
        assert "linear" in desc.lower()

        desc = get_scheduler_description("unknown")
        assert desc == "Custom scheduler"


class TestSchedulerSelectHelperNode:
    """Test the Scheduler Select Helper node."""

    @pytest.fixture
    def node(self):
        """Create a node instance."""
        return SchedulerSelectHelperNode()

    def test_input_types(self):
        """Test that INPUT_TYPES returns correct structure."""
        input_types = SchedulerSelectHelperNode.INPUT_TYPES()
        assert "required" in input_types

        # Check that schedulers are in required inputs
        required = input_types["required"]
        assert "normal" in required
        assert required["normal"][0] == "BOOLEAN"

    def test_select_schedulers_with_selections(self, node):
        """Test selecting schedulers."""
        result = node.select_schedulers(
            normal=True, karras=True, exponential=False, simple=True, beta=False
        )
        assert isinstance(result, tuple)
        assert len(result) == 1
        selected = result[0]
        assert "normal" in selected
        assert "karras" in selected
        assert "simple" in selected
        assert "exponential" not in selected

    def test_select_schedulers_no_selection(self, node):
        """Test with no schedulers selected."""
        result = node.select_schedulers(normal=False, karras=False)
        assert result == ("",)

    def test_node_properties(self):
        """Test node properties."""
        assert SchedulerSelectHelperNode.CATEGORY == "ComfyAssets/🧰 xyz-helpers"
        assert SchedulerSelectHelperNode.FUNCTION == "select_schedulers"
        assert SchedulerSelectHelperNode.RETURN_TYPES == ("STRING",)
        assert SchedulerSelectHelperNode.RETURN_NAMES == ("selected_schedulers",)
