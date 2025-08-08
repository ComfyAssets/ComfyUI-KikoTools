"""
KikoTools package initialization and node registry
Handles automatic discovery and registration of all ComfyAssets tools
"""

from .tools.display_any import DisplayAnyNode
from .tools.display_text import DisplayTextNode
from .tools.embedding_autocomplete import KikoEmbeddingAutocomplete
from .tools.empty_latent_batch import EmptyLatentBatchNode
from .tools.gemini_prompt import GeminiPromptNode
from .tools.image_scale_down_by import ImageScaleDownByNode
from .tools.image_to_multiple_of import ImageToMultipleOfNode
from .tools.kiko_film_grain import KikoFilmGrainNode
from .tools.kiko_save_image import KikoSaveImageNode
from .tools.resolution_calculator import ResolutionCalculatorNode
from .tools.sampler_combo import SamplerComboCompactNode, SamplerComboNode
from .tools.seed_history import SeedHistoryNode
from .tools.width_height_selector import WidthHeightSelectorNode
from .tools.xyz_helpers import (FluxSamplerParamsNode, LoRAFolderBatchNode,
                                PlotParametersNode, SamplerSelectHelperNode,
                                SchedulerSelectHelperNode,
                                TextEncodeSamplerParamsNode)

# ComfyUI node registration mappings
NODE_CLASS_MAPPINGS = {
    "ResolutionCalculator": ResolutionCalculatorNode,
    "WidthHeightSelector": WidthHeightSelectorNode,
    "SeedHistory": SeedHistoryNode,
    "SamplerCombo": SamplerComboNode,
    "SamplerComboCompact": SamplerComboCompactNode,
    "EmptyLatentBatch": EmptyLatentBatchNode,
    "KikoSaveImage": KikoSaveImageNode,
    "ImageToMultipleOf": ImageToMultipleOfNode,
    "ImageScaleDownBy": ImageScaleDownByNode,
    "GeminiPrompt": GeminiPromptNode,
    "DisplayAny": DisplayAnyNode,
    "DisplayText": DisplayTextNode,
    "KikoFilmGrain": KikoFilmGrainNode,
    "SamplerSelectHelper": SamplerSelectHelperNode,
    "SchedulerSelectHelper": SchedulerSelectHelperNode,
    "TextEncodeSamplerParams": TextEncodeSamplerParamsNode,
    "FluxSamplerParams": FluxSamplerParamsNode,
    "PlotParameters+": PlotParametersNode,
    "LoRAFolderBatch": LoRAFolderBatchNode,
    "KikoEmbeddingAutocomplete": KikoEmbeddingAutocomplete,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ResolutionCalculator": "Resolution Calculator",
    "WidthHeightSelector": "Width Height Selector",
    "SeedHistory": "Seed History",
    "SamplerCombo": "Sampler Combo",
    "SamplerComboCompact": "Sampler Combo (Compact)",
    "EmptyLatentBatch": "Empty Latent Batch",
    "KikoSaveImage": "Kiko Save Image",
    "ImageToMultipleOf": "Image to Multiple of",
    "ImageScaleDownBy": "Image Scale Down By",
    "GeminiPrompt": "Gemini Prompt Engineer",
    "DisplayAny": "Display Any",
    "DisplayText": "Display Text",
    "KikoFilmGrain": "Kiko Film Grain",
    "SamplerSelectHelper": "Sampler Select Helper",
    "SchedulerSelectHelper": "Scheduler Select Helper",
    "TextEncodeSamplerParams": "Text Encode for Sampler Params",
    "FluxSamplerParams": "Flux Sampler Parameters",
    "PlotParameters+": "Plot Parameters",
    "LoRAFolderBatch": "LoRA Folder Batch",
    "KikoEmbeddingAutocomplete": "🫶 Embedding Autocomplete (Test Panel)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
