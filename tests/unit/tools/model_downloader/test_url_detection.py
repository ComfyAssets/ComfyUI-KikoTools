"""Tests for URL detection and downloader selection logic"""

import pytest
from kikotools.tools.model_downloader.detector import URLDetector, DownloaderType


class TestURLDetection:
    """Test URL detection and downloader type identification"""

    def test_detect_civitai_api_url(self):
        """Detect CivitAI API download URL"""
        url = "https://civitai.com/api/download/models/123456"
        detector = URLDetector()
        result = detector.detect(url)
        assert result == DownloaderType.CIVITAI

    def test_detect_civitai_model_page_url(self):
        """Detect CivitAI model page URL"""
        url = "https://civitai.com/models/123456/model-name"
        detector = URLDetector()
        result = detector.detect(url)
        assert result == DownloaderType.CIVITAI

    def test_detect_civitai_model_version_url(self):
        """Detect CivitAI model version URL with query parameter"""
        url = "https://civitai.com/models/123456?modelVersionId=789012"
        detector = URLDetector()
        result = detector.detect(url)
        assert result == DownloaderType.CIVITAI

    def test_detect_huggingface_co_url(self):
        """Detect HuggingFace .co domain URL"""
        url = "https://huggingface.co/username/repo-name/resolve/main/model.safetensors"
        detector = URLDetector()
        result = detector.detect(url)
        assert result == DownloaderType.HUGGINGFACE

    def test_detect_huggingface_cdn_url(self):
        """Detect HuggingFace CDN URL"""
        url = "https://cdn.huggingface.co/username/repo/model.safetensors"
        detector = URLDetector()
        result = detector.detect(url)
        assert result == DownloaderType.HUGGINGFACE

    def test_detect_custom_direct_url(self):
        """Detect custom direct download URL"""
        url = "https://example.com/models/checkpoint.safetensors"
        detector = URLDetector()
        result = detector.detect(url)
        assert result == DownloaderType.CUSTOM

    def test_detect_custom_url_with_path(self):
        """Detect custom URL with complex path"""
        url = "https://cdn.example.org/public/ai/models/v1/model.ckpt"
        detector = URLDetector()
        result = detector.detect(url)
        assert result == DownloaderType.CUSTOM

    def test_invalid_url_raises_error(self):
        """Invalid URL should raise ValueError"""
        url = "not-a-valid-url"
        detector = URLDetector()
        with pytest.raises(ValueError, match="Invalid URL"):
            detector.detect(url)

    def test_empty_url_raises_error(self):
        """Empty URL should raise ValueError"""
        url = ""
        detector = URLDetector()
        with pytest.raises(ValueError, match="URL cannot be empty"):
            detector.detect(url)

    def test_none_url_raises_error(self):
        """None URL should raise ValueError"""
        url = None
        detector = URLDetector()
        with pytest.raises(ValueError, match="URL cannot be empty"):
            detector.detect(url)


class TestURLDetectorGetDownloader:
    """Test getting appropriate downloader instances"""

    def test_get_civitai_downloader(self):
        """Get CivitAI downloader instance"""
        url = "https://civitai.com/api/download/models/123456"
        detector = URLDetector()
        downloader = detector.get_downloader(url, api_token="test-token")
        from kikotools.tools.model_downloader.civitai import CivitAIDownloader

        assert isinstance(downloader, CivitAIDownloader)

    def test_get_huggingface_downloader(self):
        """Get HuggingFace downloader instance"""
        url = "https://huggingface.co/user/repo/resolve/main/model.safetensors"
        detector = URLDetector()
        downloader = detector.get_downloader(url, api_token="test-token")
        from kikotools.tools.model_downloader.huggingface import HuggingFaceDownloader

        assert isinstance(downloader, HuggingFaceDownloader)

    def test_get_custom_downloader(self):
        """Get custom URL downloader instance"""
        url = "https://example.com/model.safetensors"
        detector = URLDetector()
        downloader = detector.get_downloader(url)
        from kikotools.tools.model_downloader.custom import CustomDownloader

        assert isinstance(downloader, CustomDownloader)

    def test_downloader_receives_api_token(self):
        """Downloader should receive API token"""
        url = "https://civitai.com/api/download/models/123456"
        detector = URLDetector()
        token = "my-secret-token"
        downloader = detector.get_downloader(url, api_token=token)
        assert downloader.token == token
