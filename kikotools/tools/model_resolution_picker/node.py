"""Model Resolution Picker node and its families route for ComfyUI."""

import logging
from typing import Any, Dict, Tuple

from aiohttp import web

from ...base.base_node import ComfyAssetsBaseNode
from ..empty_latent_batch.logic import create_empty_latent_batch
from .families import (
    DEFAULT_FAMILY,
    families_payload,
    family_labels,
    resolve_family,
)
from .logic import round_to_step

logger = logging.getLogger(__name__)

FALLBACK_STEP = 8


class ModelResolutionPickerNode(ComfyAssetsBaseNode):
    """Pick a model family and size, and get an empty latent plus width/height."""

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Any]:
        """Define the input types for the ComfyUI node."""
        size_options = {"default": 1024, "min": 64, "max": 8192, "step": 8}
        return {
            "required": {
                "model": (
                    family_labels(),
                    {
                        "default": DEFAULT_FAMILY,
                        "tooltip": "Model family; the chips list its preferred sizes",
                    },
                ),
                "width": (
                    "INT",
                    {
                        **size_options,
                        "tooltip": "Custom width in pixels; rounded to the model "
                        "family's step",
                    },
                ),
                "height": (
                    "INT",
                    {
                        **size_options,
                        "tooltip": "Custom height in pixels; rounded to the model "
                        "family's step",
                    },
                ),
                "batch_size": (
                    "INT",
                    {
                        "default": 1,
                        "min": 1,
                        "max": 64,
                        "step": 1,
                        "tooltip": "Number of empty latents in the batch",
                    },
                ),
            }
        }

    RETURN_TYPES = ("LATENT", "INT", "INT")
    RETURN_NAMES = ("latent", "width", "height")
    FUNCTION = "create"
    CATEGORY = "🫶 ComfyAssets/🖼️ Resolution"

    def create(
        self, model: str, width: int, height: int, batch_size: int
    ) -> Tuple[Dict[str, Any], int, int]:
        """Round the size to the family's step and build the empty latent."""
        family = resolve_family(model)
        if family is None:
            logger.warning(
                "Unknown model family '%s'; using step %d", model, FALLBACK_STEP
            )
        step = family.step if family else FALLBACK_STEP
        new_width = round_to_step(width, step)
        new_height = round_to_step(height, step)
        if (new_width, new_height) != (width, height):
            self.log_info(
                f"Rounded {width}x{height} to {new_width}x{new_height} "
                f"(step {step})"
            )
        latent = create_empty_latent_batch(new_width, new_height, batch_size)
        return (latent, new_width, new_height)


async def get_families(request: Any) -> web.Response:
    """Serve the model family table as JSON."""
    return web.json_response(families_payload())


# Setup API routes
try:
    import server

    server.PromptServer.instance.routes.get("/kikotools/model_resolution/families")(
        get_families
    )
except ImportError:
    # Server not available during testing
    pass
