"""Model Downloader Tool for ComfyUI-KikoTools

Downloads models from CivitAI, HuggingFace, and custom URLs.
"""

from .node import ModelDownloaderNode

__all__ = ["ModelDownloaderNode"]

# Node registration
NODE_CLASS_MAPPINGS = {"KikoModelDownloader": ModelDownloaderNode}

NODE_DISPLAY_NAME_MAPPINGS = {"KikoModelDownloader": "Model Downloader 🌐"}
