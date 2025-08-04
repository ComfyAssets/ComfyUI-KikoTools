"""Value converters for different parameter types."""

from typing import Any, Union, List, Optional
from .constants import AxisType


class ParameterConverter:
    """Converts axis values to appropriate types for ComfyUI nodes."""
    
    @staticmethod
    def convert_value(value: Any, axis_type: AxisType) -> Any:
        """Convert a value based on its axis type.
        
        Args:
            value: Raw value from axis configuration
            axis_type: Type of parameter
            
        Returns:
            Converted value suitable for ComfyUI node input
        """
        if not axis_type or axis_type == AxisType.NONE:
            return value
        
        # String-based parameters
        if axis_type in (AxisType.MODEL, AxisType.VAE, AxisType.LORA, 
                        AxisType.SAMPLER, AxisType.SCHEDULER, AxisType.PROMPT):
            return str(value)
        
        # Integer parameters
        elif axis_type in (AxisType.STEPS, AxisType.CLIP_SKIP, AxisType.SEED):
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return 0
        
        # Float parameters
        elif axis_type in (AxisType.CFG_SCALE, AxisType.FLUX_GUIDANCE, AxisType.DENOISE):
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0.0
        
        return value
    
    @staticmethod
    def format_for_display(value: Any, axis_type: AxisType) -> str:
        """Format a value for display in labels.
        
        Args:
            value: Value to format
            axis_type: Type of parameter
            
        Returns:
            Formatted string for display
        """
        if axis_type == AxisType.MODEL:
            # Remove extension and path
            import os
            return os.path.splitext(os.path.basename(str(value)))[0]
        
        elif axis_type == AxisType.PROMPT:
            # Truncate long prompts
            s = str(value)
            return s[:25] + "..." if len(s) > 25 else s
        
        elif axis_type in (AxisType.CFG_SCALE, AxisType.FLUX_GUIDANCE, AxisType.DENOISE):
            # Format floats nicely
            return f"{float(value):.1f}"
        
        elif axis_type == AxisType.SEED:
            # Format large numbers
            return f"{int(value):,}"
        
        return str(value)
    
    @staticmethod
    def get_output_type(axis_type: AxisType) -> str:
        """Get the ComfyUI output type for an axis type.
        
        Args:
            axis_type: Type of parameter
            
        Returns:
            ComfyUI type string (e.g., "STRING", "INT", "FLOAT")
        """
        if axis_type in (AxisType.MODEL, AxisType.VAE, AxisType.LORA,
                        AxisType.SAMPLER, AxisType.SCHEDULER, AxisType.PROMPT):
            return "STRING"
        
        elif axis_type in (AxisType.STEPS, AxisType.CLIP_SKIP, AxisType.SEED):
            return "INT"
        
        elif axis_type in (AxisType.CFG_SCALE, AxisType.FLUX_GUIDANCE, AxisType.DENOISE):
            return "FLOAT"
        
        return "STRING"
    
    @staticmethod
    def validate_value(value: Any, axis_type: AxisType) -> tuple[bool, Optional[str]]:
        """Validate a value for an axis type.
        
        Args:
            value: Value to validate
            axis_type: Type of parameter
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if axis_type in (AxisType.STEPS, AxisType.CLIP_SKIP):
            try:
                val = int(float(value))
                if val < 1:
                    return False, f"Value must be positive (got {val})"
            except:
                return False, f"Invalid integer value: {value}"
        
        elif axis_type == AxisType.CFG_SCALE:
            try:
                val = float(value)
                if val < 0:
                    return False, f"CFG scale must be non-negative (got {val})"
            except:
                return False, f"Invalid float value: {value}"
        
        elif axis_type == AxisType.DENOISE:
            try:
                val = float(value)
                if not 0 <= val <= 1:
                    return False, f"Denoise must be between 0 and 1 (got {val})"
            except:
                return False, f"Invalid float value: {value}"
        
        return True, None


class OutputConnector:
    """Handles connecting XYZ outputs to various node inputs."""
    
    @staticmethod
    def get_connection_info(axis_type: AxisType) -> dict:
        """Get information about how to connect this axis type.
        
        Args:
            axis_type: Type of parameter
            
        Returns:
            Dict with connection information
        """
        connection_map = {
            AxisType.MODEL: {
                "target_node": "CheckpointLoaderSimple",
                "target_input": "ckpt_name",
                "type": "STRING"
            },
            AxisType.VAE: {
                "target_node": "VAELoader",
                "target_input": "vae_name",
                "type": "STRING"
            },
            AxisType.SAMPLER: {
                "target_node": "KSampler",
                "target_input": "sampler_name",
                "type": "combo"
            },
            AxisType.SCHEDULER: {
                "target_node": "KSampler",
                "target_input": "scheduler",
                "type": "combo"
            },
            AxisType.CFG_SCALE: {
                "target_node": "KSampler",
                "target_input": "cfg",
                "type": "FLOAT"
            },
            AxisType.STEPS: {
                "target_node": "KSampler",
                "target_input": "steps",
                "type": "INT"
            },
            AxisType.SEED: {
                "target_node": "KSampler",
                "target_input": "seed",
                "type": "INT"
            },
            AxisType.DENOISE: {
                "target_node": "KSampler",
                "target_input": "denoise",
                "type": "FLOAT"
            },
            AxisType.CLIP_SKIP: {
                "target_node": "CLIPSetLastLayer",
                "target_input": "stop_at_clip_layer",
                "type": "INT"
            },
            AxisType.LORA: {
                "target_node": "LoraLoader",
                "target_input": "lora_name",
                "type": "STRING"
            },
            AxisType.PROMPT: {
                "target_node": "CLIPTextEncode",
                "target_input": "text",
                "type": "STRING"
            },
            AxisType.FLUX_GUIDANCE: {
                "target_node": "FluxGuidance",  # Hypothetical node
                "target_input": "guidance",
                "type": "FLOAT"
            }
        }
        
        return connection_map.get(axis_type, {
            "target_node": "Unknown",
            "target_input": "value",
            "type": "STRING"
        })