"""Custom URL downloader - best effort for direct download links"""

import os
import sys
import time
import urllib.request
import urllib.error
from typing import Optional

from .base import BaseDownloader


CHUNK_SIZE = 1638400
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class CustomDownloader(BaseDownloader):
    """Best-effort downloader for custom/direct URLs"""

    def __init__(self, token: Optional[str] = None):
        """Initialize custom downloader

        Args:
            token: Optional authentication token (will be sent as Bearer token)
        """
        super().__init__(token)

    def download(
        self,
        url: str,
        output_path: str,
        filename: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """Download file from custom URL

        Args:
            url: Direct download URL
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

        # Determine filename
        if not filename:
            filename = self.extract_filename(
                url, default="downloaded_model.safetensors"
            )

        output_file = os.path.join(output_path, filename)

        # Check if should download
        if not self.should_download(output_file, force):
            print(f"File already exists: {output_file}")
            return output_file

        # Prepare headers
        headers = {"User-Agent": USER_AGENT}

        # Add authentication if token provided
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Create request
        request = urllib.request.Request(url, headers=headers)

        try:
            # First request to check if file exists and get metadata
            response = urllib.request.urlopen(request)

            # Try to extract filename from Content-Disposition header if not provided
            if not filename:
                content_disposition = response.getheader("Content-Disposition")
                if content_disposition:
                    extracted_filename = self.extract_filename_from_header(
                        content_disposition
                    )
                    if extracted_filename:
                        filename = extracted_filename
                        output_file = os.path.join(output_path, filename)

        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise Exception(
                    "Authentication required. Please provide a valid token if needed."
                )
            elif e.code == 403:
                raise Exception(
                    "Access forbidden. The URL might require authentication or special permissions."
                )
            elif e.code == 404:
                raise Exception("File not found. Please check the URL.")
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
        else:
            print("Size: Unknown")

        # Download with progress
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

                # Calculate speed
                speed = self.calculate_speed(len(buffer), chunk_time)

                # Report progress
                if total_size is not None:
                    progress = downloaded / total_size
                    sys.stdout.write(
                        f'\r[{"=" * int(progress * 50):<50}] {progress * 100:.2f}% - {speed:.2f} MB/s'
                    )
                    sys.stdout.flush()
                    self.report_progress(downloaded, total_size, f"{speed:.2f} MB/s")
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

        # Verify file size if known
        actual_size = os.path.getsize(output_file)
        if total_size and actual_size != total_size:
            print(
                f"⚠ Warning: Downloaded size ({actual_size} bytes) doesn't match expected size ({total_size} bytes)"
            )
            # Don't raise error for custom URLs as size mismatch might be acceptable

        return output_file
