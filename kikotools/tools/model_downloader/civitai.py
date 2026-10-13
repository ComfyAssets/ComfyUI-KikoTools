"""CivitAI downloader implementation"""

import json
import logging
import os
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, unquote, urljoin

from .base import (
    USER_AGENT,
    BaseDownloader,
    safe_server_filename,
    validate_filename,
    validate_url_scheme,
)

logger = logging.getLogger(__name__)

API_BASE = "https://civitai.com/api/v1"
REDIRECT_STATUSES = (301, 302, 303, 307, 308)

HTTP_ERROR_HINTS = {
    401: "Authentication required. Please provide a valid API token.",
    403: "Access forbidden. The model might be restricted or require special permissions.",
    404: "Model not found. The URL might be incorrect or the model was removed.",
}


class CivitAIDownloader(BaseDownloader):
    """Downloader for CivitAI models"""

    def _make_request(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> urllib.request.Request:
        """Create HTTP request with authentication

        Args:
            url: URL to request
            headers: Optional additional headers

        Returns:
            urllib Request object
        """
        if headers is None:
            headers = {}

        headers["User-Agent"] = USER_AGENT
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return urllib.request.Request(url, headers=headers)

    def _parse_civitai_url(self, url: str) -> Dict[str, Optional[int]]:
        """Extract model and version IDs from CivitAI URL

        Args:
            url: CivitAI URL to parse

        Returns:
            Dict with 'model_id' and 'version_id' keys
        """
        parsed = urlparse(url)
        result = {"model_id": None, "version_id": None}

        # Handle different URL patterns
        # 1. Direct API download URL: /api/download/models/123456
        if "/api/download/models/" in url:
            match = url.split("/api/download/models/")[-1].split("?")[0]
            if match.isdigit():
                result["version_id"] = int(match)
                return result

        # 2. Model page URL: /models/123456 or /models/123456/model-name
        if "/models/" in url:
            parts = parsed.path.split("/")
            if "models" in parts:
                idx = parts.index("models")
                if idx + 1 < len(parts) and parts[idx + 1].isdigit():
                    result["model_id"] = int(parts[idx + 1])

        # 3. Version specific URL with ?modelVersionId=789012
        query_params = parse_qs(parsed.query)
        if "modelVersionId" in query_params:
            version_id = query_params["modelVersionId"][0]
            if version_id.isdigit():
                result["version_id"] = int(version_id)

        return result

    def get_model_details(self, model_id: int) -> Dict[str, Any]:
        """Get model details from API

        Args:
            model_id: CivitAI model ID

        Returns:
            Model details dictionary

        Raises:
            Exception: If API request fails
        """
        url = f"{API_BASE}/models/{model_id}"
        request = self._make_request(url)

        try:
            with self.open_url(request) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise Exception(f"Model {model_id} not found")
            raise Exception(f"API request failed: {e}")

    def download(
        self,
        url: str,
        output_path: str,
        filename: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """Download file from CivitAI

        Args:
            url: CivitAI URL to download
            output_path: Directory to save file
            filename: Optional filename override
            force: Force re-download if file exists

        Returns:
            Path to downloaded file

        Raises:
            Exception: If download fails
        """
        validate_url_scheme(url)
        if filename:
            validate_filename(filename)
        output_dir = self.resolve_output_dir(output_path)

        # Validate that URL is from civitai.com domain
        parsed_url = urlparse(url)
        if parsed_url.netloc not in ("civitai.com", "www.civitai.com"):
            raise ValueError(
                f"Invalid URL: Only civitai.com URLs are supported, got {parsed_url.netloc}"
            )

        # Convert web URL to API URL if needed
        if "/api/download/models/" not in url:
            ids = self._parse_civitai_url(url)

            # If we have a version ID, use it directly
            if ids["version_id"]:
                url = f"https://civitai.com/api/download/models/{ids['version_id']}"
            # If we only have a model ID, get the latest version
            elif ids["model_id"]:
                try:
                    model_details = self.get_model_details(ids["model_id"])
                    if model_details.get("modelVersions"):
                        version_id = model_details["modelVersions"][0]["id"]
                        url = f"https://civitai.com/api/download/models/{version_id}"
                    else:
                        raise Exception(
                            f"No versions found for model {ids['model_id']}"
                        )
                except Exception as e:
                    raise Exception(f"Failed to get model details: {e}")
            else:
                raise Exception("Could not parse model or version ID from URL")

        headers = {"User-Agent": USER_AGENT}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)

        try:
            response = self.open_url(request, follow_redirects=False)
        except urllib.error.HTTPError as e:
            self.raise_for_http_status(e.code, e.reason, HTTP_ERROR_HINTS)
        except urllib.error.URLError as e:
            raise Exception(f"Network error: {e.reason}")

        if response.status in REDIRECT_STATUSES:
            redirect_url = response.getheader("Location")
            response.close()
            if not redirect_url:
                raise Exception("Redirect response did not include a Location header")
            redirect_url = urljoin(url, redirect_url)
            validate_url_scheme(redirect_url)

            if not filename:
                filename = self._filename_from_redirect(redirect_url)

            # The signed redirect target gets no credentials
            try:
                response = self.open_url(
                    urllib.request.Request(
                        redirect_url, headers={"User-Agent": USER_AGENT}
                    )
                )
            except urllib.error.HTTPError as e:
                self.raise_for_http_status(e.code, e.reason, HTTP_ERROR_HINTS)
            except urllib.error.URLError as e:
                raise Exception(f"Network error: {e.reason}")
        elif response.status != 200:
            code = response.status
            response.close()
            self.raise_for_http_status(
                code, "Download failed", {**HTTP_ERROR_HINTS, 404: "File not found"}
            )

        if not filename:
            filename = safe_server_filename(
                self.extract_filename(url, default="model.safetensors"),
                "model.safetensors",
            )

        output_file = os.path.join(output_dir, filename)
        if not self.should_download(output_file, force):
            response.close()
            logger.info("File already exists: %s", output_file)
            return output_file

        total_size = self.parse_content_length(response)
        logger.info("Downloading %s to %s", filename, output_file)
        return self.save_response(response, output_file, total_size)

    def _filename_from_redirect(self, redirect_url: str) -> str:
        """Derive a safe filename from a CivitAI redirect URL."""
        parsed = urlparse(redirect_url)
        disposition = parse_qs(parsed.query).get("response-content-disposition", [""])[
            0
        ]
        name = self.extract_filename_from_header(unquote(disposition))
        if not name:
            name = parsed.path.rsplit("/", 1)[-1]
        return safe_server_filename(name, "downloaded_file.safetensors")
