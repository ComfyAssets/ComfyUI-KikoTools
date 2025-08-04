"""Advanced XYZ Plot Controller with full parameter support."""

from typing import Dict, List, Any, Tuple, Optional, Union
import json

from ..utils.constants import AxisType, NUMERIC_DEFAULTS
from ..utils.helpers import (
    get_available_models, get_available_vaes, get_available_loras,
    get_sampler_names, get_scheduler_names, parse_value_string,
    generate_axis_labels, calculate_grid_dimensions, create_unique_id
)
from ..utils.converters import ParameterConverter, OutputConnector
from .execution import execution_manager
from .queue_manager import queue_manager


class XYZPlotControllerAdvanced:
    """Advanced XYZ Plot Controller with dynamic outputs."""
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get available options for dropdowns
        models = get_available_models()
        vaes = get_available_vaes()
        loras = get_available_loras()
        samplers = get_sampler_names()
        schedulers = get_scheduler_names()
        
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
                
                # Execution control
                "auto_queue": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                # Z Axis configuration (optional)
                "z_axis_type": (AxisType.choices(), {"default": AxisType.NONE.value}),
                "z_values": ("STRING", {"default": "", "multiline": True}),
                "z_label_prefix": ("STRING", {"default": ""}),
                
                # Label formatting
                "include_param_name": ("BOOLEAN", {"default": True}),
                "value_only_labels": ("BOOLEAN", {"default": False}),
                
                # Quick select dropdowns (helpers)
                "model_list": (["none"] + models, {"default": "none"}),
                "vae_list": (["none"] + vaes, {"default": "none"}),
                "lora_list": (["none"] + loras, {"default": "none"}),
                "sampler_list": (["none"] + samplers, {"default": "none"}),
                "scheduler_list": (["none"] + schedulers, {"default": "none"}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT",
            }
        }
    
    RETURN_TYPES = ("XYZ_GRID", "STRING", "INT", "FLOAT", "STRING", "INT", "FLOAT", "STRING", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("grid_data", 
                   "x_string", "x_int", "x_float",
                   "y_string", "y_int", "y_float", 
                   "z_string", "z_int", "z_float",
                   "batch_id")
    FUNCTION = "configure_grid"
    CATEGORY = "ComfyAssets/XYZ Grid"
    
    def __init__(self):
        self.unique_id = None
        self._execution_count = 0
        
    def configure_grid(self, x_axis_type, x_values, x_label_prefix,
                      y_axis_type, y_values, y_label_prefix,
                      auto_queue=True,
                      z_axis_type="none", z_values="", z_label_prefix="",
                      include_param_name=True, value_only_labels=False,
                      model_list="none", vae_list="none", lora_list="none",
                      sampler_list="none", scheduler_list="none",
                      unique_id=None, prompt=None):
        """Configure and prepare grid generation with advanced features."""
        
        # Use helper dropdowns to populate values if selected
        x_values = self._apply_quick_select(x_axis_type, x_values, 
                                          model_list, vae_list, lora_list, 
                                          sampler_list, scheduler_list)
        y_values = self._apply_quick_select(y_axis_type, y_values,
                                          model_list, vae_list, lora_list,
                                          sampler_list, scheduler_list)
        z_values = self._apply_quick_select(z_axis_type, z_values,
                                          model_list, vae_list, lora_list,
                                          sampler_list, scheduler_list)
        
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
            "auto_queue": auto_queue,
        }
        
        # Get current values from execution manager
        x_val, y_val, z_val, x_idx, y_idx, z_idx = execution_manager.get_current_values(
            batch_id, x_vals, y_vals, z_vals
        )
        
        # Convert values to appropriate types for each output
        x_outputs = self._convert_to_outputs(x_val, x_type)
        y_outputs = self._convert_to_outputs(y_val, y_type)
        z_outputs = self._convert_to_outputs(z_val, z_type)
        
        # Handle auto-queuing if enabled
        if auto_queue and unique_id and prompt:
            self._handle_auto_queue(batch_id, grid_config, unique_id, prompt)
        
        # Update current index in grid config
        grid_config["current_index"] = execution_manager.execution_states.get(
            batch_id, execution_manager.initialize_batch(batch_id, x_vals, y_vals, z_vals)
        ).current_iteration
        
        return (grid_config, 
                x_outputs[0], x_outputs[1], x_outputs[2],
                y_outputs[0], y_outputs[1], y_outputs[2],
                z_outputs[0], z_outputs[1], z_outputs[2],
                batch_id)
    
    def _apply_quick_select(self, axis_type: str, values: str, 
                           model: str, vae: str, lora: str, 
                           sampler: str, scheduler: str) -> str:
        """Apply quick select dropdown values if appropriate."""
        if values:  # If user already entered values, don't override
            return values
        
        # Map axis type to quick select value
        if axis_type == "model" and model != "none":
            return model
        elif axis_type == "vae" and vae != "none":
            return vae
        elif axis_type == "lora" and lora != "none":
            return lora
        elif axis_type == "sampler" and sampler != "none":
            return sampler
        elif axis_type == "scheduler" and scheduler != "none":
            return scheduler
        
        return values
    
    def _convert_to_outputs(self, value: Any, axis_type: Optional[AxisType]) -> Tuple[str, int, float]:
        """Convert value to all output types."""
        if not axis_type or value == "":
            return ("", 0, 0.0)
        
        # Convert using parameter converter
        converted = ParameterConverter.convert_value(value, axis_type)
        
        # Prepare outputs for all types
        str_val = str(converted)
        
        try:
            int_val = int(float(converted))
        except:
            int_val = 0
        
        try:
            float_val = float(converted)
        except:
            float_val = 0.0
        
        return (str_val, int_val, float_val)
    
    def _generate_labels(self, values: List[Any], axis_type: Optional[AxisType], 
                        prefix: str, include_param: bool, value_only: bool) -> List[str]:
        """Generate labels for axis values."""
        if not values or not axis_type:
            return []
        
        labels = []
        for value in values:
            if value_only:
                label = ParameterConverter.format_for_display(value, axis_type)
            else:
                label = ParameterConverter.format_for_display(value, axis_type)
                if include_param and not prefix:
                    param_names = AxisType.display_names()
                    param_prefix = param_names.get(axis_type, "")
                    label = f"{param_prefix}: {label}"
                elif prefix:
                    label = f"{prefix}{label}"
            
            labels.append(label)
        
        return labels
    
    def _handle_auto_queue(self, batch_id: str, grid_config: Dict, node_id: str, prompt: Dict):
        """Handle automatic queuing of grid executions."""
        # Check if this is the first execution for this batch
        state = execution_manager.execution_states.get(batch_id)
        if not state or state.current_iteration == 0:
            # Prepare all executions for the batch
            executions = queue_manager.prepare_batch_executions(
                batch_id, grid_config, node_id, prompt
            )
            
            # Mark that we've started this batch
            self._execution_count = len(executions)
        
        # Advance to next iteration after this one completes
        if execution_manager.should_continue(batch_id):
            execution_manager.advance_batch(batch_id)
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Force re-execution for grid iterations."""
        return float("nan")