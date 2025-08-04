"""Constants for XYZ Grid nodes."""

from enum import Enum


class AxisType(Enum):
    """Available parameter types for grid axes."""
    NONE = "none"
    MODEL = "model"
    SAMPLER = "sampler"
    SCHEDULER = "scheduler"
    CFG_SCALE = "cfg_scale"
    STEPS = "steps"
    CLIP_SKIP = "clip_skip"
    VAE = "vae"
    LORA = "lora"
    PROMPT = "prompt"
    SEED = "seed"
    FLUX_GUIDANCE = "flux_guidance"
    DENOISE = "denoise"
    
    @classmethod
    def choices(cls):
        """Get list of choices for ComfyUI dropdown."""
        return [member.value for member in cls]
    
    @classmethod
    def display_names(cls):
        """Get display names for UI."""
        return {
            cls.NONE: "None",
            cls.MODEL: "Model/Checkpoint",
            cls.SAMPLER: "Sampler",
            cls.SCHEDULER: "Scheduler",
            cls.CFG_SCALE: "CFG Scale",
            cls.STEPS: "Steps",
            cls.CLIP_SKIP: "Clip Skip",
            cls.VAE: "VAE",
            cls.LORA: "LoRA",
            cls.PROMPT: "Prompt",
            cls.SEED: "Seed",
            cls.FLUX_GUIDANCE: "Flux Guidance",
            cls.DENOISE: "Denoise",
        }


# Default values for numeric parameters
NUMERIC_DEFAULTS = {
    AxisType.CFG_SCALE: {"default": 7.0, "min": 0.0, "max": 30.0, "step": 0.5},
    AxisType.STEPS: {"default": 20, "min": 1, "max": 150, "step": 1},
    AxisType.CLIP_SKIP: {"default": 1, "min": 1, "max": 12, "step": 1},
    AxisType.SEED: {"default": 0, "min": 0, "max": 0xffffffffffffffff},
    AxisType.FLUX_GUIDANCE: {"default": 3.5, "min": 0.0, "max": 10.0, "step": 0.1},
    AxisType.DENOISE: {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05},
}

# Grid styling defaults
GRID_DEFAULTS = {
    "font_size": 20,
    "grid_gap": 10,
    "label_height": 30,
    "label_color": (255, 255, 255),
    "label_bg_color": (0, 0, 0, 180),
    "max_label_length": 30,
}