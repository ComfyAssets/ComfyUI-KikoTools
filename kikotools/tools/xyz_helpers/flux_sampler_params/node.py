"""Flux Sampler Params node for ComfyUI."""

from typing import Tuple, Any, Dict, List, Optional
import time
import logging
from ....base.base_node import ComfyAssetsBaseNode
from .logic import (
    parse_string_to_list,
    parse_seed_string,
    parse_sampler_string,
    parse_scheduler_string,
    get_default_flux_params,
    create_batch_params,
    process_conditioning_input,
    validate_flux_params,
)

logger = logging.getLogger(__name__)


class FluxSamplerParamsNode(ComfyAssetsBaseNode):
    """
    Flux Sampler Parameters node for batch processing.

    Enables batch processing with multiple parameter variations for
    Flux models. Supports varying seeds, samplers, schedulers, steps,
    guidance, shifts, and LoRAs for comprehensive parameter exploration.
    """

    def __init__(self):
        """Initialize the node."""
        super().__init__()
        self.lora_loader = None
        self.cached_lora = (None, None)

    @classmethod
    def INPUT_TYPES(cls):
        """Define the input types for the ComfyUI node."""
        return {
            "required": {
                "model": ("MODEL", {"tooltip": "Flux model to use"}),
                "conditioning": (
                    "CONDITIONING",
                    {"tooltip": "Conditioning (can be from TextEncodeSamplerParams)"},
                ),
                "latent_image": ("LATENT", {"tooltip": "Input latent image"}),
                "seed": (
                    "STRING",
                    {
                        "multiline": False,
                        "dynamicPrompts": False,
                        "default": "?",
                        "tooltip": "Seeds (comma-separated, ? for random)",
                    },
                ),
                "sampler": (
                    "STRING",
                    {
                        "multiline": False,
                        "dynamicPrompts": False,
                        "default": "euler",
                        "tooltip": "Samplers (comma-separated, * for all, ! to exclude)",
                    },
                ),
                "scheduler": (
                    "STRING",
                    {
                        "multiline": False,
                        "dynamicPrompts": False,
                        "default": "simple",
                        "tooltip": "Schedulers (comma-separated, * for all, ! to exclude)",
                    },
                ),
                "steps": (
                    "STRING",
                    {
                        "multiline": False,
                        "dynamicPrompts": False,
                        "default": "20",
                        "tooltip": "Steps (comma-separated values)",
                    },
                ),
                "guidance": (
                    "STRING",
                    {
                        "multiline": False,
                        "dynamicPrompts": False,
                        "default": "3.5",
                        "tooltip": "Guidance/CFG values (comma-separated)",
                    },
                ),
                "max_shift": (
                    "STRING",
                    {
                        "multiline": False,
                        "dynamicPrompts": False,
                        "default": "",
                        "tooltip": "Max shift values (comma-separated, auto-set for Flux)",
                    },
                ),
                "base_shift": (
                    "STRING",
                    {
                        "multiline": False,
                        "dynamicPrompts": False,
                        "default": "",
                        "tooltip": "Base shift values (comma-separated, auto-set for Flux)",
                    },
                ),
                "denoise": (
                    "STRING",
                    {
                        "multiline": False,
                        "dynamicPrompts": False,
                        "default": "1.0",
                        "tooltip": "Denoise values (comma-separated)",
                    },
                ),
            },
            "optional": {
                "loras": ("LORA_PARAMS", {"tooltip": "Optional LoRA parameters"})
            },
        }

    RETURN_TYPES = ("LATENT", "SAMPLER_PARAMS")
    RETURN_NAMES = ("latent", "params")
    FUNCTION = "process_batch"
    CATEGORY = "🫶 ComfyAssets/🧰 xyz-helpers"

    def process_batch(
        self,
        model: Any,
        conditioning: Any,
        latent_image: Any,
        seed: str,
        sampler: str,
        scheduler: str,
        steps: str,
        guidance: str,
        max_shift: str,
        base_shift: str,
        denoise: str,
        loras: Optional[Dict] = None,
    ) -> Tuple[Any, List[Dict[str, Any]]]:
        """
        Process batch sampling with parameter variations.

        Returns:
            Tuple of (output_latent, parameter_list)
        """
        try:
            import comfy.samplers
            import comfy.model_base
            import comfy.model_management
            import comfy.utils
            import torch
            from comfy_extras.nodes_custom_sampler import (
                Noise_RandomNoise,
                BasicScheduler,
                BasicGuider,
                SamplerCustomAdvanced,
            )
            from comfy_extras.nodes_model_advanced import (
                ModelSamplingFlux,
                ModelSamplingAuraFlow,
            )
            from node_helpers import conditioning_set_values
            from nodes import LoraLoader

        except ImportError as e:
            self.handle_error(f"Required ComfyUI modules not available: {e}")
            return (latent_image, [])

        # Local implementation of LatentBatch functionality
        # Copied from nodes_latent.py to avoid V3 schema breaking changes
        def reshape_latent_to(target_shape, latent, repeat_batch=True):
            """Reshape latent tensor to match target shape."""
            if latent.shape[1:] != target_shape[1:]:
                latent = comfy.utils.common_upscale(
                    latent, target_shape[-1], target_shape[-2], "bilinear", "center"
                )
            if repeat_batch:
                return comfy.utils.repeat_to_batch_size(latent, target_shape[0])
            else:
                return latent

        def batch_latents(samples1, samples2):
            """Batch two latent samples together."""
            samples_out = samples1.copy()
            s1 = samples1["samples"]
            s2 = samples2["samples"]

            s2 = reshape_latent_to(s1.shape, s2, repeat_batch=False)
            s = torch.cat((s1, s2), dim=0)
            samples_out["samples"] = s
            samples_out["batch_index"] = samples1.get(
                "batch_index", [x for x in range(0, s1.shape[0])]
            ) + samples2.get("batch_index", [x for x in range(0, s2.shape[0])])
            return samples_out

        try:
            if not validate_flux_params(
                steps, guidance, max_shift, base_shift, denoise
            ):
                self.handle_error("Invalid parameter format")

            is_schnell = model.model.model_type == comfy.model_base.ModelType.FLOW
            defaults = get_default_flux_params(is_schnell)

            seeds = parse_seed_string(seed)
            samplers = parse_sampler_string(sampler, comfy.samplers.KSampler.SAMPLERS)
            schedulers = parse_scheduler_string(
                scheduler, comfy.samplers.KSampler.SCHEDULERS
            )

            steps = steps if steps else str(defaults["steps"])
            steps_list = [int(s) for s in parse_string_to_list(steps)]

            guidance = guidance if guidance else str(defaults["guidance"])
            guidance_list = parse_string_to_list(guidance)

            denoise = denoise if denoise else "1.0"
            denoise_list = parse_string_to_list(denoise)

            if not is_schnell:
                max_shift = max_shift if max_shift else str(defaults["max_shift"])
                base_shift = base_shift if base_shift else str(defaults["base_shift"])
            else:
                max_shift = "0"
                base_shift = base_shift if base_shift else str(defaults["base_shift"])

            max_shift_list = parse_string_to_list(max_shift)
            base_shift_list = parse_string_to_list(base_shift)

            cond_text, cond_encoded = process_conditioning_input(conditioning)

            width = latent_image["samples"].shape[3] * 8
            height = latent_image["samples"].shape[2] * 8

            lora_strength_count = 1
            if loras:
                lora_model = loras["loras"]
                lora_strength = loras["strengths"]
                lora_strength_count = sum(len(i) for i in lora_strength)

                if self.lora_loader is None:
                    self.lora_loader = LoraLoader()

            total_samples, param_combos = create_batch_params(
                seeds,
                samplers,
                schedulers,
                steps_list,
                guidance_list,
                max_shift_list,
                base_shift_list,
                denoise_list,
                len(cond_encoded),
                lora_strength_count,
            )

            self.log_info(f"Processing {total_samples} parameter combinations")

            basicscheduler = BasicScheduler()
            basicguider = BasicGuider()
            samplercustomadvanced = SamplerCustomAdvanced()
            modelsampling = (
                ModelSamplingFlux() if not is_schnell else ModelSamplingAuraFlow()
            )

            out_latent = None
            out_params = []

            if total_samples > 1:
                from comfy.utils import ProgressBar

                pbar = ProgressBar(total_samples)

            current_sample = 0

            for lora_idx in range(lora_strength_count if loras else 1):
                if loras:
                    # Find which LoRA file and strength to use
                    cumulative_idx = 0
                    lora_file_idx = 0
                    strength_in_file_idx = 0

                    # Determine which LoRA file this index corresponds to
                    for file_idx, strengths in enumerate(lora_strength):
                        if lora_idx < cumulative_idx + len(strengths):
                            lora_file_idx = file_idx
                            strength_in_file_idx = lora_idx - cumulative_idx
                            break
                        cumulative_idx += len(strengths)

                    # Load the appropriate LoRA with its strength
                    if lora_file_idx < len(lora_model) and strength_in_file_idx < len(
                        lora_strength[lora_file_idx]
                    ):
                        patched_model = self.lora_loader.load_lora(
                            model,
                            None,
                            lora_model[lora_file_idx],
                            lora_strength[lora_file_idx][strength_in_file_idx],
                            0,
                        )[0]
                    else:
                        patched_model = model
                else:
                    patched_model = model

                for cond_idx, cond in enumerate(cond_encoded):
                    prompt_text = cond_text[cond_idx] if cond_text else None

                    for params in param_combos:
                        current_sample += 1

                        if is_schnell:
                            work_model = modelsampling.patch_aura(
                                patched_model, params["base_shift"]
                            )[0]
                        else:
                            work_model = modelsampling.patch(
                                patched_model,
                                params["max_shift"],
                                params["base_shift"],
                                width,
                                height,
                            )[0]

                        cond_with_guidance = conditioning_set_values(
                            cond, {"guidance": params["guidance"]}
                        )

                        guider = basicguider.get_guider(work_model, cond_with_guidance)[
                            0
                        ]
                        sampler_obj = comfy.samplers.sampler_object(params["sampler"])
                        sigmas = basicscheduler.get_sigmas(
                            work_model,
                            params["scheduler"],
                            params["steps"],
                            params["denoise"],
                        )[0]

                        noise = Noise_RandomNoise(params["seed"])

                        self.log_info(
                            f"Sample {current_sample}/{total_samples}: "
                            f"seed={params['seed']}, sampler={params['sampler']}, "
                            f"steps={params['steps']}"
                        )

                        start_time = time.time()
                        latent = samplercustomadvanced.sample(
                            noise, guider, sampler_obj, sigmas, latent_image
                        )[1]
                        elapsed = time.time() - start_time

                        param_record = {
                            **params,
                            "time": elapsed,
                            "width": width,
                            "height": height,
                            "prompt": prompt_text,
                        }

                        if loras:
                            # Record which LoRA and strength was used
                            param_record["lora"] = (
                                lora_model[lora_file_idx]
                                if lora_file_idx < len(lora_model)
                                else None
                            )
                            param_record["lora_strength"] = (
                                lora_strength[lora_file_idx][strength_in_file_idx]
                                if lora_file_idx < len(lora_strength)
                                and strength_in_file_idx
                                < len(lora_strength[lora_file_idx])
                                else 0
                            )
                            # Add batch info if available
                            if "batch_info" in loras:
                                param_record["lora_batch"] = (
                                    f"Batch {loras['batch_info']['index'] + 1}/"
                                    f"{loras['batch_info']['total']}"
                                )

                        out_params.append(param_record)

                        if out_latent is None:
                            out_latent = latent
                        else:
                            out_latent = batch_latents(out_latent, latent)

                        if total_samples > 1:
                            pbar.update(1)

            self.log_info(f"Completed {len(out_params)} samples")
            return (out_latent, out_params)

        except Exception as e:
            self.handle_error(f"Error in batch processing: {str(e)}", e)
            return (latent_image, [])
