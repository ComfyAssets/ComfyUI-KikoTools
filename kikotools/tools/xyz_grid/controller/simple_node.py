"""Simplified XYZ Plot Controller using native ComfyUI widgets."""

from typing import Dict, List, Any, Tuple
import json

from ..utils.constants import AxisType
from ..utils.helpers import (
    get_available_models, get_available_vaes, get_available_loras,
    get_sampler_names, get_scheduler_names, parse_value_string,
    create_unique_id
)


class XYZPlotController:
    """Simplified XYZ Plot Controller with native widgets."""
    
    @classmethod
    def INPUT_TYPES(cls):
        # For file-based parameters, we'll use a special format in the values field
        axis_types = [
            "none",
            "model",
            "vae", 
            "lora",
            "sampler",
            "scheduler",
            "cfg_scale",
            "steps",
            "seed",
            "denoise",
            "clip_skip",
            "prompt"
        ]
        
        return {
            "required": {
                # X Axis
                "x_type": (axis_types, {"default": "none"}),
                "x_values": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "placeholder": "Enter values separated by commas or use start:stop:step notation"
                }),
                
                # Y Axis  
                "y_type": (axis_types, {"default": "none"}),
                "y_values": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "placeholder": "Enter values separated by commas or use start:stop:step notation"
                }),
                
                # Z Axis (optional)
                "z_type": (axis_types, {"default": "none"}),
                "z_values": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "placeholder": "Enter values separated by commas or use start:stop:step notation"
                }),
                
                # Control
                "auto_queue": ("BOOLEAN", {"default": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }
    
    RETURN_TYPES = ("XYZ_GRID", "STRING", "INT", "FLOAT", "STRING", "INT", "FLOAT", "STRING", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("grid_data", "x_string", "x_int", "x_float", "y_string", "y_int", "y_float", "z_string", "z_int", "z_float", "batch_id")
    OUTPUT_NODE = True
    FUNCTION = "create_grid"
    CATEGORY = "ComfyAssets/XYZ Grid"
    
    def create_grid(self, x_type, x_values, y_type, y_values, z_type, z_values, auto_queue, unique_id=None):
        """Create grid configuration."""
        
        # Parse values for each axis
        x_parsed = self._parse_axis_values(x_type, x_values) if x_type != "none" else []
        y_parsed = self._parse_axis_values(y_type, y_values) if y_type != "none" else []
        z_parsed = self._parse_axis_values(z_type, z_values) if z_type != "none" else []
        
        # Calculate total combinations
        x_count = max(1, len(x_parsed))
        y_count = max(1, len(y_parsed))
        z_count = max(1, len(z_parsed))
        total_images = x_count * y_count * z_count
        
        # Generate batch ID
        batch_id = create_unique_id()
        
        # Create grid data
        grid_data = {
            "batch_id": batch_id,
            "x_axis": {
                "type": x_type,
                "values": x_parsed,
                "count": x_count
            },
            "y_axis": {
                "type": y_type,
                "values": y_parsed,
                "count": y_count
            },
            "z_axis": {
                "type": z_type,
                "values": z_parsed,
                "count": z_count
            },
            "total_images": total_images,
            "current_index": 0,
            "auto_queue": auto_queue
        }
        
        # Get current values for outputs
        x_current = x_parsed[0] if x_parsed else self._get_default_value(x_type)
        y_current = y_parsed[0] if y_parsed else self._get_default_value(y_type)
        z_current = z_parsed[0] if z_parsed else self._get_default_value(z_type)
        
        # Convert to appropriate output types
        x_str, x_int, x_float = self._convert_value(x_type, x_current)
        y_str, y_int, y_float = self._convert_value(y_type, y_current)
        z_str, z_int, z_float = self._convert_value(z_type, z_current)
        
        # Store grid data for execution
        if hasattr(self, '_grids'):
            self._grids[batch_id] = grid_data
        else:
            self._grids = {batch_id: grid_data}
        
        # Log grid info
        print(f"\n[XYZ Grid] Created grid with {total_images} total combinations:")
        if x_type != "none":
            print(f"  X axis ({x_type}): {x_count} values")
        if y_type != "none":
            print(f"  Y axis ({y_type}): {y_count} values")
        if z_type != "none":
            print(f"  Z axis ({z_type}): {z_count} values")
        
        return (grid_data, x_str, x_int, x_float, y_str, y_int, y_float, z_str, z_int, z_float, batch_id)
    
    def _parse_axis_values(self, axis_type: str, values_str: str) -> List[Any]:
        """Parse axis values based on type."""
        if not values_str.strip():
            return []
        
        # Handle range notation (start:stop:step)
        if ":" in values_str and axis_type in ["cfg_scale", "steps", "seed", "denoise", "clip_skip"]:
            try:
                parts = values_str.split(":")
                if len(parts) == 2:
                    start, stop = float(parts[0]), float(parts[1])
                    step = 1.0
                elif len(parts) == 3:
                    start, stop, step = float(parts[0]), float(parts[1]), float(parts[2])
                else:
                    raise ValueError("Invalid range format")
                
                # Generate values
                values = []
                current = start
                while current <= stop:
                    if axis_type in ["steps", "seed", "clip_skip"]:
                        values.append(int(current))
                    else:
                        values.append(round(current, 2))
                    current += step
                return values
            except:
                pass
        
        # Parse comma-separated values
        if axis_type == "prompt":
            # For prompts, split by newline instead of comma
            return [v.strip() for v in values_str.split("\n") if v.strip()]
        else:
            # For everything else, split by comma
            values = [v.strip() for v in values_str.split(",") if v.strip()]
            
            # Convert numeric types
            if axis_type in ["cfg_scale", "denoise"]:
                return [float(v) for v in values]
            elif axis_type in ["steps", "seed", "clip_skip"]:
                return [int(v) for v in values]
            else:
                return values
    
    def _get_default_value(self, axis_type: str) -> Any:
        """Get default value for axis type."""
        defaults = {
            "model": "",
            "vae": "Automatic",
            "lora": "None",
            "sampler": "euler",
            "scheduler": "normal",
            "cfg_scale": 7.0,
            "steps": 20,
            "seed": 0,
            "denoise": 1.0,
            "clip_skip": 1,
            "prompt": ""
        }
        return defaults.get(axis_type, "")
    
    def _convert_value(self, axis_type: str, value: Any) -> Tuple[str, int, float]:
        """Convert value to all output types."""
        if axis_type in ["model", "vae", "lora", "sampler", "scheduler", "prompt"]:
            return (str(value), 0, 0.0)
        elif axis_type in ["steps", "seed", "clip_skip"]:
            return ("", int(value), float(value))
        elif axis_type in ["cfg_scale", "denoise"]:
            return ("", 0, float(value))
        else:
            return ("", 0, 0.0)


# For backward compatibility
XYZPlotControllerAdvanced = XYZPlotController