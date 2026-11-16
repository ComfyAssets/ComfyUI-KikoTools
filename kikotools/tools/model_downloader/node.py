"""ComfyUI Model Downloader Node"""

import logging
import re

from ...base import ComfyAssetsBaseNode
from .base import sha256_of_file
from .detector import URLDetector

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

logger = logging.getLogger(__name__)


def _parse_sha256(raw):
    """(lowercase hex SHA256 or None, error text or None) from the sha256 input."""
    value = (raw or "").strip().lower() or None
    if value and not SHA256_PATTERN.match(value):
        return None, "Invalid SHA256: expected 64 hex characters"
    return value, None


def _verify_result(downloader, file_path: str, sha256):
    """(error text or None, note for the success message) after a download.

    A file save_response just verified is not hashed again; a file that was
    already present (and so skipped) is hashed here and kept on a mismatch.
    """
    if not sha256:
        return None, ""
    if downloader.verified_path != file_path:
        actual = sha256_of_file(file_path)
        if actual != sha256:
            return (
                f"SHA256 mismatch for existing file {file_path}: expected {sha256}, "
                f"got {actual}. The file was kept; turn on Force Redownload to "
                "replace it."
            ), ""
    return None, " (SHA256 verified)"


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
                        "placeholder": "Leave empty: uses CIVITAI_API_KEY / HF_TOKEN",
                        "tooltip": "Leave empty to use the server's token: CIVITAI_API_KEY for "
                        "Civitai, HF_TOKEN or `hf auth login` for Hugging Face. A token typed here "
                        "is saved inside the workflow, so anyone you share it with gets it.",
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
                # Last on purpose: saved workflows store widget values by position.
                "sha256": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "placeholder": "Optional: expected SHA256",
                        "tooltip": "When set, a download whose SHA256 differs is discarded, "
                        "and an existing file is checked instead of trusted.",
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
        sha256: str = "",
    ):
        """Download model from URL

        Args:
            url: URL to download from
            save_path: Directory to save file
            filename: Optional filename override
            api_token: Optional API token
            force_download: Force re-download if file exists
            sha256: Optional expected SHA256 (hex) of the file

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
        sha256, error_msg = _parse_sha256(sha256)
        if error_msg:
            return {"ui": {"text": [error_msg]}}

        try:
            # Detect downloader type and get appropriate downloader
            detector = URLDetector()
            downloader_type = detector.detect(url)

            logger.info("Detected downloader type: %s", downloader_type.value)
            logger.info("URL: %s", url)
            logger.info("Save path: %s", save_path)
            if filename:
                logger.info("Filename: %s", filename)
            if force_download:
                logger.info("Force download: enabled")

            # Get downloader instance
            downloader = detector.get_downloader(url, api_token=api_token)
            downloader.expected_sha256 = sha256

            # Download file
            file_path = downloader.download(
                url=url, output_path=save_path, filename=filename, force=force_download
            )

            message = f"Successfully downloaded to {file_path}"
            error_msg, note = _verify_result(downloader, file_path, sha256)
            if error_msg:
                logger.error(error_msg)
                return {"ui": {"text": [error_msg]}}
            message += note
            logger.info(message)

            return {"ui": {"text": [message]}}

        except ValueError as e:
            error_msg = f"Invalid URL: {str(e)}"
            logger.error(error_msg)
            return {"ui": {"text": [error_msg]}}

        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(error_msg)
            return {"ui": {"text": [error_msg]}}

    @classmethod
    def IS_CHANGED(
        cls,
        url,
        save_path,
        filename="",
        api_token="",
        force_download=False,
        sha256="",
    ):
        """Force re-evaluation on every execution or when inputs change"""
        # Include hash of inputs plus timestamp to force execution
        # This ensures the node re-runs even if the download failed previously
        import time
        import hashlib

        # Create a unique hash based on non-sensitive inputs and current time
        # Note: api_token is excluded to avoid sensitive data in hash
        # The token doesn't affect cache invalidation - URL changes are sufficient
        input_str = (
            f"{url}|{save_path}|{filename}|{force_download}|{sha256}|{time.time()}"
        )
        return hashlib.sha256(input_str.encode()).hexdigest()


# Node display name
NODE_DISPLAY_NAME = "Model Downloader 🌐"
