"""Base downloader class with common functionality"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, List, Optional, Sequence, Union
from urllib.parse import urlparse, unquote
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT = 60  # seconds, applied to every network operation
CHUNK_SIZE = 1638400
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
ALLOWED_SCHEMES = ("http", "https")
PART_SUFFIX = ".part"
# Only model weights and inert data files may be written; never code.
ALLOWED_FILE_EXTENSIONS = frozenset(
    {
        ".safetensors",
        ".sft",
        ".ckpt",
        ".pt",
        ".pt2",
        ".pth",
        ".bin",
        ".gguf",
        ".onnx",
        ".model",
        ".json",
        ".yaml",
        ".yml",
        ".txt",
    }
)
# folder_paths entries that hold code rather than models.
EXCLUDED_FOLDER_NAMES = frozenset({"custom_nodes"})

try:
    import comfy.model_management

    COMFY_AVAILABLE = True
except ImportError:
    COMFY_AVAILABLE = False


def validate_url_scheme(url: str) -> None:
    """Raise ValueError unless url uses an allowed scheme (http/https)."""
    scheme = urlparse(url or "").scheme.lower()
    if scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"Unsupported URL scheme '{scheme}'. Only http and https are allowed."
        )


def validate_filename(name: Optional[str]) -> str:
    """Validate a user-supplied filename.

    Raises:
        ValueError: If the name is empty, a dot name, or contains path parts.
    """
    if (
        not name
        or name in (".", "..")
        or os.path.basename(name) != name
        or "/" in name
        or "\\" in name
        or "\x00" in name
    ):
        raise ValueError(f"Invalid filename: {name!r}")
    return name


def safe_server_filename(name: Optional[str], default: str) -> str:
    """Reduce a server-derived filename to a safe basename, or use default."""
    if name:
        candidate = os.path.basename(name.replace("\\", "/"))
        try:
            return validate_filename(candidate)
        except ValueError:
            pass
    return default


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Only follow http(s) redirects and drop credentials on cross-host hops."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme.lower() not in ALLOWED_SCHEMES:
            raise urllib.error.HTTPError(
                newurl, code, "Redirect to disallowed URL scheme", headers, fp
            )
        new_request = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_request is not None and (
            urlparse(newurl).netloc.lower() != urlparse(req.full_url).netloc.lower()
        ):
            new_request.remove_header("Authorization")
        return new_request


class _NoRedirectProcessor(urllib.request.HTTPErrorProcessor):
    """Return every response as-is so redirects can be handled manually."""

    def http_response(self, request, response):
        return response

    https_response = http_response


def _folder_paths():
    """Return the folder_paths module, or None when unavailable."""
    try:
        import folder_paths

        return folder_paths
    except ImportError:
        return None


def _default_model_roots() -> List[str]:
    """Return ComfyUI's models dir plus every registered model folder.

    Covers extra_model_paths.yaml entries on other drives.
    """
    fp = _folder_paths()
    if fp is None:
        return []
    roots: List[str] = []
    models_dir = getattr(fp, "models_dir", None)
    if isinstance(models_dir, str) and models_dir:
        roots.append(models_dir)
    registry = getattr(fp, "folder_names_and_paths", None)
    if isinstance(registry, dict):
        for name, entry in registry.items():
            if name in EXCLUDED_FOLDER_NAMES:
                continue
            try:
                paths = entry[0]
            except (TypeError, IndexError, KeyError):
                continue
            if isinstance(paths, (list, tuple)):
                roots.extend(p for p in paths if isinstance(p, str) and p)
    return roots


def _default_base_path() -> Optional[str]:
    """Return ComfyUI's base path used to resolve relative save paths."""
    fp = _folder_paths()
    base = getattr(fp, "base_path", None) if fp is not None else None
    return base if isinstance(base, str) and base else None


class BaseDownloader(ABC):
    """Abstract base class for all downloaders"""

    def __init__(
        self,
        token: Optional[str] = None,
        models_root: Union[str, Sequence[str], None] = None,
    ):
        """Initialize downloader with optional API token

        Args:
            token: Optional API token for authentication
            models_root: Directory (or list of directories) downloads must
                stay inside. Defaults to ComfyUI's models directory plus all
                registered model folders.
        """
        self.token = token
        if isinstance(models_root, str):
            models_root = [models_root]
        self._models_root = list(models_root) if models_root else None
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
        if not content_disposition:
            return None
        match = re.search(r"filename\*\s*=\s*[^']*'[^']*'([^;]+)", content_disposition)
        if match:
            return unquote(match.group(1).strip()) or None
        match = re.search(
            r'filename\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^;]+))', content_disposition
        )
        if match:
            value = next(g for g in match.groups() if g is not None)
            return value.strip() or None
        return None

    @staticmethod
    def _is_within(path: str, root: str) -> bool:
        try:
            return os.path.commonpath([root, path]) == root
        except ValueError:  # different drives
            return False

    def resolve_output_dir(self, output_path: str) -> str:
        """Resolve output_path and ensure it lives inside the models root.

        Returns:
            Real (symlink-resolved) directory path, created if missing.

        Raises:
            ValueError: If the path escapes the models directory.
        """
        roots = self._models_root or _default_model_roots()
        if not roots:
            raise ValueError("Models directory is unavailable; refusing to download")
        if not os.path.isabs(output_path):
            output_path = os.path.join(_default_base_path() or os.getcwd(), output_path)
        real_dir = os.path.realpath(output_path)
        real_roots = [os.path.realpath(r) for r in roots]
        if not any(self._is_within(real_dir, r) for r in real_roots):
            raise ValueError(
                f"Save path must be inside a ComfyUI models directory "
                f"({', '.join(real_roots)})"
            )
        self.validate_output_path(real_dir)
        return real_dir

    def open_url(self, request: urllib.request.Request, follow_redirects: bool = True):
        """Open a request with scheme checks, timeout and safe redirects."""
        validate_url_scheme(request.full_url)
        handler = _SafeRedirectHandler if follow_redirects else _NoRedirectProcessor
        opener = urllib.request.build_opener(handler)
        return opener.open(request, timeout=DOWNLOAD_TIMEOUT)

    @staticmethod
    def parse_content_length(response: Any) -> Optional[int]:
        """Return Content-Length as int, or None if absent/invalid."""
        value = response.getheader("Content-Length")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def save_response(
        self,
        response: Any,
        output_file: str,
        total_size: Optional[int],
        strict_size: bool = True,
    ) -> str:
        """Stream response to output_file atomically via a .part file.

        The .part file is removed on any failure (including interrupts).

        Raises:
            ValueError: If output_file is not a model/data file type.
        """
        extension = os.path.splitext(output_file)[1].lower()
        if extension not in ALLOWED_FILE_EXTENSIONS:
            raise ValueError(
                f"Refusing to save file type '{extension or 'none'}': "
                f"only model files ({', '.join(sorted(ALLOWED_FILE_EXTENSIONS))})"
            )
        part_file = output_file + PART_SUFFIX
        try:
            downloaded = 0
            start_time = time.time()
            with open(part_file, "wb") as f:
                while True:
                    chunk_start = time.time()
                    buffer = response.read(CHUNK_SIZE)
                    chunk_time = time.time() - chunk_start
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    f.write(buffer)
                    self.check_interrupt()
                    speed = self.calculate_speed(len(buffer), chunk_time)
                    self._report_chunk(downloaded, total_size, speed)
            sys.stdout.write("\n")

            actual_size = os.path.getsize(part_file)
            if total_size and actual_size != total_size:
                message = (
                    f"Download incomplete. Expected {total_size} bytes, "
                    f"got {actual_size} bytes"
                )
                if strict_size:
                    raise Exception(message)
                logger.warning(message)

            os.replace(part_file, output_file)
            logger.info(
                "Download completed in %.0fs: %s", time.time() - start_time, output_file
            )
            return output_file
        except BaseException:
            if os.path.exists(part_file):
                os.remove(part_file)
            raise
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()

    def _report_chunk(
        self, downloaded: int, total_size: Optional[int], speed: float
    ) -> None:
        """Write console progress and notify the callback."""
        if total_size:
            progress = downloaded / total_size
            sys.stdout.write(
                f'\r[{"=" * int(progress * 50):<50}] {progress * 100:.2f}% - {speed:.2f} MB/s'
            )
            self.report_progress(downloaded, total_size, f"{speed:.2f} MB/s")
        else:
            sys.stdout.write(
                f"\rDownloaded: {self.format_size(downloaded)} - {speed:.2f} MB/s"
            )
            self.report_progress(downloaded, 0, f"{speed:.2f} MB/s")
        sys.stdout.flush()

    def raise_for_http_status(self, code: int, reason: str, hints: dict) -> None:
        """Raise a friendly Exception for an HTTP error status."""
        message = hints.get(code)
        if message is None and code == 429:
            message = "Rate limited. Please wait a moment before trying again."
        raise Exception(message or f"HTTP error {code}: {reason}")

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
