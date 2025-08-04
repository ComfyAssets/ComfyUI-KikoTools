"""Tests for parameter converters."""

import pytest
from kikotools.tools.xyz_grid.utils.constants import AxisType
from kikotools.tools.xyz_grid.utils.converters import ParameterConverter, OutputConnector


class TestParameterConverter:
    """Test parameter value conversion."""
    
    def test_convert_string_types(self):
        """Test conversion of string-based parameters."""
        assert ParameterConverter.convert_value("model.ckpt", AxisType.MODEL) == "model.ckpt"
        assert ParameterConverter.convert_value("euler", AxisType.SAMPLER) == "euler"
        assert ParameterConverter.convert_value("My prompt", AxisType.PROMPT) == "My prompt"
    
    def test_convert_integer_types(self):
        """Test conversion of integer parameters."""
        assert ParameterConverter.convert_value("20", AxisType.STEPS) == 20
        assert ParameterConverter.convert_value("3", AxisType.CLIP_SKIP) == 3
        assert ParameterConverter.convert_value("12345", AxisType.SEED) == 12345
        
        # Test float to int conversion
        assert ParameterConverter.convert_value("20.5", AxisType.STEPS) == 20
        assert ParameterConverter.convert_value(20.7, AxisType.STEPS) == 20
    
    def test_convert_float_types(self):
        """Test conversion of float parameters."""
        assert ParameterConverter.convert_value("7.5", AxisType.CFG_SCALE) == 7.5
        assert ParameterConverter.convert_value("3.5", AxisType.FLUX_GUIDANCE) == 3.5
        assert ParameterConverter.convert_value("0.8", AxisType.DENOISE) == 0.8
        
        # Test integer to float
        assert ParameterConverter.convert_value(7, AxisType.CFG_SCALE) == 7.0
    
    def test_convert_invalid_values(self):
        """Test conversion of invalid values."""
        # Invalid integers default to 0
        assert ParameterConverter.convert_value("abc", AxisType.STEPS) == 0
        assert ParameterConverter.convert_value("", AxisType.STEPS) == 0
        
        # Invalid floats default to 0.0
        assert ParameterConverter.convert_value("xyz", AxisType.CFG_SCALE) == 0.0
        assert ParameterConverter.convert_value(None, AxisType.CFG_SCALE) == 0.0
    
    def test_format_for_display(self):
        """Test display formatting."""
        # Model names strip extension
        assert ParameterConverter.format_for_display("model.safetensors", AxisType.MODEL) == "model"
        assert ParameterConverter.format_for_display("path/to/checkpoint.ckpt", AxisType.MODEL) == "checkpoint"
        
        # Floats format with one decimal
        assert ParameterConverter.format_for_display(7.5, AxisType.CFG_SCALE) == "7.5"
        assert ParameterConverter.format_for_display(10.0, AxisType.CFG_SCALE) == "10.0"
        
        # Large numbers get commas
        assert ParameterConverter.format_for_display(1234567, AxisType.SEED) == "1,234,567"
        
        # Long prompts truncate
        long_text = "This is a very long prompt that exceeds the display limit"
        formatted = ParameterConverter.format_for_display(long_text, AxisType.PROMPT)
        assert len(formatted) <= 28  # 25 + "..."
    
    def test_get_output_type(self):
        """Test output type detection."""
        # String types
        assert ParameterConverter.get_output_type(AxisType.MODEL) == "STRING"
        assert ParameterConverter.get_output_type(AxisType.SAMPLER) == "STRING"
        assert ParameterConverter.get_output_type(AxisType.PROMPT) == "STRING"
        
        # Integer types
        assert ParameterConverter.get_output_type(AxisType.STEPS) == "INT"
        assert ParameterConverter.get_output_type(AxisType.CLIP_SKIP) == "INT"
        assert ParameterConverter.get_output_type(AxisType.SEED) == "INT"
        
        # Float types
        assert ParameterConverter.get_output_type(AxisType.CFG_SCALE) == "FLOAT"
        assert ParameterConverter.get_output_type(AxisType.FLUX_GUIDANCE) == "FLOAT"
        assert ParameterConverter.get_output_type(AxisType.DENOISE) == "FLOAT"
    
    def test_validate_values(self):
        """Test value validation."""
        # Valid values
        assert ParameterConverter.validate_value(20, AxisType.STEPS) == (True, None)
        assert ParameterConverter.validate_value(7.5, AxisType.CFG_SCALE) == (True, None)
        assert ParameterConverter.validate_value(0.5, AxisType.DENOISE) == (True, None)
        
        # Invalid values
        valid, msg = ParameterConverter.validate_value(-5, AxisType.STEPS)
        assert not valid
        assert "positive" in msg
        
        valid, msg = ParameterConverter.validate_value(-2.5, AxisType.CFG_SCALE)
        assert not valid
        assert "non-negative" in msg
        
        valid, msg = ParameterConverter.validate_value(1.5, AxisType.DENOISE)
        assert not valid
        assert "between 0 and 1" in msg


class TestOutputConnector:
    """Test output connection information."""
    
    def test_get_connection_info(self):
        """Test connection info for different parameter types."""
        # Model connection
        info = OutputConnector.get_connection_info(AxisType.MODEL)
        assert info["target_node"] == "CheckpointLoaderSimple"
        assert info["target_input"] == "ckpt_name"
        assert info["type"] == "STRING"
        
        # Sampler connection
        info = OutputConnector.get_connection_info(AxisType.SAMPLER)
        assert info["target_node"] == "KSampler"
        assert info["target_input"] == "sampler_name"
        
        # CFG connection
        info = OutputConnector.get_connection_info(AxisType.CFG_SCALE)
        assert info["target_node"] == "KSampler"
        assert info["target_input"] == "cfg"
        assert info["type"] == "FLOAT"
        
        # Prompt connection
        info = OutputConnector.get_connection_info(AxisType.PROMPT)
        assert info["target_node"] == "CLIPTextEncode"
        assert info["target_input"] == "text"