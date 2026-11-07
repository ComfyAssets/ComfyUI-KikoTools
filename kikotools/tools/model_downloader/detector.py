"""URL detection and downloader selection logic"""

from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

from .tokens import resolve_token

if TYPE_CHECKING:
    from .base import BaseDownloader

# Civitai serves models on civitai.com, civitai.green (SFW) and civitai.red (mature).
CIVITAI_HOSTS = (
    "civitai.com",
    "www.civitai.com",
    "civitai.green",
    "www.civitai.green",
    "civitai.red",
    "www.civitai.red",
)


class DownloaderType(Enum):
    """Types of supported downloaders"""

    CIVITAI = "civitai"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


class URLDetector:
    """Detects URL type and returns appropriate downloader"""

    def detect(self, url: Optional[str]) -> DownloaderType:
        """Detect which downloader to use based on URL

        Args:
            url: URL to analyze

        Returns:
            DownloaderType enum value

        Raises:
            ValueError: If URL is invalid or empty
        """
        if not url:
            raise ValueError("URL cannot be empty")

        url = url.strip()
        if not url:
            raise ValueError("URL cannot be empty")

        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception:
            raise ValueError("Invalid URL")

        # Check for CivitAI
        if self._is_civitai_url(url, parsed):
            return DownloaderType.CIVITAI

        # Check for HuggingFace
        if self._is_huggingface_url(url, parsed):
            return DownloaderType.HUGGINGFACE

        # Default to custom downloader
        return DownloaderType.CUSTOM

    def _is_civitai_url(self, url: str, parsed) -> bool:
        """Check if URL is from CivitAI

        Args:
            url: Full URL string
            parsed: Parsed URL object

        Returns:
            True if CivitAI URL
        """
        # Validate exact domain match to prevent subdomain attacks
        if parsed.netloc not in CIVITAI_HOSTS:
            return False

        # Check for API download endpoint
        if "/api/download/models/" in url:
            return True

        # Check for model page
        if "/models/" in url:
            return True

        return False

    def _is_huggingface_url(self, url: str, parsed) -> bool:
        """Check if URL is from HuggingFace

        Args:
            url: Full URL string
            parsed: Parsed URL object

        Returns:
            True if HuggingFace URL
        """
        # Validate exact domain match to prevent subdomain attacks
        # Support both main domain and CDN domains
        allowed_domains = (
            "huggingface.co",
            "www.huggingface.co",
            "cdn.huggingface.co",
            "cdn-lfs.huggingface.co",
        )
        if parsed.netloc in allowed_domains:
            return True

        return False

    def get_downloader(
        self, url: str, api_token: Optional[str] = None
    ) -> "BaseDownloader":
        """Get appropriate downloader instance for URL

        Args:
            url: URL to download from
            api_token: Optional token typed on the node. When empty, Civitai and
                Hugging Face use the server's token (see tokens.py); other hosts
                get none.

        Returns:
            Appropriate downloader instance

        Raises:
            ValueError: If URL is invalid
        """
        downloader_type = self.detect(url)

        if downloader_type == DownloaderType.CIVITAI:
            from .civitai import CivitAIDownloader

            return CivitAIDownloader(token=resolve_token("civitai", api_token))

        elif downloader_type == DownloaderType.HUGGINGFACE:
            from .huggingface import HuggingFaceDownloader

            return HuggingFaceDownloader(token=resolve_token("huggingface", api_token))

        else:  # CUSTOM
            from .custom import CustomDownloader

            return CustomDownloader(token=resolve_token("custom", api_token))
