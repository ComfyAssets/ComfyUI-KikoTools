"""HuggingFace downloader implementation"""

import logging
import os
import urllib.request
import urllib.error
from typing import Optional
from urllib.parse import urlparse, quote

from .base import (
    USER_AGENT,
    BaseDownloader,
    safe_server_filename,
    validate_filename,
    validate_url_scheme,
)

logger = logging.getLogger(__name__)

HTTP_ERROR_HINTS = {
    401: "Authentication required. Please provide a valid HuggingFace token.",
    403: "Access forbidden. The model might be gated or require special permissions.",
    404: "File not found. The URL might be incorrect or the file was removed.",
}


class HuggingFaceDownloader(BaseDownloader):
    """Downloader for HuggingFace models"""

    def _parse_huggingface_url(self, url: str) -> dict:
        """Parse HuggingFace URL to extract repo and file information

        Args:
            url: HuggingFace URL

        Returns:
            Dict with 'repo_id', 'filename', 'revision' keys
        """
        parsed = urlparse(url)
        parts = parsed.path.strip("/").split("/")

        result = {"repo_id": None, "filename": None, "revision": "main"}

        # Handle blob URLs (web UI format) - convert to resolve format
        # /{username}/{repo}/blob/{revision}/{file_path}
        if len(parts) >= 5 and "blob" in parts:
            blob_idx = parts.index("blob")
            if blob_idx >= 2:
                # Extract repo_id (username/repo)
                result["repo_id"] = "/".join(parts[:blob_idx])
                # Extract revision
                if blob_idx + 1 < len(parts):
                    result["revision"] = parts[blob_idx + 1]
                # Extract filename (everything after revision)
                if blob_idx + 2 < len(parts):
                    result["filename"] = "/".join(parts[blob_idx + 2 :])

        # Standard HF URL format: /{username}/{repo}/resolve/{revision}/{file_path}
        elif len(parts) >= 5 and "resolve" in parts:
            resolve_idx = parts.index("resolve")
            if resolve_idx >= 2:
                # Extract repo_id (username/repo)
                result["repo_id"] = "/".join(parts[:resolve_idx])
                # Extract revision
                if resolve_idx + 1 < len(parts):
                    result["revision"] = parts[resolve_idx + 1]
                # Extract filename (everything after revision)
                if resolve_idx + 2 < len(parts):
                    result["filename"] = "/".join(parts[resolve_idx + 2 :])

        # Alternative CDN format: Extract what we can
        elif "cdn" in parsed.netloc:
            # CDN URLs might have different structure
            # Try to extract filename from path
            if len(parts) > 0:
                result["filename"] = parts[-1]

        return result

    def _construct_download_url(
        self, repo_id: str, filename: str, revision: str = "main"
    ) -> str:
        """Construct HuggingFace download URL

        Args:
            repo_id: Repository ID (username/repo)
            filename: File path within repo
            revision: Branch/tag/commit (default: main)

        Returns:
            Download URL
        """
        # URL encode the filename to handle special characters
        encoded_filename = quote(filename, safe="/")
        return f"https://huggingface.co/{repo_id}/resolve/{revision}/{encoded_filename}"

    def download(
        self,
        url: str,
        output_path: str,
        filename: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """Download file from HuggingFace

        Args:
            url: HuggingFace URL to download (http or https)
            output_path: Directory to save file (must be inside models dir)
            filename: Optional filename override (plain name, no path parts)
            force: Force re-download if file exists

        Returns:
            Path to downloaded file

        Raises:
            ValueError: For bad scheme, filename or save path
            Exception: If download fails
        """
        validate_url_scheme(url)
        if filename:
            validate_filename(filename)
        output_dir = self.resolve_output_dir(output_path)

        url_info = self._parse_huggingface_url(url)

        # Convert blob URL to resolve URL if needed
        if url_info["repo_id"] and url_info["filename"]:
            download_url = self._construct_download_url(
                url_info["repo_id"], url_info["filename"], url_info["revision"]
            )
            logger.info("Converted URL to: %s", download_url)
        else:
            download_url = url

        if not filename:
            if url_info["filename"]:
                name = os.path.basename(url_info["filename"])
            else:
                name = self.extract_filename(url, default="model.safetensors")
            filename = safe_server_filename(name, "model.safetensors")

        output_file = os.path.join(output_dir, filename)
        if not self.should_download(output_file, force):
            logger.info("File already exists: %s", output_file)
            return output_file

        headers = {"User-Agent": USER_AGENT}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(download_url, headers=headers)

        try:
            response = self.open_url(request)
        except urllib.error.HTTPError as e:
            self.raise_for_http_status(e.code, e.reason, HTTP_ERROR_HINTS)
        except urllib.error.URLError as e:
            raise Exception(f"Network error: {e.reason}")

        total_size = self.parse_content_length(response)
        logger.info("Downloading %s to %s", filename, output_file)
        return self.save_response(response, output_file, total_size)
