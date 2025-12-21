"""
KikoTools package initialization and node registry
Handles automatic discovery and registration of all ComfyAssets tools
"""

from .tools.batch_prompts import BatchPromptsNode
from .tools.display_any import DisplayAnyNode
from .tools.display_text import DisplayTextNode
from .tools.embedding_autocomplete import KikoEmbeddingAutocomplete
from .tools.empty_latent_batch import EmptyLatentBatchNode
from .tools.gemini_prompt import GeminiPromptNode
from .tools.image_scale_down_by import ImageScaleDownByNode
from .tools.image_to_multiple_of import ImageToMultipleOfNode
from .tools.kiko_film_grain import KikoFilmGrainNode
from .tools.kiko_purge_vram import KikoPurgeVRAM
from .tools.kiko_workflow_timer import KikoWorkflowTimerNode
from .tools.kiko_save_image import KikoSaveImageNode
from .tools.local_image_loader import LocalImageLoaderNode
from .tools.model_downloader import ModelDownloaderNode
from .tools.resolution_calculator import ResolutionCalculatorNode
from .tools.sampler_combo import SamplerComboCompactNode, SamplerComboNode
from .tools.seed_history import SeedHistoryNode
from .tools.text_input import TextInputNode
from .tools.width_height_selector import WidthHeightSelectorNode
from .tools.width_height_to_vec2 import WidthHeightToVec2Node
from .tools.xyz_helpers import (
    FluxSamplerParamsNode,
    LoRAFolderBatchNode,
    PlotParametersNode,
    SamplerSelectHelperNode,
    SchedulerSelectHelperNode,
    TextEncodeSamplerParamsNode,
)

# ComfyUI node registration mappings
NODE_CLASS_MAPPINGS = {
    "BatchPrompts": BatchPromptsNode,
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
    "TextInput": TextInputNode,
    "KikoFilmGrain": KikoFilmGrainNode,
    "KikoPurgeVRAM": KikoPurgeVRAM,
    "KikoLocalImageLoader": LocalImageLoaderNode,
    "KikoModelDownloader": ModelDownloaderNode,
    "SamplerSelectHelper": SamplerSelectHelperNode,
    "SchedulerSelectHelper": SchedulerSelectHelperNode,
    "TextEncodeSamplerParams": TextEncodeSamplerParamsNode,
    "FluxSamplerParams": FluxSamplerParamsNode,
    "PlotParameters+": PlotParametersNode,
    "LoRAFolderBatch": LoRAFolderBatchNode,
    "WidthHeightToVec2": WidthHeightToVec2Node,
    "KikoWorkflowTimer": KikoWorkflowTimerNode,
    # Note: KikoEmbeddingAutocomplete is not registered as a node
    # It's a settings-only feature accessed through ComfyUI settings menu
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BatchPrompts": "Batch Prompts",
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
    "TextInput": "Text Input",
    "KikoFilmGrain": "Film Grain",
    "KikoPurgeVRAM": "Kiko Purge VRAM",
    "KikoLocalImageLoader": "Local Image Loader",
    "KikoModelDownloader": "Model Downloader 🌐",
    "SamplerSelectHelper": "Sampler Select Helper",
    "SchedulerSelectHelper": "Scheduler Select Helper",
    "TextEncodeSamplerParams": "Text Encode for Sampler Params",
    "FluxSamplerParams": "Flux Sampler Parameters",
    "PlotParameters+": "Plot Parameters",
    "LoRAFolderBatch": "LoRA Folder Batch",
    "WidthHeightToVec2": "Width Height to VEC2",
    "KikoWorkflowTimer": "Workflow Timer",
    # KikoEmbeddingAutocomplete removed - settings only, not a node
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
