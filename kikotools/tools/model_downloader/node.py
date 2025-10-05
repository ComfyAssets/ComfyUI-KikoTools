"""ComfyUI Model Downloader Node"""

from ...base import ComfyAssetsBaseNode
from .detector import URLDetector


class ModelDownloaderNode(ComfyAssetsBaseNode):
    """ComfyUI node for downloading models from CivitAI, HuggingFace, and custom URLs"""

    @classmethod
    def INPUT_TYPES(cls):
        """Define input types for the node"""
        return {
            "required": {
                "url": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "https://civitai.com/... or https://huggingface.co/...",
                    },
                ),
                "save_path": (
                    "STRING",
                    {
                        "default": "models/checkpoints",
                        "multiline": False,
                        "placeholder": "Path to save downloaded models",
                    },
                ),
            },
            "optional": {
                "filename": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "Leave empty for auto-detection",
                    },
                ),
                "api_token": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "API token (CivitAI or HuggingFace)",
                    },
                ),
                "force_download": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": "Force Redownload",
                        "label_off": "Skip if Exists",
                    },
                ),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "download_model"
    CATEGORY = "🫶 ComfyAssets/🛠️ Utils"
    OUTPUT_NODE = True

    def download_model(
        self,
        url: str,
        save_path: str,
        filename: str = "",
        api_token: str = "",
        force_download: bool = False,
    ):
        """Download model from URL

        Args:
            url: URL to download from
            save_path: Directory to save file
            filename: Optional filename override
            api_token: Optional API token
            force_download: Force re-download if file exists

        Returns:
            Dictionary with 'ui' key for ComfyUI display
        """
        # Validate inputs
        if not url or not url.strip():
            error_msg = "URL cannot be empty"
            return {"ui": {"text": [error_msg]}}

        if not save_path or not save_path.strip():
            error_msg = "Save path cannot be empty"
            return {"ui": {"text": [error_msg]}}

        url = url.strip()
        save_path = save_path.strip()
        filename = filename.strip() if filename else None
        api_token = api_token.strip() if api_token else None

        try:
            # Detect downloader type and get appropriate downloader
            detector = URLDetector()
            downloader_type = detector.detect(url)

            print(
                f"\n[Model Downloader] Detected downloader type: {downloader_type.value}"
            )
            print(f"[Model Downloader] URL: {url}")
            print(f"[Model Downloader] Save path: {save_path}")
            if filename:
                print(f"[Model Downloader] Filename: {filename}")
            if force_download:
                print("[Model Downloader] Force download: enabled")

            # Get downloader instance
            downloader = detector.get_downloader(url, api_token=api_token)

            # Download file
            file_path = downloader.download(
                url=url, output_path=save_path, filename=filename, force=force_download
            )

            message = f"Successfully downloaded to {file_path}"
            print(f"[Model Downloader] {message}")

            return {"ui": {"text": [message]}}

        except ValueError as e:
            error_msg = f"Invalid URL: {str(e)}"
            print(f"[Model Downloader] Error: {error_msg}")
            return {"ui": {"text": [error_msg]}}

        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            print(f"[Model Downloader] Error: {error_msg}")
            return {"ui": {"text": [error_msg]}}

    @classmethod
    def IS_CHANGED(
        cls, url, save_path, filename="", api_token="", force_download=False
    ):
        """Force re-evaluation on every execution or when inputs change"""
        # Include hash of inputs plus timestamp to force execution
        # This ensures the node re-runs even if the download failed previously
        import time
        import hashlib

        # Create a unique hash based on non-sensitive inputs and current time
        # Note: api_token is excluded to avoid sensitive data in hash
        # The token doesn't affect cache invalidation - URL changes are sufficient
        input_str = f"{url}|{save_path}|{filename}|{force_download}|{time.time()}"
        return hashlib.sha256(input_str.encode()).hexdigest()


# Node display name
NODE_DISPLAY_NAME = "Model Downloader 🌐"
