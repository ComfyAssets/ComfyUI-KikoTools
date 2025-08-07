"""Seed History node for ComfyUI."""

from typing import Tuple
from ...base.base_node import ComfyAssetsBaseNode
from .logic import (
    generate_random_seed,
    validate_seed_value,
    sanitize_seed_value,
)


class SeedHistoryNode(ComfyAssetsBaseNode):
    """
    Seed History node for tracking and managing seed values.

    Provides seed value output with integrated history tracking,
    deduplication, and interactive UI for seed management.
    """

    @classmethod
    def INPUT_TYPES(cls):
        """Define the input types for the ComfyUI node."""
        return {
            "required": {
                "seed": (
                    "INT",
                    {
                        "default": 12345,
                        "min": 0,
                        "max": 0xFFFFFFFFFFFFFFFF,
                        "tooltip": "Seed value for generation processes. "
                        "History UI tracks all changes automatically.",
                    },
                ),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("seed",)
    FUNCTION = "output_seed"
    CATEGORY = "ComfyAssets/🌱 Seeds"

    def output_seed(self, seed: int) -> Tuple[int]:
        """
        Output the seed value for use in other nodes.

        Args:
            seed: Input seed value

        Returns:
            Tuple containing the seed value
        """
        try:
            # Validate and sanitize the seed
            if not validate_seed_value(seed):
                # Log the validation error but don't raise
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"{self.__class__.__name__}: Invalid seed value: {seed}. "
                    f"Using fallback seed 12345."
                )
                return (12345,)

            clean_seed = sanitize_seed_value(seed)

            return (clean_seed,)

        except Exception as e:
            # Handle any unexpected errors gracefully
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"{self.__class__.__name__}: Error processing seed: {str(e)}. "
                f"Using fallback seed 12345."
            )
            return (12345,)

    def generate_new_seed(self) -> int:
        """
        Generate a new random seed value.

        Returns:
            New random seed integer
        """
        try:
            new_seed = generate_random_seed()
            self.log_info(f"Generated new seed: {new_seed}")
            return new_seed
        except Exception as e:
            error_msg = f"Error generating seed: {str(e)}. Using fallback."
            self.handle_error(error_msg)
            return 12345

    def validate_seed_input(self, seed: int) -> bool:
        """
        Validate seed input value.

        Args:
            seed: Seed value to validate

        Returns:
            True if seed is valid
        """
        return validate_seed_value(seed)

    def get_seed_info(self, seed: int) -> str:
        """
        Get descriptive information about a seed value.

        Args:
            seed: Seed value

        Returns:
            Information string about the seed
        """
        if not validate_seed_value(seed):
            return f"Invalid seed: {seed} (outside valid range)"

        # Convert to hex for additional info
        hex_value = hex(seed)

        # Check if it's a "nice" number (power of 2, round number, etc.)
        seed_type = "standard"
        if seed == 0:
            seed_type = "zero"
        elif seed & (seed - 1) == 0:  # Power of 2
            seed_type = "power of 2"
        elif str(seed).count("0") > len(str(seed)) // 2:
            seed_type = "round number"
        elif seed == 12345:
            seed_type = "default"

        return f"Seed {seed} ({hex_value}) - {seed_type}"

    def get_seed_range_info(self) -> str:
        """
        Get information about the valid seed range.

        Returns:
            Range information string
        """
        max_seed = 0xFFFFFFFFFFFFFFFF
        return f"Valid range: 0 to {max_seed:,} ({hex(max_seed)})"

    @classmethod
    def get_default_seed(cls) -> int:
        """
        Get the default seed value.

        Returns:
            Default seed integer
        """
        return 12345

    @classmethod
    def is_seed_in_range(cls, seed: int) -> bool:
        """
        Check if seed is within valid ComfyUI range.

        Args:
            seed: Seed value to check

        Returns:
            True if seed is in valid range
        """
        return 0 <= seed <= 0xFFFFFFFFFFFFFFFF

    def __str__(self) -> str:
        """String representation of the node."""
        return "SeedHistoryNode(with_ui_tracking)"

    def __repr__(self) -> str:
        """Detailed string representation of the node."""
        return (
            f"SeedHistoryNode("
            f"category='{self.CATEGORY}', "
            f"function='{self.FUNCTION}', "
            f"max_seed={hex(0xFFFFFFFFFFFFFFFF)}"
            f")"
        )
