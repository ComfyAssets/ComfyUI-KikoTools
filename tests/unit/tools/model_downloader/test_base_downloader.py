"""Tests for base downloader functionality"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from kikotools.tools.model_downloader.base import BaseDownloader


# Create concrete implementation for testing
class TestDownloader(BaseDownloader):
    """Concrete downloader for testing"""

    def download(self, url, output_path, filename=None, force=False):
        """Test implementation"""
        return f"{output_path}/{filename or 'test.file'}"


class TestBaseDownloader:
    """Test base downloader common functionality"""

    def test_init_with_token(self):
        """Initialize downloader with API token"""
        downloader = TestDownloader(token="test-token")
        assert downloader.token == "test-token"

    def test_init_without_token(self):
        """Initialize downloader without token"""
        downloader = TestDownloader()
        assert downloader.token is None

    def test_extract_filename_from_url(self):
        """Extract filename from URL"""
        downloader = TestDownloader()
        url = "https://example.com/path/to/model.safetensors"
        filename = downloader.extract_filename(url)
        assert filename == "model.safetensors"

    def test_extract_filename_with_query_params(self):
        """Extract filename from URL with query parameters"""
        downloader = TestDownloader()
        url = "https://example.com/model.ckpt?download=true&token=abc"
        filename = downloader.extract_filename(url)
        assert filename == "model.ckpt"

    def test_extract_filename_from_content_disposition(self):
        """Extract filename from Content-Disposition header"""
        downloader = TestDownloader()
        content_disposition = 'attachment; filename="custom-model.safetensors"'
        filename = downloader.extract_filename_from_header(content_disposition)
        assert filename == "custom-model.safetensors"

    def test_extract_filename_fallback(self):
        """Fallback to default filename when extraction fails"""
        downloader = TestDownloader()
        url = "https://example.com/"
        filename = downloader.extract_filename(
            url, default="downloaded_model.safetensors"
        )
        assert filename == "downloaded_model.safetensors"

    def test_validate_output_path_exists(self):
        """Validate that output path is a directory"""
        downloader = TestDownloader()
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=True):
                result = downloader.validate_output_path("/tmp/models")
                assert result is True

    def test_validate_output_path_create(self):
        """Create output path if it doesn't exist"""
        downloader = TestDownloader()
        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                downloader.validate_output_path("/tmp/models")
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_validate_output_path_not_directory_raises_error(self):
        """Raise error if output path exists but is not a directory"""
        downloader = TestDownloader()
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.is_dir", return_value=False):
                with pytest.raises(ValueError, match="exists but is not a directory"):
                    downloader.validate_output_path("/tmp/file.txt")

    def test_should_force_download_when_force_true(self):
        """Force download when force=True regardless of file existence"""
        downloader = TestDownloader()
        with patch("pathlib.Path.exists", return_value=True):
            result = downloader.should_download("/tmp/model.safetensors", force=True)
            assert result is True

    def test_should_download_when_file_not_exists(self):
        """Download when file doesn't exist"""
        downloader = TestDownloader()
        with patch("pathlib.Path.exists", return_value=False):
            result = downloader.should_download("/tmp/model.safetensors", force=False)
            assert result is True

    def test_should_not_download_when_file_exists_no_force(self):
        """Skip download when file exists and force=False"""
        downloader = TestDownloader()
        with patch("pathlib.Path.exists", return_value=True):
            result = downloader.should_download("/tmp/model.safetensors", force=False)
            assert result is False

    def test_format_file_size_bytes(self):
        """Format file size in bytes"""
        downloader = TestDownloader()
        assert downloader.format_size(500) == "500.00 B"

    def test_format_file_size_kb(self):
        """Format file size in kilobytes"""
        downloader = TestDownloader()
        assert downloader.format_size(2048) == "2.00 KB"

    def test_format_file_size_mb(self):
        """Format file size in megabytes"""
        downloader = TestDownloader()
        assert downloader.format_size(5242880) == "5.00 MB"

    def test_format_file_size_gb(self):
        """Format file size in gigabytes"""
        downloader = TestDownloader()
        assert downloader.format_size(2147483648) == "2.00 GB"

    def test_download_method_not_implemented(self):
        """download() method should raise NotImplementedError when not overridden"""

        # Create a minimal concrete class without implementing download
        class IncompleteDownloader(BaseDownloader):
            pass

        # Should not be able to instantiate without implementing abstract method
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            downloader = IncompleteDownloader()


class TestBaseDownloaderProgress:
    """Test progress reporting functionality"""

    def test_progress_callback_called(self):
        """Progress callback should be called with correct values"""
        downloader = TestDownloader()
        callback = Mock()
        downloader.set_progress_callback(callback)

        downloader.report_progress(50, 100, "Downloading...")
        callback.assert_called_once_with(50, 100, "Downloading...")

    def test_progress_callback_none_safe(self):
        """Progress reporting should be safe when callback is None"""
        downloader = TestDownloader()
        # Should not raise error
        downloader.report_progress(50, 100, "Downloading...")

    def test_calculate_speed(self):
        """Calculate download speed correctly"""
        downloader = TestDownloader()
        bytes_downloaded = 1048576  # 1 MB
        elapsed_seconds = 1.0
        speed = downloader.calculate_speed(bytes_downloaded, elapsed_seconds)
        assert speed == 1.0  # 1 MB/s

    def test_calculate_speed_zero_time(self):
        """Handle zero elapsed time in speed calculation"""
        downloader = TestDownloader()
        speed = downloader.calculate_speed(1000, 0)
        assert speed == 0.0
