"""KikoEmbeddingAutocomplete node for ComfyUI.

Provides autocomplete functionality for embeddings and LoRAs in text inputs.
"""

import os
import json
from typing import Dict, List, Any, Optional
import folder_paths


class KikoEmbeddingAutocomplete:
    """Node that provides embedding autocomplete functionality."""

    DISPLAY_NAME = "Embedding Autocomplete"
    CATEGORY = "ComfyAssets"

    # Settings definition for the settings registry
    SETTINGS = {
        "enabled": {
            "type": "boolean",
            "default": True,
            "description": "Enable embedding autocomplete",
        },
        "trigger_chars": {
            "type": "combo",
            "default": 2,
            "options": [1, 2, 3, 4],
            "description": "Number of characters before showing suggestions",
        },
        "max_suggestions": {
            "type": "combo",
            "default": 20,
            "options": [10, 20, 30, 50],
            "description": "Maximum number of suggestions to show",
        },
        "show_embeddings": {
            "type": "boolean",
            "default": True,
            "description": "Show embeddings in suggestions",
        },
        "show_loras": {
            "type": "boolean",
            "default": True,
            "description": "Show LoRAs in suggestions",
        },
        "case_sensitive": {
            "type": "boolean",
            "default": False,
            "description": "Case sensitive matching",
        },
    }

    @classmethod
    def INPUT_TYPES(cls):
        """Define input types for the node."""
        return {
            "required": {},
            "optional": {
                "refresh": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("DICT",)
    RETURN_NAMES = ("autocomplete_data",)
    FUNCTION = "get_autocomplete_data"

    def __init__(self):
        self.embeddings_cache = None
        self.loras_cache = None

    def get_autocomplete_data(self, refresh=False):
        """Get autocomplete data for embeddings and LoRAs.

        This node doesn't process data in the traditional sense - it provides
        autocomplete data to the frontend JavaScript component.
        """
        if refresh or self.embeddings_cache is None:
            self.refresh_cache()

        return (
            {
                "embeddings": self.embeddings_cache,
                "loras": self.loras_cache,
                "timestamp": os.path.getmtime(folder_paths.base_path),
            },
        )

    def refresh_cache(self):
        """Refresh the cache of embeddings and LoRAs."""
        self.embeddings_cache = self.get_embeddings()
        self.loras_cache = self.get_loras()

    def get_embeddings(self) -> List[Dict[str, Any]]:
        """Get list of available embeddings."""
        embeddings = []

        # Get embedding files from ComfyUI's folder system
        try:
            embedding_files = folder_paths.get_filename_list("embeddings")
            for file in embedding_files:
                name = os.path.splitext(file)[0]
                embeddings.append(
                    {
                        "name": name,
                        "file": file,
                        "type": "embedding",
                        "display": f"embedding:{name}",
                        "value": f"embedding:{name}",
                    }
                )
        except Exception as e:
            print(f"Error loading embeddings: {e}")

        return embeddings

    def get_loras(self) -> List[Dict[str, Any]]:
        """Get list of available LoRAs."""
        loras = []

        # Get LoRA files from ComfyUI's folder system
        try:
            lora_files = folder_paths.get_filename_list("loras")
            for file in lora_files:
                name = os.path.splitext(file)[0]
                loras.append(
                    {
                        "name": name,
                        "file": file,
                        "type": "lora",
                        "display": f"<lora:{name}:1.0>",
                        "value": f"<lora:{name}:1.0>",
                    }
                )
        except Exception as e:
            print(f"Error loading LoRAs: {e}")

        return loras

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Check if the node needs to be re-executed."""
        # Always re-execute if refresh is True
        if kwargs.get("refresh", False):
            return float("NaN")

        # Check if embeddings/loras folders have changed
        try:
            embeddings_path = folder_paths.get_folder_paths("embeddings")[0]
            loras_path = folder_paths.get_folder_paths("loras")[0]

            # Return combined modification time
            return os.path.getmtime(embeddings_path) + os.path.getmtime(loras_path)
        except:
            return 0


class KikoEmbeddingAutocompleteAPI:
    """API endpoints for embedding autocomplete."""

    @staticmethod
    def get_suggestions(
        prefix: str,
        max_results: int = 20,
        include_embeddings: bool = True,
        include_loras: bool = True,
        case_sensitive: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get autocomplete suggestions for a given prefix.

        Args:
            prefix: The text prefix to match
            max_results: Maximum number of results to return
            include_embeddings: Include embeddings in results
            include_loras: Include LoRAs in results
            case_sensitive: Use case-sensitive matching

        Returns:
            List of suggestion dictionaries
        """
        suggestions = []

        # Normalize prefix for matching
        match_prefix = prefix if case_sensitive else prefix.lower()

        # Get embeddings
        if include_embeddings:
            try:
                embedding_files = folder_paths.get_filename_list("embeddings")
                for file in embedding_files:
                    name = os.path.splitext(file)[0]
                    match_name = name if case_sensitive else name.lower()

                    # Check for match
                    if match_name.startswith(match_prefix):
                        suggestions.append(
                            {
                                "name": name,
                                "type": "embedding",
                                "display": f"embedding:{name}",
                                "value": f"embedding:{name}",
                                "priority": 1 if match_name == match_prefix else 0,
                            }
                        )
                    elif match_prefix in match_name:
                        suggestions.append(
                            {
                                "name": name,
                                "type": "embedding",
                                "display": f"embedding:{name}",
                                "value": f"embedding:{name}",
                                "priority": -1,
                            }
                        )
            except Exception as e:
                print(f"Error loading embeddings: {e}")

        # Get LoRAs
        if include_loras:
            try:
                lora_files = folder_paths.get_filename_list("loras")
                for file in lora_files:
                    name = os.path.splitext(file)[0]
                    match_name = name if case_sensitive else name.lower()

                    # Check for match
                    if match_name.startswith(match_prefix):
                        suggestions.append(
                            {
                                "name": name,
                                "type": "lora",
                                "display": f"<lora:{name}:1.0>",
                                "value": f"<lora:{name}:1.0>",
                                "priority": 1 if match_name == match_prefix else 0,
                            }
                        )
                    elif match_prefix in match_name:
                        suggestions.append(
                            {
                                "name": name,
                                "type": "lora",
                                "display": f"<lora:{name}:1.0>",
                                "value": f"<lora:{name}:1.0>",
                                "priority": -1,
                            }
                        )
            except Exception as e:
                print(f"Error loading LoRAs: {e}")

        # Sort by priority and name
        suggestions.sort(key=lambda x: (-x["priority"], x["name"]))

        # Limit results
        return suggestions[:max_results]
