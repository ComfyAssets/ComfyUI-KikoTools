"""Tests for HuggingFace downloader"""

import pytest
from kikotools.tools.model_downloader.huggingface import HuggingFaceDownloader


class TestHuggingFaceURLParsing:
    """Test HuggingFace URL parsing"""

    def test_parse_blob_url(self):
        """Parse blob URL (web UI format)"""
        downloader = HuggingFaceDownloader()
        url = "https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/blob/main/Wan22Animate/Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors"

        result = downloader._parse_huggingface_url(url)

        assert result["repo_id"] == "Kijai/WanVideo_comfy_fp8_scaled"
        assert result["revision"] == "main"
        assert (
            result["filename"]
            == "Wan22Animate/Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors"
        )

    def test_parse_resolve_url(self):
        """Parse resolve URL (download format)"""
        downloader = HuggingFaceDownloader()
        url = "https://huggingface.co/username/repo/resolve/main/model.safetensors"

        result = downloader._parse_huggingface_url(url)

        assert result["repo_id"] == "username/repo"
        assert result["revision"] == "main"
        assert result["filename"] == "model.safetensors"

    def test_parse_resolve_url_with_subdirectory(self):
        """Parse resolve URL with subdirectory"""
        downloader = HuggingFaceDownloader()
        url = (
            "https://huggingface.co/user/repo/resolve/main/subfolder/model.safetensors"
        )

        result = downloader._parse_huggingface_url(url)

        assert result["repo_id"] == "user/repo"
        assert result["revision"] == "main"
        assert result["filename"] == "subfolder/model.safetensors"

    def test_parse_blob_url_with_branch(self):
        """Parse blob URL with non-main branch"""
        downloader = HuggingFaceDownloader()
        url = "https://huggingface.co/user/repo/blob/dev/model.safetensors"

        result = downloader._parse_huggingface_url(url)

        assert result["repo_id"] == "user/repo"
        assert result["revision"] == "dev"
        assert result["filename"] == "model.safetensors"

    def test_construct_download_url(self):
        """Construct proper download URL"""
        downloader = HuggingFaceDownloader()

        url = downloader._construct_download_url(
            "Kijai/WanVideo_comfy_fp8_scaled",
            "Wan22Animate/Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors",
            "main",
        )

        expected = "https://huggingface.co/Kijai/WanVideo_comfy_fp8_scaled/resolve/main/Wan22Animate/Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors"
        assert url == expected

    def test_construct_download_url_with_special_characters(self):
        """Construct download URL with special characters in filename"""
        downloader = HuggingFaceDownloader()

        url = downloader._construct_download_url(
            "user/repo", "models/file name with spaces.safetensors", "main"
        )

        assert "file%20name%20with%20spaces" in url
        assert "/resolve/main/" in url
