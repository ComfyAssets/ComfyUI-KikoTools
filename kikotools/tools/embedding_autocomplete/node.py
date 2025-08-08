"""KikoEmbeddingAutocomplete node for ComfyUI.

Provides autocomplete functionality for embeddings and LoRAs in text inputs.
"""

import os
import json
from typing import Dict, List, Any, Optional
import folder_paths


class KikoEmbeddingAutocomplete:
    """Node that provides embedding autocomplete functionality."""

    DISPLAY_NAME = "🫶 Embedding Autocomplete (Test Panel)"
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
        hints = """🫶 Embedding Autocomplete Test Panel
        
Try these triggers in the text field below:
• Type 'embedding:' to list all embeddings
• Type '<lora:' to list all LoRAs  
• Start typing any name to filter results
• Use Tab or Enter to select, Escape to cancel
• Arrow keys to navigate suggestions

This autocomplete works in all prompt fields!"""
        
        return {
            "required": {
                "test_input": ("STRING", {
                    "multiline": True,
                    "default": hints,
                    "placeholder": "Type here to test autocomplete..."
                }),
            },
            "optional": {
                "refresh": ("BOOLEAN", {"default": False, "label_on": "Refresh Lists", "label_off": "Use Cache"}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }

    RETURN_TYPES = ("STRING", "INT", "INT")
    RETURN_NAMES = ("test_output", "embeddings_count", "loras_count")
    FUNCTION = "process_autocomplete"
    OUTPUT_NODE = True
    
    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def __init__(self):
        self.embeddings_cache = None
        self.loras_cache = None

    def process_autocomplete(self, test_input, refresh=False, unique_id=None):
        """Process and display autocomplete information.

        This node serves as both a test panel and information display
        for the embedding autocomplete functionality.
        """
        if refresh or self.embeddings_cache is None:
            self.refresh_cache()

        # Count available resources
        embeddings_count = len(self.embeddings_cache)
        loras_count = len(self.loras_cache)
        
        # Generate informative output
        output_lines = [
            f"🫶 Embedding Autocomplete Status",
            f"═" * 40,
            f"📦 Embeddings found: {embeddings_count}",
            f"🎨 LoRAs found: {loras_count}",
            f"",
            f"✅ Autocomplete is {'enabled' if self.embeddings_cache or self.loras_cache else 'ready (no resources found)'}",
            f"",
            f"Your test input:",
            f"─" * 40,
            test_input,
            f"─" * 40,
            f"",
            f"💡 Tips:",
            f"• This node enables autocomplete in ALL prompt fields",
            f"• Settings available in ComfyUI Settings menu",
            f"• Look for 🫶 Embedding Autocomplete options"
        ]
        
        if embeddings_count > 0:
            output_lines.append(f"")
            output_lines.append(f"Sample embeddings (first 5):")
            for emb in self.embeddings_cache[:5]:
                output_lines.append(f"  • {emb['name']}")
                
        if loras_count > 0:
            output_lines.append(f"")
            output_lines.append(f"Sample LoRAs (first 5):")
            for lora in self.loras_cache[:5]:
                output_lines.append(f"  • {lora['name']}")
        
        output_text = "\n".join(output_lines)
        
        return (output_text, embeddings_count, loras_count)

    def refresh_cache(self):
        """Refresh the cache of embeddings and LoRAs."""
        print("[KikoEmbeddingAutocomplete] Refreshing cache...")
        self.embeddings_cache = self.get_embeddings()
        self.loras_cache = self.get_loras()
        print(f"[KikoEmbeddingAutocomplete] Cached {len(self.embeddings_cache)} embeddings, {len(self.loras_cache)} LoRAs")

    def get_embeddings(self) -> List[Dict[str, Any]]:
        """Get list of available embeddings."""
        embeddings = []

        # Get embedding files from ComfyUI's folder system
        try:
            print("[KikoEmbeddingAutocomplete] Getting embeddings list...")
            embedding_files = folder_paths.get_filename_list("embeddings")
            print(f"[KikoEmbeddingAutocomplete] Found {len(embedding_files)} embedding files")
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
