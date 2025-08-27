"""Unit tests for Local Image Loader tool."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import torch
from PIL import Image, PngImagePlugin

from kikotools.tools.local_image_loader.logic import (
    create_empty_tensor,
    get_supported_extensions,
    load_image_from_path,
    scan_directory,
)
from kikotools.tools.local_image_loader.node import LocalImageLoaderNode


class TestLocalImageLoaderLogic:
    """Test the logic functions for local image loader."""

    def test_get_supported_extensions(self):
        """Test getting supported file extensions."""
        extensions = get_supported_extensions()

        assert "image" in extensions
        assert "video" in extensions
        assert "audio" in extensions

        assert ".jpg" in extensions["image"]
        assert ".png" in extensions["image"]
        assert ".mp4" in extensions["video"]
        assert ".mp3" in extensions["audio"]

    def test_create_empty_tensor(self):
        """Test creating an empty tensor."""
        tensor = create_empty_tensor()

        assert isinstance(tensor, torch.Tensor)
        assert tensor.shape == (1, 1, 1, 4)
        assert torch.all(tensor == 0)

    def test_load_image_from_path_rgb(self):
        """Test loading an RGB image from file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            # Create a test image
            img = Image.new("RGB", (100, 100), color="red")
            img.save(tmp.name)

            try:
                tensor, metadata = load_image_from_path(tmp.name)

                # Check tensor
                assert isinstance(tensor, torch.Tensor)
                assert tensor.shape == (1, 100, 100, 3)
                assert tensor.min() >= 0.0
                assert tensor.max() <= 1.0

                # Check metadata
                assert metadata["width"] == 100
                assert metadata["height"] == 100
                assert metadata["filename"] == os.path.basename(tmp.name)
                assert "mode" in metadata
                assert "format" in metadata
            finally:
                os.unlink(tmp.name)

    def test_load_image_from_path_rgba(self):
        """Test loading an RGBA image from file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            # Create a test image with alpha
            img = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
            img.save(tmp.name)

            try:
                tensor, metadata = load_image_from_path(tmp.name)

                # Check tensor
                assert isinstance(tensor, torch.Tensor)
                assert tensor.shape == (1, 50, 50, 4)  # RGBA has 4 channels
                assert tensor.min() >= 0.0
                assert tensor.max() <= 1.0

                # Check metadata
                assert metadata["width"] == 50
                assert metadata["height"] == 50
            finally:
                os.unlink(tmp.name)

    def test_load_image_from_path_with_metadata(self):
        """Test loading an image with embedded metadata."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            # Create image with metadata
            img = Image.new("RGB", (100, 100), color="blue")

            # Add some metadata
            metadata_to_save = {
                "parameters": "test parameters",
                "prompt": json.dumps({"text": "test prompt"}),
                "workflow": json.dumps({"nodes": []}),
            }

            pnginfo = PngImagePlugin.PngInfo()
            for key, value in metadata_to_save.items():
                pnginfo.add_text(key, value)

            img.save(tmp.name, pnginfo=pnginfo)

            try:
                tensor, metadata = load_image_from_path(tmp.name)

                # Check embedded metadata
                assert metadata.get("parameters") == "test parameters"
                assert metadata.get("prompt") == {"text": "test prompt"}
                assert metadata.get("workflow") == {"nodes": []}
            finally:
                os.unlink(tmp.name)

    def test_load_image_from_nonexistent_path(self):
        """Test loading image from nonexistent path raises error."""
        with pytest.raises(FileNotFoundError):
            load_image_from_path("/nonexistent/path/image.png")

    def test_scan_directory_images_only(self):
        """Test scanning directory for images only."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "image1.jpg").touch()
            Path(tmpdir, "image2.png").touch()
            Path(tmpdir, "video.mp4").touch()
            Path(tmpdir, "audio.mp3").touch()
            Path(tmpdir, "document.txt").touch()
            Path(tmpdir, "subdir").mkdir()

            items = scan_directory(tmpdir, show_videos=False, show_audio=False)

            # Should have 1 directory and 2 images
            assert len(items) == 3

            # Check types
            types = [item["type"] for item in items]
            assert "dir" in types
            assert types.count("image") == 2

    def test_scan_directory_with_videos_audio(self):
        """Test scanning directory with videos and audio enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "image.jpg").touch()
            Path(tmpdir, "video.mp4").touch()
            Path(tmpdir, "audio.mp3").touch()

            items = scan_directory(tmpdir, show_videos=True, show_audio=True)

            assert len(items) == 3
            types = [item["type"] for item in items]
            assert "image" in types
            assert "video" in types
            assert "audio" in types

    def test_scan_directory_sorting(self):
        """Test directory scanning with different sort options."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with different names
            Path(tmpdir, "zebra.jpg").touch()
            Path(tmpdir, "apple.jpg").touch()
            Path(tmpdir, "banana.jpg").touch()

            # Sort by name ascending
            items = scan_directory(tmpdir, sort_by="name", sort_order="asc")
            names = [item["name"] for item in items if item["type"] == "image"]
            assert names == ["apple.jpg", "banana.jpg", "zebra.jpg"]

            # Sort by name descending
            items = scan_directory(tmpdir, sort_by="name", sort_order="desc")
            names = [item["name"] for item in items if item["type"] == "image"]
            assert names == ["zebra.jpg", "banana.jpg", "apple.jpg"]

    def test_scan_nonexistent_directory(self):
        """Test scanning nonexistent directory raises error."""
        with pytest.raises(NotADirectoryError):
            scan_directory("/nonexistent/directory")


class TestLocalImageLoaderNode:
    """Test the Local Image Loader node."""

    def test_input_types(self):
        """Test node input types definition."""
        input_types = LocalImageLoaderNode.INPUT_TYPES()

        assert "required" in input_types
        assert "hidden" in input_types
        assert "unique_id" in input_types["hidden"]

    def test_node_properties(self):
        """Test node properties."""
        assert LocalImageLoaderNode.RETURN_TYPES == (
            "IMAGE",
            "STRING",
            "STRING",
            "STRING",
        )
        assert LocalImageLoaderNode.RETURN_NAMES == (
            "image",
            "video_path",
            "audio_path",
            "info",
        )
        assert LocalImageLoaderNode.FUNCTION == "load_media"
        assert LocalImageLoaderNode.CATEGORY == "🫶 ComfyAssets/💾 Images"

    @patch("kikotools.tools.local_image_loader.node.load_selections")
    def test_load_media_no_selection(self, mock_load_selections):
        """Test loading media with no selection returns empty values."""
        mock_load_selections.return_value = {}

        node = LocalImageLoaderNode()
        image, video_path, audio_path, info = node.load_media("test_id")

        # Check empty returns
        assert isinstance(image, torch.Tensor)
        assert image.shape == (1, 1, 1, 4)
        assert torch.all(image == 0)
        assert video_path == ""
        assert audio_path == ""
        assert info == ""

    @patch("kikotools.tools.local_image_loader.node.load_selections")
    @patch("kikotools.tools.local_image_loader.node.load_image_from_path")
    def test_load_media_with_image_selection(
        self, mock_load_image, mock_load_selections
    ):
        """Test loading media with image selection."""
        # Setup mocks
        mock_load_selections.return_value = {
            "test_id": {"image": {"path": "/path/to/image.jpg"}}
        }

        test_tensor = torch.ones(1, 100, 100, 3)
        test_metadata = {"width": 100, "height": 100, "filename": "image.jpg"}
        mock_load_image.return_value = (test_tensor, test_metadata)

        # Mock os.path.exists
        with patch("os.path.exists", return_value=True):
            node = LocalImageLoaderNode()
            image, video_path, audio_path, info = node.load_media("test_id")

        # Check returns
        assert torch.equal(image, test_tensor)
        assert video_path == ""
        assert audio_path == ""
        assert json.loads(info) == test_metadata

    @patch("kikotools.tools.local_image_loader.node.load_selections")
    def test_load_media_with_video_audio_selection(self, mock_load_selections):
        """Test loading media with video and audio selection."""
        mock_load_selections.return_value = {
            "test_id": {
                "video": {"path": "/path/to/video.mp4"},
                "audio": {"path": "/path/to/audio.mp3"},
            }
        }

        with patch("os.path.exists", return_value=True):
            node = LocalImageLoaderNode()
            image, video_path, audio_path, info = node.load_media("test_id")

        # Check returns
        assert isinstance(image, torch.Tensor)
        assert image.shape == (1, 1, 1, 4)  # Empty tensor
        assert video_path == "/path/to/video.mp4"
        assert audio_path == "/path/to/audio.mp3"
        assert info == ""

    def test_is_changed(self):
        """Test IS_CHANGED method."""
        with patch("os.path.exists", return_value=False):
            result = LocalImageLoaderNode.IS_CHANGED()
            assert result == float("inf")

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getmtime", return_value=12345.0),
        ):
            result = LocalImageLoaderNode.IS_CHANGED()
            assert result == 12345.0
