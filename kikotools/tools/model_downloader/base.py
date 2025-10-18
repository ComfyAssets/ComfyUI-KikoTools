"""Base downloader class with common functionality"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse, unquote
import os

try:
    import comfy.model_management

    COMFY_AVAILABLE = True
except ImportError:
    COMFY_AVAILABLE = False


class BaseDownloader(ABC):
    """Abstract base class for all downloaders"""

    def __init__(self, token: Optional[str] = None):
        """Initialize downloader with optional API token

        Args:
            token: Optional API token for authentication
        """
        self.token = token
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None

    def set_progress_callback(self, callback: Callable[[int, int, str], None]) -> None:
        """Set callback function for progress updates

        Args:
            callback: Function(downloaded_bytes, total_bytes, message)
        """
        self._progress_callback = callback

    def report_progress(self, downloaded: int, total: int, message: str = "") -> None:
        """Report download progress to callback

        Args:
            downloaded: Bytes downloaded so far
            total: Total bytes to download
            message: Optional status message
        """
        if self._progress_callback:
            self._progress_callback(downloaded, total, message)

    def check_interrupt(self) -> None:
        """Check if processing has been interrupted by user

        Raises:
            comfy.model_management.InterruptProcessingException: If user cancelled
        """
        if COMFY_AVAILABLE:
            comfy.model_management.throw_exception_if_processing_interrupted()

    def extract_filename(self, url: str, default: str = "downloaded_file") -> str:
        """Extract filename from URL

        Args:
            url: URL to extract filename from
            default: Default filename if extraction fails

        Returns:
            Extracted or default filename
        """
        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)
            filename = os.path.basename(path)

            # Remove query parameters from filename
            if "?" in filename:
                filename = filename.split("?")[0]

            # Validate filename
            if filename and len(filename) > 0 and "." in filename:
                return filename
        except Exception:
            pass

        return default

    def extract_filename_from_header(self, content_disposition: str) -> Optional[str]:
        """Extract filename from Content-Disposition header

        Args:
            content_disposition: Content-Disposition header value

        Returns:
            Extracted filename or None
        """
        try:
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[1]
                # Remove quotes and whitespace
                filename = filename.strip().strip('"').strip("'")
                return filename
        except Exception:
            pass
        return None

    def validate_output_path(self, output_path: str) -> bool:
        """Validate and create output path if needed

        Args:
            output_path: Directory path to validate

        Returns:
            True if valid

        Raises:
            ValueError: If path exists but is not a directory
        """
        path = Path(output_path)

        if path.exists():
            if not path.is_dir():
                raise ValueError(
                    f"Output path {output_path} exists but is not a directory"
                )
            return True

        # Create directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)
        return True

    def should_download(self, file_path: str, force: bool = False) -> bool:
        """Check if file should be downloaded

        Args:
            file_path: Full path to file
            force: Force download even if file exists

        Returns:
            True if should download, False if file exists and force=False
        """
        if force:
            return True

        return not Path(file_path).exists()

    def format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string (e.g., "5.00 MB")
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def calculate_speed(self, bytes_downloaded: int, elapsed_seconds: float) -> float:
        """Calculate download speed in MB/s

        Args:
            bytes_downloaded: Number of bytes downloaded
            elapsed_seconds: Time elapsed in seconds

        Returns:
            Download speed in MB/s
        """
        if elapsed_seconds <= 0:
            return 0.0

        mb_downloaded = bytes_downloaded / (1024 * 1024)
        return mb_downloaded / elapsed_seconds

    @abstractmethod
    def download(
        self,
        url: str,
        output_path: str,
        filename: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """Download file from URL

        Args:
            url: URL to download from
            output_path: Directory to save file
            filename: Optional filename override
            force: Force re-download if file exists

        Returns:
            Path to downloaded file

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Subclasses must implement download()")
