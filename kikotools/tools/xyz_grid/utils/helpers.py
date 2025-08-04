"""Helper utilities for XYZ Grid nodes."""

import os
from typing import List, Dict, Any, Tuple, Optional
from .constants import AxisType, NUMERIC_DEFAULTS


def get_available_models() -> List[str]:
    """Get list of available checkpoint models."""
    try:
        import folder_paths
        model_dir = folder_paths.get_folder_paths("checkpoints")[0]
        models = []
        for file in os.listdir(model_dir):
            if file.endswith(('.ckpt', '.safetensors', '.pt', '.pth')):
                models.append(file)
        return sorted(models)
    except:
        return ["No models found"]


def get_available_vaes() -> List[str]:
    """Get list of available VAE models."""
    try:
        import folder_paths
        vae_dir = folder_paths.get_folder_paths("vae")[0]
        vaes = ["Automatic"]
        for file in os.listdir(vae_dir):
            if file.endswith(('.ckpt', '.safetensors', '.pt', '.pth')):
                vaes.append(file)
        return vaes
    except:
        return ["Automatic"]


def get_available_loras() -> List[str]:
    """Get list of available LoRA models."""
    try:
        import folder_paths
        lora_dir = folder_paths.get_folder_paths("loras")[0]
        loras = ["None"]
        for file in os.listdir(lora_dir):
            if file.endswith(('.safetensors', '.pt', '.pth')):
                loras.append(file)
        return loras
    except:
        return ["None"]


def get_sampler_names() -> List[str]:
    """Get list of available sampler names."""
    try:
        import nodes
        return nodes.KSampler.SAMPLERS
    except:
        # Fallback list of common samplers
        return ["euler", "euler_ancestral", "heun", "dpm_2", "dpm_2_ancestral",
                "lms", "dpm_fast", "dpm_adaptive", "dpmpp_2s_ancestral", 
                "dpmpp_sde", "dpmpp_2m", "dpmpp_2m_sde", "ddim", "uni_pc", "uni_pc_bh2"]


def get_scheduler_names() -> List[str]:
    """Get list of available scheduler names."""
    try:
        import nodes
        return nodes.KSampler.SCHEDULERS
    except:
        # Fallback list
        return ["normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform"]


def parse_value_string(value_str: str, axis_type: AxisType) -> List[Any]:
    """Parse a string of values based on axis type.
    
    Args:
        value_str: String containing values (comma-separated or range syntax)
        axis_type: Type of parameter to parse for
        
    Returns:
        List of parsed values
    """
    if not value_str or not value_str.strip():
        return []
    
    values = []
    
    # Handle numeric types with range syntax
    if axis_type in NUMERIC_DEFAULTS:
        # Check for range syntax (start:stop:step)
        if ':' in value_str:
            parts = value_str.split(':')
            if len(parts) == 2:
                start, stop = float(parts[0]), float(parts[1])
                step = 1.0 if axis_type == AxisType.CFG_SCALE else 1
            elif len(parts) == 3:
                start, stop, step = float(parts[0]), float(parts[1]), float(parts[2])
            else:
                raise ValueError(f"Invalid range syntax: {value_str}")
            
            # Generate range values
            current = start
            while current <= stop:
                if axis_type in (AxisType.STEPS, AxisType.CLIP_SKIP, AxisType.SEED):
                    values.append(int(current))
                else:
                    values.append(round(current, 2))
                current += step
        else:
            # Parse comma-separated values
            for val in value_str.split(','):
                val = val.strip()
                if val:
                    if axis_type in (AxisType.STEPS, AxisType.CLIP_SKIP, AxisType.SEED):
                        values.append(int(val))
                    else:
                        values.append(float(val))
    else:
        # String-based parameters (split by comma)
        values = [v.strip() for v in value_str.split(',') if v.strip()]
    
    return values


def generate_axis_labels(values: List[Any], axis_type: AxisType, prefix: str = "") -> List[str]:
    """Generate labels for axis values.
    
    Args:
        values: List of axis values
        axis_type: Type of parameter
        prefix: Optional prefix for labels
        
    Returns:
        List of label strings
    """
    labels = []
    
    for value in values:
        if axis_type == AxisType.MODEL:
            # Strip extension and path for models
            label = os.path.splitext(os.path.basename(str(value)))[0]
        elif axis_type == AxisType.PROMPT:
            # Truncate long prompts
            label = str(value)[:30] + "..." if len(str(value)) > 30 else str(value)
        else:
            label = str(value)
        
        if prefix:
            label = f"{prefix}{label}"
        
        labels.append(label)
    
    return labels


def calculate_grid_dimensions(x_count: int, y_count: int, z_count: int = 1) -> Dict[str, int]:
    """Calculate total images and grid dimensions.
    
    Args:
        x_count: Number of X axis values
        y_count: Number of Y axis values 
        z_count: Number of Z axis values (default 1)
        
    Returns:
        Dict with total_images, grids_count, cols, rows
    """
    total_images = x_count * y_count * z_count
    grids_count = z_count if z_count > 0 else 1
    
    return {
        "total_images": total_images,
        "grids_count": grids_count,
        "cols": x_count,
        "rows": y_count,
    }


def create_unique_id() -> str:
    """Create unique ID for a grid batch."""
    import uuid
    return str(uuid.uuid4())[:8]