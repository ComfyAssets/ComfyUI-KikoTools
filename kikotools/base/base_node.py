"""
Base node class for all ComfyAssets tools
Provides consistent categorization and shared functionality
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ComfyAssetsBaseNode:
    """
    Base class for all ComfyAssets nodes

    Provides:
    - Consistent "ComfyAssets" categorization
    - Standardized error handling and logging
    - Common validation patterns
    - Consistent return type handling
    """

    CATEGORY = "ComfyAssets"

    def validate_inputs(self, **kwargs) -> None:
        """
        Common input validation logic
        Override in subclasses for specific validation needs

        Args:
            **kwargs: Input parameters to validate

        Raises:
            ValueError: If validation fails
        """
        pass

    def handle_error(self, error_msg: str, exception: Optional[Exception] = None) -> None:
        """
        Standardized error handling with logging

        Args:
            error_msg: Human-readable error message
            exception: Optional original exception for logging
        """
        logger.error(f"{self.__class__.__name__}: {error_msg}")
        if exception:
            logger.exception(f"Original exception: {exception}")
        raise ValueError(error_msg)

    def log_info(self, message: str) -> None:
        """
        Standardized info logging

        Args:
            message: Information message to log
        """
        logger.info(f"{self.__class__.__name__}: {message}")

    @classmethod
    def get_node_info(cls) -> Dict[str, Any]:
        """
        Get standardized node information for debugging/introspection

        Returns:
            Dict containing node metadata
        """
        return {
            "class_name": cls.__name__,
            "category": getattr(cls, "CATEGORY", "Unknown"),
            "function": getattr(cls, "FUNCTION", "Unknown"),
            "return_types": getattr(cls, "RETURN_TYPES", ()),
            "return_names": getattr(cls, "RETURN_NAMES", ()),
        }
