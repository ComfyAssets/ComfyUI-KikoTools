"""CivitAI downloader implementation"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs, unquote

from .base import BaseDownloader

try:
    import comfy.model_management

    COMFY_AVAILABLE = True
    InterruptProcessingException = comfy.model_management.InterruptProcessingException
except ImportError:
    COMFY_AVAILABLE = False
    # Fallback exception type that will never be raised
    InterruptProcessingException = type(
        "InterruptProcessingException", (Exception,), {}
    )


CHUNK_SIZE = 1638400
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
API_BASE = "https://civitai.com/api/v1"
MAX_RETRIES = 3
RETRY_DELAY = 5


class CivitAIDownloader(BaseDownloader):
    """Downloader for CivitAI models"""

    def __init__(self, token: Optional[str] = None):
        """Initialize CivitAI downloader

        Args:
            token: Optional CivitAI API token
        """
        super().__init__(token)

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
            with urllib.request.urlopen(request) as response:
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
        # Validate output path
        self.validate_output_path(output_path)

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

        # Disable automatic redirect handling
        class NoRedirection(urllib.request.HTTPErrorProcessor):
            def http_response(self, request, response):
                return response

            https_response = http_response

        request = urllib.request.Request(url, headers=headers)
        opener = urllib.request.build_opener(NoRedirection)

        try:
            response = opener.open(request)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise Exception(
                    "Authentication required. Please provide a valid API token."
                )
            elif e.code == 403:
                raise Exception(
                    "Access forbidden. The model might be restricted or require special permissions."
                )
            elif e.code == 404:
                raise Exception(
                    "Model not found. The URL might be incorrect or the model was removed."
                )
            elif e.code == 429:
                raise Exception(
                    "Rate limited. Please wait a moment before trying again."
                )
            else:
                raise Exception(f"HTTP error {e.code}: {e.reason}")

        # Handle redirects
        if response.status in [301, 302, 303, 307, 308]:
            redirect_url = response.getheader("Location")

            # Handle relative redirects
            if redirect_url.startswith("/"):
                base_url = urlparse(url)
                redirect_url = f"{base_url.scheme}://{base_url.netloc}{redirect_url}"

            # Extract filename from redirect URL if not provided
            if not filename:
                parsed_url = urlparse(redirect_url)
                query_params = parse_qs(parsed_url.query)
                content_disposition = query_params.get(
                    "response-content-disposition", [None]
                )[0]

                if content_disposition and "filename=" in content_disposition:
                    filename = unquote(
                        content_disposition.split("filename=")[1].strip('"')
                    )
                else:
                    # Fallback: extract filename from URL path
                    path = parsed_url.path
                    if path and "/" in path:
                        filename = path.split("/")[-1]
                    else:
                        filename = "downloaded_file.safetensors"

            response = urllib.request.urlopen(redirect_url)
        elif response.status == 404:
            raise Exception("File not found")
        elif response.status != 200:
            raise Exception(f"Download failed with status {response.status}")

        # Use provided filename or extracted filename
        if not filename:
            filename = self.extract_filename(url, default="model.safetensors")

        output_file = os.path.join(output_path, filename)

        # Check if should download
        if not self.should_download(output_file, force):
            print(f"File already exists: {output_file}")
            return output_file

        total_size = response.getheader("Content-Length")
        if total_size is not None:
            total_size = int(total_size)

        print(f"Downloading: {filename}")
        print(f"Destination: {output_file}")
        if total_size:
            print(f"Size: {self.format_size(total_size)}")

        # Download with progress
        try:
            with open(output_file, "wb") as f:
                downloaded = 0
                start_time = time.time()

                while True:
                    chunk_start_time = time.time()
                    buffer = response.read(CHUNK_SIZE)
                    chunk_end_time = time.time()

                    if not buffer:
                        break

                    downloaded += len(buffer)
                    f.write(buffer)
                    chunk_time = chunk_end_time - chunk_start_time

                    # Check for user cancellation
                    self.check_interrupt()

                    # Calculate speed
                    speed = self.calculate_speed(len(buffer), chunk_time)

                    # Report progress
                    if total_size is not None:
                        progress = downloaded / total_size
                        sys.stdout.write(
                            f'\r[{"=" * int(progress * 50):<50}] {progress * 100:.2f}% - {speed:.2f} MB/s'
                        )
                        sys.stdout.flush()
                        self.report_progress(
                            downloaded, total_size, f"{speed:.2f} MB/s"
                        )
                    else:
                        sys.stdout.write(
                            f"\rDownloaded: {self.format_size(downloaded)} - {speed:.2f} MB/s"
                        )
                        sys.stdout.flush()
                        self.report_progress(downloaded, 0, f"{speed:.2f} MB/s")

            end_time = time.time()
            time_taken = end_time - start_time
            hours, remainder = divmod(time_taken, 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours > 0:
                time_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            elif minutes > 0:
                time_str = f"{int(minutes)}m {int(seconds)}s"
            else:
                time_str = f"{int(seconds)}s"

            sys.stdout.write("\n")
            print(f"✓ Download completed in {time_str}")
            print(f"✓ File saved as: {output_file}")

            # Verify file size
            actual_size = os.path.getsize(output_file)
            if total_size and actual_size != total_size:
                raise Exception(
                    f"Download incomplete. Expected {total_size} bytes, got {actual_size} bytes"
                )

            return output_file
        except InterruptProcessingException:
            # Clean up partial download on interrupt
            if os.path.exists(output_file):
                os.remove(output_file)
            raise InterruptProcessingException("Download interrupted")
