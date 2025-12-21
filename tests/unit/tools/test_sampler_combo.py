"""Tests for Sampler Combo node."""

import pytest
from unittest.mock import patch
from kikotools.tools.sampler_combo.node import SamplerComboNode
from kikotools.tools.sampler_combo.logic import (
    validate_sampler_settings,
    get_sampler_combo,
    get_compatible_scheduler_suggestions,
    get_recommended_steps_range,
    get_recommended_cfg_range,
    get_sampler_info,
    SAMPLERS,
    SCHEDULERS,
)


class TestSamplerComboLogic:
    """Test cases for sampler combo logic functions."""

    def test_validate_sampler_settings_valid(self):
        """Test validation with valid settings."""
        assert validate_sampler_settings("euler", "normal", 20, 7.0) is True
        assert validate_sampler_settings("dpmpp_2m", "karras", 15, 8.5) is True
        assert validate_sampler_settings("ddim", "ddim_uniform", 30, 6.0) is True

    def test_validate_sampler_settings_invalid_sampler(self):
        """Test validation with invalid sampler."""
        assert validate_sampler_settings("invalid_sampler", "normal", 20, 7.0) is False

    def test_validate_sampler_settings_invalid_scheduler(self):
        """Test validation with invalid scheduler."""
        assert validate_sampler_settings("euler", "invalid_scheduler", 20, 7.0) is False

    def test_validate_sampler_settings_invalid_steps(self):
        """Test validation with invalid steps."""
        assert validate_sampler_settings("euler", "normal", 0, 7.0) is False
        assert validate_sampler_settings("euler", "normal", 1001, 7.0) is False
        assert validate_sampler_settings("euler", "normal", -5, 7.0) is False

    def test_validate_sampler_settings_invalid_cfg(self):
        """Test validation with invalid CFG."""
        assert validate_sampler_settings("euler", "normal", 20, -1.0) is False
        assert validate_sampler_settings("euler", "normal", 20, 31.0) is False

    def test_get_sampler_combo_valid(self):
        """Test getting sampler combo with valid inputs."""
        result = get_sampler_combo("euler", "normal", 20, 7.0)
        assert result == ("euler", "normal", 20, 7.0)

        result = get_sampler_combo("dpmpp_2m", "karras", 25, 8.5)
        assert result == ("dpmpp_2m", "karras", 25, 8.5)

    def test_get_sampler_combo_invalid_returns_defaults(self):
        """Test that invalid inputs return safe defaults."""
        result = get_sampler_combo("invalid", "normal", 20, 7.0)
        assert result == ("euler", "normal", 20, 7.0)

        result = get_sampler_combo("euler", "invalid", 20, 7.0)
        assert result == ("euler", "normal", 20, 7.0)

    def test_get_sampler_combo_sanitizes_values(self):
        """Test that values are sanitized to valid ranges."""
        # Test steps clamping
        result = get_sampler_combo("euler", "normal", 0, 7.0)
        assert result[2] >= 1  # steps should be at least 1

        result = get_sampler_combo("euler", "normal", 1500, 7.0)
        assert result[2] <= 1000  # steps should be at most 1000

        # Test CFG clamping
        result = get_sampler_combo("euler", "normal", 20, -5.0)
        assert result[3] >= 0.0  # CFG should be at least 0

        result = get_sampler_combo("euler", "normal", 20, 50.0)
        assert result[3] <= 30.0  # CFG should be at most 30

    def test_get_compatible_scheduler_suggestions(self):
        """Test getting scheduler suggestions for different samplers."""
        suggestions = get_compatible_scheduler_suggestions("euler")
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        assert "normal" in suggestions

        suggestions = get_compatible_scheduler_suggestions("ddim")
        assert "ddim_uniform" in suggestions

        # Test unknown sampler returns defaults
        suggestions = get_compatible_scheduler_suggestions("unknown_sampler")
        assert "normal" in suggestions
        assert "karras" in suggestions

    def test_get_recommended_steps_range(self):
        """Test getting recommended steps range for samplers."""
        min_steps, max_steps, default_steps = get_recommended_steps_range("euler")
        assert isinstance(min_steps, int)
        assert isinstance(max_steps, int)
        assert isinstance(default_steps, int)
        assert min_steps <= default_steps <= max_steps
        assert min_steps > 0

        # Test unknown sampler returns defaults
        min_steps, max_steps, default_steps = get_recommended_steps_range("unknown")
        assert min_steps == 10
        assert max_steps == 50
        assert default_steps == 20

    def test_get_recommended_cfg_range(self):
        """Test getting recommended CFG range for samplers."""
        min_cfg, max_cfg, default_cfg = get_recommended_cfg_range("euler")
        assert isinstance(min_cfg, float)
        assert isinstance(max_cfg, float)
        assert isinstance(default_cfg, float)
        assert min_cfg <= default_cfg <= max_cfg
        assert min_cfg >= 0.0

        # Test unknown sampler returns defaults
        min_cfg, max_cfg, default_cfg = get_recommended_cfg_range("unknown")
        assert min_cfg == 1.0
        assert max_cfg == 20.0
        assert default_cfg == 7.0

    def test_get_sampler_info(self):
        """Test getting sampler information."""
        info = get_sampler_info()
        assert isinstance(info, dict)
        assert "samplers" in info
        assert "schedulers" in info
        assert "sampler_count" in info
        assert "scheduler_count" in info
        assert info["sampler_count"] == len(SAMPLERS)
        assert info["scheduler_count"] == len(SCHEDULERS)


class TestSamplerComboNode:
    """Test cases for SamplerComboNode."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = SamplerComboNode()

    def test_input_types_structure(self):
        """Test that INPUT_TYPES returns correct structure."""
        input_types = SamplerComboNode.INPUT_TYPES()

        assert "required" in input_types
        required = input_types["required"]

        # Check all required inputs are present
        assert "sampler_name" in required
        assert "scheduler" in required
        assert "steps" in required
        assert "cfg" in required

        # Check sampler input structure
        sampler_input = required["sampler_name"]
        assert sampler_input[0] == SAMPLERS
        assert isinstance(sampler_input[1], dict)
        assert "default" in sampler_input[1]
        assert "tooltip" in sampler_input[1]

        # Check scheduler input structure
        scheduler_input = required["scheduler"]
        assert scheduler_input[0] == SCHEDULERS
        assert isinstance(scheduler_input[1], dict)

        # Check steps input structure
        steps_input = required["steps"]
        assert steps_input[0] == "INT"
        assert steps_input[1]["min"] == 1
        assert steps_input[1]["max"] == 100

        # Check CFG input structure
        cfg_input = required["cfg"]
        assert cfg_input[0] == "FLOAT"
        assert cfg_input[1]["min"] == 0.0
        assert cfg_input[1]["max"] == 20.0

    def test_return_types_structure(self):
        """Test that return types are correctly defined."""
        assert SamplerComboNode.RETURN_TYPES == (SAMPLERS, SCHEDULERS, "INT", "FLOAT")
        assert SamplerComboNode.RETURN_NAMES == (
            "sampler_name",
            "scheduler",
            "steps",
            "cfg",
        )
        assert SamplerComboNode.FUNCTION == "get_sampler_combo"
        assert SamplerComboNode.CATEGORY == "🫶 ComfyAssets/🌀 Samplers"

    def test_get_sampler_combo_valid_inputs(self):
        """Test get_sampler_combo with valid inputs."""
        result = self.node.get_sampler_combo("euler", "normal", 20, 7.0)
        assert result == ("euler", "normal", 20, 7.0)

        result = self.node.get_sampler_combo("dpmpp_2m", "karras", 15, 8.5)
        assert result == ("dpmpp_2m", "karras", 15, 8.5)

    def test_get_sampler_combo_invalid_inputs_returns_defaults(self):
        """Test that invalid inputs return safe defaults."""
        with patch.object(self.node, "handle_error") as mock_error:
            mock_error.side_effect = ValueError("Invalid settings")

            try:
                result = self.node.get_sampler_combo("invalid", "normal", 20, 7.0)
            except ValueError:
                pass  # Expected when handle_error raises

        # Test with exception handling bypassed
        with patch(
            "kikotools.tools.sampler_combo.node.validate_sampler_settings",
            return_value=False,
        ):
            result = self.node.get_sampler_combo("invalid", "normal", 20, 7.0)
            assert result == ("euler", "normal", 20, 7.0)

    def test_validate_inputs_valid(self):
        """Test input validation with valid inputs."""
        # Should not raise any exception
        self.node.validate_inputs("euler", "normal", 20, 7.0)

    def test_validate_inputs_invalid(self):
        """Test input validation with invalid inputs."""
        with pytest.raises(ValueError):
            self.node.validate_inputs("invalid", "normal", 20, 7.0)

    def test_get_scheduler_suggestions(self):
        """Test getting scheduler suggestions."""
        suggestions = self.node.get_scheduler_suggestions("euler")
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

        suggestions = self.node.get_scheduler_suggestions("ddim")
        assert "ddim_uniform" in suggestions

    def test_get_steps_recommendation(self):
        """Test getting steps recommendations."""
        rec = self.node.get_steps_recommendation("euler")
        assert isinstance(rec, dict)
        assert "min" in rec
        assert "max" in rec
        assert "default" in rec
        assert "recommendation" in rec

    def test_get_cfg_recommendation(self):
        """Test getting CFG recommendations."""
        rec = self.node.get_cfg_recommendation("euler")
        assert isinstance(rec, dict)
        assert "min" in rec
        assert "max" in rec
        assert "default" in rec
        assert "recommendation" in rec

    def test_get_combo_analysis(self):
        """Test getting combo analysis."""
        analysis = self.node.get_combo_analysis("euler", "normal", 20, 7.0)
        assert isinstance(analysis, dict)
        assert "sampler" in analysis
        assert "scheduler" in analysis
        assert "steps" in analysis
        assert "cfg" in analysis
        assert "valid" in analysis
        assert "scheduler_suggestions" in analysis
        assert "scheduler_compatible" in analysis
        assert "steps_optimal" in analysis
        assert "cfg_optimal" in analysis

    def test_get_available_samplers(self):
        """Test getting available samplers."""
        samplers = SamplerComboNode.get_available_samplers()
        assert isinstance(samplers, list)
        assert len(samplers) > 0
        assert "euler" in samplers

    def test_get_available_schedulers(self):
        """Test getting available schedulers."""
        schedulers = SamplerComboNode.get_available_schedulers()
        assert isinstance(schedulers, list)
        assert len(schedulers) > 0
        assert "normal" in schedulers

    def test_string_representations(self):
        """Test string representations of the node."""
        str_repr = str(self.node)
        assert "SamplerComboNode" in str_repr
        assert "samplers=" in str_repr
        assert "schedulers=" in str_repr

        repr_str = repr(self.node)
        assert "SamplerComboNode" in repr_str
        assert "category=" in repr_str
        assert "function=" in repr_str

    def test_node_inheritance(self):
        """Test that node properly inherits from base class."""
        from kikotools.base.base_node import ComfyAssetsBaseNode

        assert isinstance(self.node, ComfyAssetsBaseNode)
        assert hasattr(self.node, "validate_inputs")
        assert hasattr(self.node, "handle_error")
        assert hasattr(self.node, "log_info")


class TestSamplerComboIntegration:
    """Integration tests for Sampler Combo functionality."""

    def test_full_workflow_valid_settings(self):
        """Test complete workflow with valid settings."""
        node = SamplerComboNode()

        # Test with different sampler/scheduler combinations
        test_cases = [
            ("euler", "normal", 20, 7.0),
            ("dpmpp_2m", "karras", 15, 8.0),
            ("euler_ancestral", "exponential", 25, 9.0),
            ("ddim", "ddim_uniform", 30, 6.0),
        ]

        for sampler, scheduler, steps, cfg in test_cases:
            result = node.get_sampler_combo(sampler, scheduler, steps, cfg)
            assert result == (sampler, scheduler, steps, cfg)

    def test_recommendation_compatibility(self):
        """Test that recommendations are compatible with actual functionality."""
        node = SamplerComboNode()

        for sampler in SAMPLERS[:5]:  # Test first 5 samplers
            suggestions = node.get_scheduler_suggestions(sampler)
            steps_rec = node.get_steps_recommendation(sampler)
            cfg_rec = node.get_cfg_recommendation(sampler)

            # Test that recommendations work with the node
            for scheduler in suggestions[:2]:  # Test first 2 suggestions
                result = node.get_sampler_combo(
                    sampler, scheduler, steps_rec["default"], cfg_rec["default"]
                )
                assert result[0] == sampler
                assert result[1] == scheduler
                assert result[2] == steps_rec["default"]
                assert result[3] == cfg_rec["default"]

    def test_error_recovery(self):
        """Test error recovery with malformed inputs."""
        node = SamplerComboNode()

        # These should all return safe defaults due to error handling
        with patch(
            "kikotools.tools.sampler_combo.logic.validate_sampler_settings",
            side_effect=Exception("Simulated error"),
        ):
            result = node.get_sampler_combo("euler", "normal", 20, 7.0)
            assert result == ("euler", "normal", 20, 7.0)  # Safe defaults
