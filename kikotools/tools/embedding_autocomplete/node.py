"""KikoEmbeddingAutocomplete node for ComfyUI.

Provides autocomplete functionality for embeddings and LoRAs in text inputs.
"""

import os
from typing import Dict, List, Any

try:
    import folder_paths
except ImportError:
    # For testing outside ComfyUI environment
    folder_paths = None


class KikoEmbeddingAutocomplete:
    """Node that provides embedding autocomplete functionality."""

    DISPLAY_NAME = "🫶 Embedding Autocomplete Settings"
    CATEGORY = "🫶 ComfyAssets"

    # Settings definition for the settings registry
    SETTINGS = {
        "enabled": {
            "type": "boolean",
            "default": True,
            "description": "Enable autocomplete",
        },
        "show_embeddings": {
            "type": "boolean",
            "default": True,
            "description": "Show embeddings in autocomplete",
        },
        "show_loras": {
            "type": "boolean",
            "default": True,
            "description": "Show LoRAs in autocomplete",
        },
        "embedding_trigger": {
            "type": "text",
            "default": "embedding:",
            "description": "Trigger text for embeddings (e.g., 'embedding:', 'emb:', or custom)",
        },
        "lora_trigger": {
            "type": "text",
            "default": "<lora:",
            "description": "Trigger text for LoRAs (e.g., '<lora:', 'lora:', or custom)",
        },
        "quick_trigger": {
            "type": "text",
            "default": "em",
            "description": "Quick trigger to show embeddings (e.g., 'em', 'emb', or disabled with '')",
        },
        "min_chars": {
            "type": "combo",
            "default": 2,
            "options": [1, 2, 3, 4, 5],
            "description": "Minimum characters before showing suggestions",
        },
        "max_suggestions": {
            "type": "combo",
            "default": 20,
            "options": [5, 10, 15, 20, 30, 50, 100],
            "description": "Maximum number of suggestions to display",
        },
        "sort_by_directory": {
            "type": "boolean",
            "default": True,
            "description": "Group suggestions by directory",
        },
    }

    @classmethod
    def INPUT_TYPES(cls):
        """Define input types for the node."""
        return {
            "required": {},
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "update_settings"
    OUTPUT_NODE = True

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def __init__(self):
        self.embeddings_cache = None
        self.loras_cache = None

    def update_settings(self, unique_id=None):
        """Update settings display.

        This node serves as a settings indicator.
        Actual settings are configured in ComfyUI Settings menu.
        """
        # This node doesn't actually process anything
        # It's just a visual indicator that autocomplete is available
        return ()

    def refresh_cache(self):
        """Refresh the cache of embeddings and LoRAs."""
        print("[KikoEmbeddingAutocomplete] Refreshing cache...")
        self.embeddings_cache = self.get_embeddings()
        self.loras_cache = self.get_loras()
        print(
            f"[KikoEmbeddingAutocomplete] Cached {len(self.embeddings_cache)} embeddings, {len(self.loras_cache)} LoRAs"
        )

    def get_embeddings(self) -> List[Dict[str, Any]]:
        """Get list of available embeddings."""
        embeddings = []

        # Get embedding files from ComfyUI's folder system
        try:
            print("[KikoEmbeddingAutocomplete] Getting embeddings list...")
            if folder_paths is None:
                return embeddings
            embedding_files = folder_paths.get_filename_list("embeddings")
            print(
                f"[KikoEmbeddingAutocomplete] Found {len(embedding_files)} embedding files"
            )
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
            if folder_paths is None:
                return loras
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
            if folder_paths is None:
                return 0
            embeddings_path = folder_paths.get_folder_paths("embeddings")[0]
            loras_path = folder_paths.get_folder_paths("loras")[0]

            # Return combined modification time
            return os.path.getmtime(embeddings_path) + os.path.getmtime(loras_path)
        except Exception:
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
                if folder_paths is None:
                    embedding_files = []
                else:
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
                if folder_paths is None:
                    lora_files = []
                else:
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
