"""XYZ Plot Controller node implementation."""

from typing import Dict, List, Any, Tuple, Optional
import json

from ..utils.constants import AxisType, NUMERIC_DEFAULTS
from ..utils.helpers import (
    parse_value_string, generate_axis_labels, calculate_grid_dimensions, create_unique_id
)
from .execution import execution_manager


class XYZPlotController:
    """Main configuration node for XYZ grid plotting."""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # X Axis configuration
                "x_axis_type": (AxisType.choices(), {"default": AxisType.NONE.value}),
                "x_values": ("STRING", {"default": "", "multiline": True}),
                "x_label_prefix": ("STRING", {"default": ""}),
                
                # Y Axis configuration  
                "y_axis_type": (AxisType.choices(), {"default": AxisType.NONE.value}),
                "y_values": ("STRING", {"default": "", "multiline": True}),
                "y_label_prefix": ("STRING", {"default": ""}),
            },
            "optional": {
                # Z Axis configuration (optional)
                "z_axis_type": (AxisType.choices(), {"default": AxisType.NONE.value}),
                "z_values": ("STRING", {"default": "", "multiline": True}),
                "z_label_prefix": ("STRING", {"default": ""}),
                
                # Label formatting
                "include_param_name": ("BOOLEAN", {"default": True}),
                "value_only_labels": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("XYZ_GRID", "STRING", "STRING", "STRING", "INT", "INT", "INT", "STRING")
    RETURN_NAMES = ("grid_data", "x_value", "y_value", "z_value", "x_index", "y_index", "z_index", "batch_id")
    FUNCTION = "configure_grid"
    CATEGORY = "ComfyAssets/XYZ Grid"
    
    def __init__(self):
        self.unique_id = None  # Set by ComfyUI
        
    def configure_grid(self, x_axis_type, x_values, x_label_prefix,
                      y_axis_type, y_values, y_label_prefix,
                      z_axis_type="none", z_values="", z_label_prefix="",
                      include_param_name=True, value_only_labels=False):
        """Configure and prepare grid generation."""
        
        # Parse axis types
        x_type = AxisType(x_axis_type) if x_axis_type != "none" else None
        y_type = AxisType(y_axis_type) if y_axis_type != "none" else None
        z_type = AxisType(z_axis_type) if z_axis_type != "none" else None
        
        # Parse values for each axis
        x_vals = parse_value_string(x_values, x_type) if x_type else [""]
        y_vals = parse_value_string(y_values, y_type) if y_type else [""]
        z_vals = parse_value_string(z_values, z_type) if z_type else [""]
        
        # Validate we have at least one axis configured
        if not x_type and not y_type:
            raise ValueError("At least one axis (X or Y) must be configured")
        
        # Calculate grid dimensions
        dims = calculate_grid_dimensions(len(x_vals), len(y_vals), len(z_vals))
        
        # Generate labels
        x_labels = self._generate_labels(x_vals, x_type, x_label_prefix, include_param_name, value_only_labels)
        y_labels = self._generate_labels(y_vals, y_type, y_label_prefix, include_param_name, value_only_labels)
        z_labels = self._generate_labels(z_vals, z_type, z_label_prefix, include_param_name, value_only_labels)
        
        # Create batch ID
        batch_id = create_unique_id()
        
        # Prepare grid configuration
        grid_config = {
            "batch_id": batch_id,
            "axes": {
                "x": {"type": x_type, "values": x_vals, "labels": x_labels},
                "y": {"type": y_type, "values": y_vals, "labels": y_labels},
                "z": {"type": z_type, "values": z_vals, "labels": z_labels},
            },
            "dimensions": dims,
            "total_images": dims["total_images"],
            "current_index": 0,
        }
        
        # Get current values from execution manager
        x_val, y_val, z_val, x_idx, y_idx, z_idx = execution_manager.get_current_values(
            batch_id, x_vals, y_vals, z_vals
        )
        
        # Format output values based on type
        x_output = self._format_output_value(x_val, x_type)
        y_output = self._format_output_value(y_val, y_type)
        z_output = self._format_output_value(z_val, z_type)
        
        return (grid_config, x_output, y_output, z_output, x_idx, y_idx, z_idx, batch_id)
    
    def _generate_labels(self, values: List[Any], axis_type: Optional[AxisType], 
                        prefix: str, include_param: bool, value_only: bool) -> List[str]:
        """Generate labels for axis values."""
        if not values or not axis_type:
            return []
        
        if value_only:
            # Just use values as labels
            return generate_axis_labels(values, axis_type, "")
        elif include_param and not prefix:
            # Use parameter name as prefix
            param_names = AxisType.display_names()
            prefix = param_names.get(axis_type, "") + ": "
        
        return generate_axis_labels(values, axis_type, prefix)
    
    def _format_output_value(self, value: Any, axis_type: Optional[AxisType]) -> str:
        """Format value for output based on axis type."""
        if not axis_type:
            return ""
        
        # Return appropriate type based on what nodes expect
        if axis_type in (AxisType.MODEL, AxisType.VAE, AxisType.LORA, 
                        AxisType.SAMPLER, AxisType.SCHEDULER, AxisType.PROMPT):
            return str(value)
        else:
            # Numeric types - return as string but nodes can convert
            return str(value)
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Force re-execution for grid iterations."""
        # This ensures node re-executes for each grid cell
        return float("nan")