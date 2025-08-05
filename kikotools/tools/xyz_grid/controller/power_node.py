"""XYZ Plot Controller with Power Lora Loader-style dynamic widgets."""

from typing import Dict, List, Any, Tuple, Union, Optional
import folder_paths

from ..utils.helpers import create_unique_id


class FlexibleOptionalInputType(dict):
    """Input that allows dynamic widget values from JavaScript."""
    
    def __contains__(self, key):
        # Accept any key from JavaScript widgets
        return True
    
    def __getitem__(self, key):
        # Return a tuple that ComfyUI expects for input types
        # This allows the JavaScript to pass widget values
        return ("STRING", {"forceInput": False})


class XYZPlotController:
    """XYZ Plot Controller with dynamic widget management."""
    
    @classmethod
    def INPUT_TYPES(cls):
        axis_types = [
            "none",
            "models",
            "vaes", 
            "loras",
            "samplers",
            "schedulers",
            "cfg_scale",
            "steps",
            "seed",
            "denoise",
            "clip_skip",
            "prompt"
        ]
        
        inputs = {
            "required": {
                # Axis configuration
                "x_type": (axis_types, {"default": "none"}),
                "y_type": (axis_types, {"default": "none"}),
                "z_type": (axis_types, {"default": "none"}),
                
                # Control
                "auto_queue": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                # Static inputs for numeric/prompt values
                "numeric_values": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "placeholder": "For numeric types: use comma-separated values or start:stop:step notation"
                }),
                
                "prompt_values": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "placeholder": "For prompts: enter each prompt on a new line"
                })
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO"
            }
        }
        
        # Use FlexibleOptionalInputType to accept dynamic widget values from JavaScript
        # But don't create an actual input connection
        inputs["optional"] = FlexibleOptionalInputType()
        
        return inputs
    
    RETURN_TYPES = ("XYZ_GRID", "STRING", "INT", "FLOAT", "STRING", "INT", "FLOAT", "STRING", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("grid_data", "x_string", "x_int", "x_float", "y_string", "y_int", "y_float", "z_string", "z_int", "z_float", "batch_id")
    OUTPUT_NODE = True
    FUNCTION = "create_grid"
    CATEGORY = "ComfyAssets/XYZ Grid"
    
    def create_grid(self, x_type="none", y_type="none", z_type="none", 
                   auto_queue=True, numeric_values="", prompt_values="",
                   unique_id=None, prompt=None, extra_pnginfo=None, **kwargs):
        """Create grid configuration from dynamic selections."""
        
        # Extract dynamic values from kwargs
        models = []
        vaes = []
        loras = []
        samplers = []
        schedulers = []
        
        # Process all kwargs to find dynamic widgets
        for key, value in kwargs.items():
            if key.startswith("x_") or key.startswith("y_") or key.startswith("z_"):
                # Handle dynamic widget values
                if isinstance(value, dict) and "on" in value and value["on"]:
                    # Extract the resource type and axis
                    parts = key.split("_")
                    if len(parts) >= 3:
                        axis = parts[0]
                        resource_type = parts[1]
                        
                        # Store the value based on type
                        if resource_type == "models" and value.get("value") != "none":
                            models.append(value["value"])
                        elif resource_type == "vaes" and value.get("value") != "none":
                            vaes.append(value["value"])
                        elif resource_type == "loras" and value.get("value") != "none":
                            # For loras, store both name and strength
                            lora_data = {
                                "name": value["value"],
                                "strength": value.get("strength", 1.0)
                            }
                            loras.append(lora_data)
                        elif resource_type == "samplers" and value.get("value") != "none":
                            samplers.append(value["value"])
                        elif resource_type == "schedulers" and value.get("value") != "none":
                            schedulers.append(value["value"])
        
        # Parse values for each axis
        x_parsed = self._get_axis_values(x_type, models, vaes, loras, samplers, schedulers, numeric_values, prompt_values)
        y_parsed = self._get_axis_values(y_type, models, vaes, loras, samplers, schedulers, numeric_values, prompt_values)
        z_parsed = self._get_axis_values(z_type, models, vaes, loras, samplers, schedulers, numeric_values, prompt_values)
        
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
            "axes": {
                "x": {
                    "type": x_type,
                    "labels": self._create_labels(x_type, x_parsed)
                },
                "y": {
                    "type": y_type,
                    "labels": self._create_labels(y_type, y_parsed)
                },
                "z": {
                    "type": z_type,
                    "labels": self._create_labels(z_type, z_parsed) if z_type != "none" else []
                }
            },
            "dimensions": {
                "total_images": total_images,
                "x_count": x_count,
                "y_count": y_count,
                "z_count": z_count,
                "cols": x_count,  # X axis forms columns
                "rows": y_count,  # Y axis forms rows
                "grids_count": z_count  # Z axis creates multiple grids
            },
            "total_images": total_images,  # Keep for backward compatibility
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
        
        # Log grid info
        print(f"\n[XYZ Grid] Created grid with {total_images} total combinations:")
        if x_type != "none":
            print(f"  X axis ({x_type}): {x_count} values - {x_parsed}")
        if y_type != "none":
            print(f"  Y axis ({y_type}): {y_count} values - {y_parsed}")
        if z_type != "none":
            print(f"  Z axis ({z_type}): {z_count} values - {z_parsed}")
        
        return (grid_data, x_str, x_int, x_float, y_str, y_int, y_float, z_str, z_int, z_float, batch_id)
    
    def _get_axis_values(self, axis_type, models, vaes, loras, samplers, schedulers, numeric_values, prompt_values):
        """Get values for a specific axis type."""
        if axis_type == "none":
            return []
        elif axis_type == "models":
            return models
        elif axis_type == "vaes":
            return vaes
        elif axis_type == "loras":
            return loras
        elif axis_type == "samplers":
            return samplers
        elif axis_type == "schedulers":
            return schedulers
        elif axis_type == "prompt":
            return [p.strip() for p in prompt_values.split("\n") if p.strip()]
        elif axis_type in ["cfg_scale", "steps", "seed", "denoise", "clip_skip"]:
            return self._parse_numeric_values(axis_type, numeric_values)
        else:
            return []
    
    def _parse_numeric_values(self, axis_type: str, values_str: str) -> List[Union[int, float]]:
        """Parse numeric values with range support."""
        if not values_str.strip():
            return []
        
        # Handle range notation (start:stop:step)
        if ":" in values_str:
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
            "models": "",
            "vaes": "Automatic",
            "loras": "None",
            "samplers": "euler",
            "schedulers": "normal",
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
        if axis_type in ["models", "vaes", "loras", "samplers", "schedulers", "prompt"]:
            # For loras, return the name string
            if axis_type == "loras" and isinstance(value, dict):
                return (value.get("name", ""), 0, 0.0)
            return (str(value), 0, 0.0)
        elif axis_type in ["steps", "seed", "clip_skip"]:
            return ("", int(value), float(value))
        elif axis_type in ["cfg_scale", "denoise"]:
            return ("", 0, float(value))
        else:
            return ("", 0, 0.0)
    
    def _create_labels(self, axis_type: str, values: list) -> list:
        """Create human-readable labels for axis values."""
        labels = []
        for value in values:
            if axis_type == "prompt":
                # Truncate long prompts
                label = str(value)[:30] + "..." if len(str(value)) > 30 else str(value)
            elif axis_type in ["models", "vaes", "loras"]:
                # Use just the filename without path/extension for resources
                if isinstance(value, dict) and "name" in value:
                    name = value["name"]
                else:
                    name = str(value)
                # Remove extension and path
                label = name.split("/")[-1].split(".")[0]
            elif axis_type in ["cfg_scale", "denoise"]:
                # Format floats nicely
                label = f"{float(value):.1f}"
            elif axis_type in ["steps", "seed", "clip_skip"]:
                # Just show the integer
                label = str(int(value))
            elif axis_type in ["samplers", "schedulers"]:
                # Just use the name as-is
                label = str(value)
            else:
                # Default: convert to string
                label = str(value)
            labels.append(label)
        return labels
    
    def _apply_lora(self, model, clip, lora_data: dict):
        """Apply a lora to model and clip."""
        try:
            # Import LoraLoader from ComfyUI
            from nodes import LoraLoader
            import folder_paths
            
            lora_name = lora_data.get("name")
            strength = lora_data.get("strength", 1.0)
            
            if not lora_name:
                return model, clip
                
            # Get the full path to the lora
            lora_path = folder_paths.get_full_path("loras", lora_name)
            if not lora_path:
                print(f"[XYZ Grid] Warning: LoRA '{lora_name}' not found")
                return model, clip
                
            # Apply the lora
            loader = LoraLoader()
            model, clip = loader.load_lora(model, clip, lora_name, strength, strength)
            
            return model, clip
        except Exception as e:
            print(f"[XYZ Grid] Error applying LoRA: {e}")
            return model, clip