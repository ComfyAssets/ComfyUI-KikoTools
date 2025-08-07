"""Logic module for Sampler Select Helper node."""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

try:
    import comfy.samplers

    SAMPLERS = comfy.samplers.KSampler.SAMPLERS
except ImportError:
    SAMPLERS = [
        "euler",
        "euler_cfg_pp",
        "euler_ancestral",
        "euler_ancestral_cfg_pp",
        "heun",
        "heunpp2",
        "dpm_2",
        "dpm_2_ancestral",
        "lms",
        "dpm_fast",
        "dpm_adaptive",
        "dpmpp_2s_ancestral",
        "dpmpp_2s_ancestral_cfg_pp",
        "dpmpp_sde",
        "dpmpp_sde_gpu",
        "dpmpp_2m",
        "dpmpp_2m_cfg_pp",
        "dpmpp_2m_sde",
        "dpmpp_2m_sde_gpu",
        "dpmpp_3m_sde",
        "dpmpp_3m_sde_gpu",
        "ddpm",
        "lcm",
        "ipndm",
        "ipndm_v",
        "deis",
        "ddim",
        "uni_pc",
        "uni_pc_bh2",
    ]


def process_sampler_selection(**sampler_flags: bool) -> str:
    """
    Process boolean flags for each sampler and return selected ones.

    Args:
        **sampler_flags: Keyword arguments where keys are sampler names
                         and values are boolean selection states

    Returns:
        Comma-separated string of selected sampler names
    """
    try:
        selected_samplers = [
            sampler_name
            for sampler_name, is_selected in sampler_flags.items()
            if is_selected
        ]

        if not selected_samplers:
            logger.warning("No samplers selected, returning empty string")
            return ""

        result = ", ".join(selected_samplers)
        logger.info(f"Selected samplers: {result}")
        return result

    except Exception as e:
        logger.error(f"Error processing sampler selection: {e}")
        return ""


def validate_sampler_names(sampler_names: str) -> List[str]:
    """
    Validate and clean a comma-separated string of sampler names.

    Args:
        sampler_names: Comma-separated string of sampler names

    Returns:
        List of valid sampler names
    """
    if not sampler_names:
        return []

    try:
        names = [name.strip() for name in sampler_names.split(",")]
        valid_names = [name for name in names if name in SAMPLERS]

        invalid_names = [name for name in names if name not in SAMPLERS]
        if invalid_names:
            logger.warning(f"Invalid sampler names ignored: {invalid_names}")

        return valid_names

    except Exception as e:
        logger.error(f"Error validating sampler names: {e}")
        return []


def get_sampler_groups() -> Dict[str, List[str]]:
    """
    Get samplers organized by algorithm family.

    Returns:
        Dictionary mapping algorithm families to sampler names
    """
    groups = {
        "Euler": ["euler", "euler_cfg_pp", "euler_ancestral", "euler_ancestral_cfg_pp"],
        "Heun": ["heun", "heunpp2"],
        "DPM": ["dpm_2", "dpm_2_ancestral", "dpm_fast", "dpm_adaptive"],
        "DPM++": [
            "dpmpp_2s_ancestral",
            "dpmpp_2s_ancestral_cfg_pp",
            "dpmpp_sde",
            "dpmpp_sde_gpu",
            "dpmpp_2m",
            "dpmpp_2m_cfg_pp",
            "dpmpp_2m_sde",
            "dpmpp_2m_sde_gpu",
            "dpmpp_3m_sde",
            "dpmpp_3m_sde_gpu",
        ],
        "Other": [
            "lms",
            "ddpm",
            "lcm",
            "ipndm",
            "ipndm_v",
            "deis",
            "ddim",
            "uni_pc",
            "uni_pc_bh2",
        ],
    }

    return {
        family: [s for s in samplers if s in SAMPLERS]
        for family, samplers in groups.items()
    }


def get_default_samplers() -> List[str]:
    """
    Get a list of commonly used default samplers.

    Returns:
        List of default sampler names
    """
    defaults = [
        "euler",
        "euler_ancestral",
        "dpmpp_2m",
        "dpmpp_sde",
        "dpmpp_2m_sde",
        "ddim",
        "uni_pc",
    ]
    return [s for s in defaults if s in SAMPLERS]
