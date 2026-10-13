"""Custom URL downloader - best effort for direct download links"""

import logging
import os
import urllib.error
import urllib.request
from typing import Optional

from .base import (
    USER_AGENT,
    BaseDownloader,
    safe_server_filename,
    validate_filename,
    validate_url_scheme,
)

logger = logging.getLogger(__name__)

DEFAULT_FILENAME = "downloaded_model.safetensors"

HTTP_ERROR_HINTS = {
    401: "Authentication required. Please provide a valid token if needed.",
    403: "Access forbidden. The URL might require authentication or special permissions.",
    404: "File not found. Please check the URL.",
}


class CustomDownloader(BaseDownloader):
    """Best-effort downloader for custom/direct URLs

    The optional token is sent as a Bearer token and is dropped automatically
    if the server redirects to a different host.
    """

    def download(
        self,
        url: str,
        output_path: str,
        filename: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """Download file from custom URL

        Args:
            url: Direct download URL (http or https)
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

        # Fast path: a known filename lets us skip the request entirely
        if filename:
            output_file = os.path.join(output_dir, filename)
            if not self.should_download(output_file, force):
                logger.info("File already exists: %s", output_file)
                return output_file

        headers = {"User-Agent": USER_AGENT}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers)

        try:
            response = self.open_url(request)
        except urllib.error.HTTPError as e:
            self.raise_for_http_status(e.code, e.reason, HTTP_ERROR_HINTS)
        except urllib.error.URLError as e:
            raise Exception(f"Network error: {e.reason}")

        if not filename:
            header_name = self.extract_filename_from_header(
                response.getheader("Content-Disposition") or ""
            )
            filename = safe_server_filename(
                header_name, self.extract_filename(url, default=DEFAULT_FILENAME)
            )
            output_file = os.path.join(output_dir, filename)
            if not self.should_download(output_file, force):
                response.close()
                logger.info("File already exists: %s", output_file)
                return output_file

        total_size = self.parse_content_length(response)
        logger.info("Downloading %s to %s", filename, output_file)

        # Size mismatch is only a warning for arbitrary URLs
        return self.save_response(response, output_file, total_size, strict_size=False)
