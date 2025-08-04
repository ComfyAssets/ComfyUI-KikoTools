"""XYZ Plot Controller with multiple selection dropdowns."""

from typing import Dict, List, Any, Tuple
import folder_paths

from ..utils.helpers import create_unique_id


class XYZPlotController:
    """XYZ Plot Controller with individual model selection dropdowns."""
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get available options
        models = folder_paths.get_filename_list("checkpoints")
        vaes = ["Automatic"] + folder_paths.get_filename_list("vae")
        loras = ["None"] + folder_paths.get_filename_list("loras")
        
        # Get sampler/scheduler options from a KSampler if available
        samplers = ["euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral", 
                   "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", 
                   "dpmpp_sde", "dpmpp_2m", "dpmpp_2m_sde", "ddim", "uni_pc"]
        schedulers = ["normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform"]
        
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
                # X Axis
                "x_type": (axis_types, {"default": "none"}),
                
                # Y Axis  
                "y_type": (axis_types, {"default": "none"}),
                
                # Z Axis
                "z_type": (axis_types, {"default": "none"}),
                
                # Model selections (up to 10)
                "model_1": (["disabled"] + models, {"default": "disabled"}),
                "model_2": (["disabled"] + models, {"default": "disabled"}),
                "model_3": (["disabled"] + models, {"default": "disabled"}),
                "model_4": (["disabled"] + models, {"default": "disabled"}),
                "model_5": (["disabled"] + models, {"default": "disabled"}),
                
                # VAE selections (up to 5)
                "vae_1": (["disabled"] + vaes, {"default": "disabled"}),
                "vae_2": (["disabled"] + vaes, {"default": "disabled"}),
                "vae_3": (["disabled"] + vaes, {"default": "disabled"}),
                
                # LoRA selections (up to 5)
                "lora_1": (["disabled"] + loras, {"default": "disabled"}),
                "lora_2": (["disabled"] + loras, {"default": "disabled"}),
                "lora_3": (["disabled"] + loras, {"default": "disabled"}),
                
                # Sampler selections (up to 5)
                "sampler_1": (["disabled"] + samplers, {"default": "disabled"}),
                "sampler_2": (["disabled"] + samplers, {"default": "disabled"}),
                "sampler_3": (["disabled"] + samplers, {"default": "disabled"}),
                
                # Scheduler selections (up to 3)
                "scheduler_1": (["disabled"] + schedulers, {"default": "disabled"}),
                "scheduler_2": (["disabled"] + schedulers, {"default": "disabled"}),
                
                # Numeric values (still use text for flexibility)
                "numeric_values": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "placeholder": "For numeric types: use comma-separated values or start:stop:step"
                }),
                
                # Prompts
                "prompts": ("STRING", {
                    "default": "", 
                    "multiline": True,
                    "placeholder": "For prompts: enter each prompt on a new line"
                }),
                
                # Control
                "auto_queue": ("BOOLEAN", {"default": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }
        
        return inputs
    
    RETURN_TYPES = ("XYZ_GRID", "STRING", "INT", "FLOAT", "STRING", "INT", "FLOAT", "STRING", "INT", "FLOAT", "STRING")
    RETURN_NAMES = ("grid_data", "x_string", "x_int", "x_float", "y_string", "y_int", "y_float", "z_string", "z_int", "z_float", "batch_id")
    OUTPUT_NODE = True
    FUNCTION = "create_grid"
    CATEGORY = "ComfyAssets/XYZ Grid"
    
    def create_grid(self, x_type, y_type, z_type, 
                   model_1, model_2, model_3, model_4, model_5,
                   vae_1, vae_2, vae_3,
                   lora_1, lora_2, lora_3,
                   sampler_1, sampler_2, sampler_3,
                   scheduler_1, scheduler_2,
                   numeric_values, prompts, auto_queue, unique_id=None):
        """Create grid configuration from selections."""
        
        # Collect enabled selections
        models = [m for m in [model_1, model_2, model_3, model_4, model_5] if m != "disabled"]
        vaes = [v for v in [vae_1, vae_2, vae_3] if v != "disabled"]
        loras = [l for l in [lora_1, lora_2, lora_3] if l != "disabled"]
        samplers = [s for s in [sampler_1, sampler_2, sampler_3] if s != "disabled"]
        schedulers = [s for s in [scheduler_1, scheduler_2] if s != "disabled"]
        
        # Parse values for each axis
        x_parsed = self._get_axis_values(x_type, models, vaes, loras, samplers, schedulers, numeric_values, prompts)
        y_parsed = self._get_axis_values(y_type, models, vaes, loras, samplers, schedulers, numeric_values, prompts)
        z_parsed = self._get_axis_values(z_type, models, vaes, loras, samplers, schedulers, numeric_values, prompts)
        
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
        
        # Log grid info
        print(f"\n[XYZ Grid] Created grid with {total_images} total combinations:")
        if x_type != "none":
            print(f"  X axis ({x_type}): {x_count} values")
        if y_type != "none":
            print(f"  Y axis ({y_type}): {y_count} values")
        if z_type != "none":
            print(f"  Z axis ({z_type}): {z_count} values")
        
        return (grid_data, x_str, x_int, x_float, y_str, y_int, y_float, z_str, z_int, z_float, batch_id)
    
    def _get_axis_values(self, axis_type, models, vaes, loras, samplers, schedulers, numeric_values, prompts):
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
            return [p.strip() for p in prompts.split("\n") if p.strip()]
        elif axis_type in ["cfg_scale", "steps", "seed", "denoise", "clip_skip"]:
            return self._parse_numeric_values(axis_type, numeric_values)
        else:
            return []
    
    def _parse_numeric_values(self, axis_type: str, values_str: str) -> List[Any]:
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
            return (str(value), 0, 0.0)
        elif axis_type in ["steps", "seed", "clip_skip"]:
            return ("", int(value), float(value))
        elif axis_type in ["cfg_scale", "denoise"]:
            return ("", 0, float(value))
        else:
            return ("", 0, 0.0)