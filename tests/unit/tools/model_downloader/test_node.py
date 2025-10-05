"""Tests for Model Downloader ComfyUI node"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from kikotools.tools.model_downloader.node import ModelDownloaderNode


class TestModelDownloaderNode:
    """Test ModelDownloaderNode functionality"""

    def test_node_has_correct_input_types(self):
        """Node should define correct input types"""
        inputs = ModelDownloaderNode.INPUT_TYPES()

        assert "required" in inputs
        assert "url" in inputs["required"]
        assert "save_path" in inputs["required"]

        assert "optional" in inputs
        assert "filename" in inputs["optional"]
        assert "api_token" in inputs["optional"]
        assert "force_download" in inputs["optional"]

    def test_node_has_correct_return_types(self):
        """Node should return correct types"""
        assert ModelDownloaderNode.RETURN_TYPES == ()

    def test_node_category(self):
        """Node should be in ComfyAssets/Utils category"""
        assert ModelDownloaderNode.CATEGORY == "🫶 ComfyAssets/🛠️ Utils"

    def test_download_empty_url_returns_error(self):
        """Empty URL should return error"""
        node = ModelDownloaderNode()
        result = node.download_model(url="", save_path="/tmp/models")

        assert "ui" in result
        assert "text" in result["ui"]
        assert "URL cannot be empty" in result["ui"]["text"][0]

    def test_download_empty_save_path_returns_error(self):
        """Empty save path should return error"""
        node = ModelDownloaderNode()
        result = node.download_model(
            url="https://example.com/model.safetensors", save_path=""
        )

        assert "ui" in result
        assert "text" in result["ui"]
        assert "Save path cannot be empty" in result["ui"]["text"][0]

    @patch("kikotools.tools.model_downloader.node.URLDetector")
    def test_download_civitai_url(self, mock_detector_class):
        """Download CivitAI URL successfully"""
        # Setup mocks
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        from kikotools.tools.model_downloader.detector import DownloaderType

        mock_detector.detect.return_value = DownloaderType.CIVITAI

        mock_downloader = Mock()
        mock_downloader.download.return_value = "/tmp/models/model.safetensors"
        mock_detector.get_downloader.return_value = mock_downloader

        # Execute
        node = ModelDownloaderNode()
        result = node.download_model(
            url="https://civitai.com/api/download/models/123456",
            save_path="/tmp/models",
        )

        # Verify
        assert "ui" in result
        assert "text" in result["ui"]
        assert "Successfully downloaded" in result["ui"]["text"][0]
        assert "/tmp/models/model.safetensors" in result["ui"]["text"][0]

        mock_detector.detect.assert_called_once()
        mock_detector.get_downloader.assert_called_once()
        mock_downloader.download.assert_called_once()

    @patch("kikotools.tools.model_downloader.node.URLDetector")
    def test_download_huggingface_url(self, mock_detector_class):
        """Download HuggingFace URL successfully"""
        # Setup mocks
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        from kikotools.tools.model_downloader.detector import DownloaderType

        mock_detector.detect.return_value = DownloaderType.HUGGINGFACE

        mock_downloader = Mock()
        mock_downloader.download.return_value = "/tmp/models/hf_model.safetensors"
        mock_detector.get_downloader.return_value = mock_downloader

        # Execute
        node = ModelDownloaderNode()
        result = node.download_model(
            url="https://huggingface.co/user/repo/resolve/main/model.safetensors",
            save_path="/tmp/models",
            api_token="hf_token123",
        )

        # Verify
        assert "ui" in result
        assert "text" in result["ui"]
        assert "Successfully downloaded" in result["ui"]["text"][0]

        # Check that API token was passed
        mock_detector.get_downloader.assert_called_once_with(
            "https://huggingface.co/user/repo/resolve/main/model.safetensors",
            api_token="hf_token123",
        )

    @patch("kikotools.tools.model_downloader.node.URLDetector")
    def test_download_with_custom_filename(self, mock_detector_class):
        """Download with custom filename"""
        # Setup mocks
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        from kikotools.tools.model_downloader.detector import DownloaderType

        mock_detector.detect.return_value = DownloaderType.CUSTOM

        mock_downloader = Mock()
        mock_downloader.download.return_value = "/tmp/models/my_custom_name.safetensors"
        mock_detector.get_downloader.return_value = mock_downloader

        # Execute
        node = ModelDownloaderNode()
        result = node.download_model(
            url="https://example.com/model.safetensors",
            save_path="/tmp/models",
            filename="my_custom_name.safetensors",
        )

        # Verify
        assert "ui" in result
        assert "text" in result["ui"]
        assert "Successfully downloaded" in result["ui"]["text"][0]
        call_args = mock_downloader.download.call_args
        assert call_args.kwargs["filename"] == "my_custom_name.safetensors"

    @patch("kikotools.tools.model_downloader.node.URLDetector")
    def test_download_with_force_flag(self, mock_detector_class):
        """Download with force flag enabled"""
        # Setup mocks
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        from kikotools.tools.model_downloader.detector import DownloaderType

        mock_detector.detect.return_value = DownloaderType.CIVITAI

        mock_downloader = Mock()
        mock_downloader.download.return_value = "/tmp/models/model.safetensors"
        mock_detector.get_downloader.return_value = mock_downloader

        # Execute
        node = ModelDownloaderNode()
        result = node.download_model(
            url="https://civitai.com/api/download/models/123456",
            save_path="/tmp/models",
            force_download=True,
        )

        # Verify
        assert "ui" in result

        # Verify force flag was passed
        call_args = mock_downloader.download.call_args
        assert call_args.kwargs["force"] is True

    @patch("kikotools.tools.model_downloader.node.URLDetector")
    def test_download_handles_value_error(self, mock_detector_class):
        """Handle ValueError (invalid URL) gracefully"""
        # Setup mock to raise ValueError
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector
        mock_detector.detect.side_effect = ValueError("Invalid URL format")

        # Execute
        node = ModelDownloaderNode()
        result = node.download_model(url="not-a-valid-url", save_path="/tmp/models")

        # Verify error handling
        assert "ui" in result
        assert "text" in result["ui"]
        assert "Invalid URL" in result["ui"]["text"][0]

    @patch("kikotools.tools.model_downloader.node.URLDetector")
    def test_download_handles_download_exception(self, mock_detector_class):
        """Handle download exceptions gracefully"""
        # Setup mocks
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        from kikotools.tools.model_downloader.detector import DownloaderType

        mock_detector.detect.return_value = DownloaderType.CIVITAI

        mock_downloader = Mock()
        mock_downloader.download.side_effect = Exception("Network error")
        mock_detector.get_downloader.return_value = mock_downloader

        # Execute
        node = ModelDownloaderNode()
        result = node.download_model(
            url="https://civitai.com/api/download/models/123456",
            save_path="/tmp/models",
        )

        # Verify error handling
        assert "ui" in result
        assert "text" in result["ui"]
        assert "Download failed" in result["ui"]["text"][0]
        assert "Network error" in result["ui"]["text"][0]

    def test_is_changed_returns_different_values(self):
        """IS_CHANGED should return different values to force re-evaluation"""
        import time

        value1 = ModelDownloaderNode.IS_CHANGED(
            url="https://test.com/model.safetensors", save_path="/tmp/models"
        )
        time.sleep(0.01)
        value2 = ModelDownloaderNode.IS_CHANGED(
            url="https://test.com/model.safetensors", save_path="/tmp/models"
        )

        assert value1 != value2
