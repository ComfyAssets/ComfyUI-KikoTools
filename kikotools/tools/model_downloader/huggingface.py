"""HuggingFace downloader implementation"""

import os
import sys
import time
import urllib.request
import urllib.error
from typing import Optional
from urllib.parse import urlparse, quote

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


class HuggingFaceDownloader(BaseDownloader):
    """Downloader for HuggingFace models"""

    def __init__(self, token: Optional[str] = None):
        """Initialize HuggingFace downloader

        Args:
            token: Optional HuggingFace API token
        """
        super().__init__(token)

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
            url: HuggingFace URL to download
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

        # Parse URL to get file information
        url_info = self._parse_huggingface_url(url)

        # Convert blob URL to resolve URL if needed
        if url_info["repo_id"] and url_info["filename"]:
            download_url = self._construct_download_url(
                url_info["repo_id"], url_info["filename"], url_info["revision"]
            )
            print(f"[HuggingFace] Converted URL to: {download_url}")
        else:
            # Use original URL if parsing failed
            download_url = url

        # Determine filename
        if not filename:
            if url_info["filename"]:
                # Use just the basename from the URL
                filename = os.path.basename(url_info["filename"])
            else:
                filename = self.extract_filename(url, default="model.safetensors")

        output_file = os.path.join(output_path, filename)

        # Check if should download
        if not self.should_download(output_file, force):
            print(f"File already exists: {output_file}")
            return output_file

        # Prepare headers
        headers = {"User-Agent": USER_AGENT}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Create request with converted download URL
        request = urllib.request.Request(download_url, headers=headers)

        try:
            response = urllib.request.urlopen(request)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise Exception(
                    "Authentication required. Please provide a valid HuggingFace token."
                )
            elif e.code == 403:
                raise Exception(
                    "Access forbidden. The model might be gated or require special permissions."
                )
            elif e.code == 404:
                raise Exception(
                    "File not found. The URL might be incorrect or the file was removed."
                )
            elif e.code == 429:
                raise Exception(
                    "Rate limited. Please wait a moment before trying again."
                )
            else:
                raise Exception(f"HTTP error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Network error: {e.reason}")

        # Get file size
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
            raise
