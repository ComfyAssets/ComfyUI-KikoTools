"""Tests for Flux Sampler Params node."""

import pytest
from unittest.mock import Mock, MagicMock
from kikotools.tools.xyz_helpers.flux_sampler_params import FluxSamplerParamsNode
from kikotools.tools.xyz_helpers.flux_sampler_params.logic import (
    parse_string_to_list,
    parse_seed_string,
    parse_sampler_string,
    parse_scheduler_string,
    get_default_flux_params,
    create_batch_params,
    process_conditioning_input,
    validate_flux_params,
)


class TestFluxSamplerParamsLogic:
    """Test the logic functions for Flux Sampler Params."""

    def test_parse_string_to_list(self):
        """Test parsing comma-separated strings to lists."""
        assert parse_string_to_list("1.0, 2.5, 3.7") == [1.0, 2.5, 3.7]
        assert parse_string_to_list("5") == [5.0]
        assert parse_string_to_list("") == []
        assert parse_string_to_list("1.0, invalid, 3.0") == [1.0, 3.0]

    def test_parse_seed_string(self):
        """Test parsing seed strings."""
        seeds = parse_seed_string("123, 456, 789")
        assert seeds == [123, 456, 789]

        # Test with ? for random
        seeds = parse_seed_string("123, ?")
        assert len(seeds) == 2
        assert seeds[0] == 123
        assert 0 <= seeds[1] <= 999999

        # Test with newlines
        seeds = parse_seed_string("123\n456\n789")
        assert seeds == [123, 456, 789]

    def test_parse_sampler_string(self):
        """Test parsing sampler strings."""
        available = ["euler", "dpmpp_2m", "ddim", "uni_pc"]

        # Test normal selection
        result = parse_sampler_string("euler, ddim", available)
        assert result == ["euler", "ddim"]

        # Test wildcard
        result = parse_sampler_string("*", available)
        assert result == available

        # Test exclusion
        result = parse_sampler_string("!euler, ddim", available)
        assert "euler" not in result
        assert "ddim" not in result
        assert "dpmpp_2m" in result
        assert "uni_pc" in result

    def test_parse_scheduler_string(self):
        """Test parsing scheduler strings."""
        available = ["normal", "karras", "simple", "exponential"]

        # Test normal selection
        result = parse_scheduler_string("normal, simple", available)
        assert result == ["normal", "simple"]

        # Test wildcard
        result = parse_scheduler_string("*", available)
        assert result == available

        # Test exclusion
        result = parse_scheduler_string("!normal", available)
        assert "normal" not in result
        assert "karras" in result

    def test_get_default_flux_params(self):
        """Test getting default Flux parameters."""
        # Test Schnell defaults
        params = get_default_flux_params(is_schnell=True)
        assert params["steps"] == 4
        assert params["max_shift"] == 0
        assert params["base_shift"] == 1.0

        # Test regular Flux defaults
        params = get_default_flux_params(is_schnell=False)
        assert params["steps"] == 20
        assert params["max_shift"] == 1.15
        assert params["base_shift"] == 0.5

    def test_create_batch_params(self):
        """Test creating batch parameters."""
        total, params = create_batch_params(
            seeds=[1, 2],
            samplers=["euler"],
            schedulers=["normal"],
            steps=[20],
            guidances=[7.0],
            max_shifts=[1.0],
            base_shifts=[0.5],
            denoises=[1.0],
            conditioning_count=1,
            lora_strength_count=1,
        )

        assert total == 2  # 2 seeds * 1 of everything else
        assert len(params) == 2
        assert params[0]["seed"] == 1
        assert params[1]["seed"] == 2

    def test_process_conditioning_input(self):
        """Test processing conditioning input."""
        # Test dict input
        cond_dict = {
            "text": ["prompt1", "prompt2"],
            "encoded": ["encoded1", "encoded2"],
        }
        text, encoded = process_conditioning_input(cond_dict)
        assert text == ["prompt1", "prompt2"]
        assert encoded == ["encoded1", "encoded2"]

        # Test regular conditioning
        regular_cond = "regular_conditioning"
        text, encoded = process_conditioning_input(regular_cond)
        assert text is None
        assert encoded == ["regular_conditioning"]

    def test_validate_flux_params(self):
        """Test validating Flux parameters."""
        assert validate_flux_params("20", "7.0", "1.15", "0.5", "1.0") == True
        assert validate_flux_params("20, 30", "7.0, 8.0", "1.15", "0.5", "1.0") == True


class TestFluxSamplerParamsNode:
    """Test the Flux Sampler Params node."""

    @pytest.fixture
    def node(self):
        """Create a node instance."""
        return FluxSamplerParamsNode()

    @pytest.fixture
    def mock_model(self):
        """Create a mock model."""
        model = Mock()
        model.model = Mock()
        model.model.model_type = Mock()
        return model

    @pytest.fixture
    def mock_conditioning(self):
        """Create mock conditioning."""
        return {"text": ["test prompt"], "encoded": [Mock()]}

    @pytest.fixture
    def mock_latent(self):
        """Create mock latent."""
        latent = {"samples": Mock()}
        latent["samples"].shape = [1, 4, 64, 64]  # batch, channels, height, width
        return latent

    def test_input_types(self):
        """Test that INPUT_TYPES returns correct structure."""
        input_types = FluxSamplerParamsNode.INPUT_TYPES()
        assert "required" in input_types
        assert "optional" in input_types

        required = input_types["required"]
        assert "model" in required
        assert "conditioning" in required
        assert "latent_image" in required
        assert "seed" in required
        assert "sampler" in required
        assert "scheduler" in required
        assert "steps" in required
        assert "guidance" in required

        optional = input_types["optional"]
        assert "loras" in optional

    def test_node_properties(self):
        """Test node properties."""
        assert FluxSamplerParamsNode.CATEGORY == "🫶 ComfyAssets/🧰 xyz-helpers"
        assert FluxSamplerParamsNode.FUNCTION == "process_batch"
        assert FluxSamplerParamsNode.RETURN_TYPES == ("LATENT", "SAMPLER_PARAMS")
        assert FluxSamplerParamsNode.RETURN_NAMES == ("latent", "params")

    def test_init(self):
        """Test node initialization."""
        node = FluxSamplerParamsNode()
        assert node.lora_loader is None
        assert node.cached_lora == (None, None)
