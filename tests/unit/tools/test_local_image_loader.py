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
            tmp.close()  # Windows can't reopen/delete an open file
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
            tmp.close()  # Windows can't reopen/delete an open file
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
            tmp.close()  # Windows can't reopen/delete an open file
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
            "H3_REF_LIST",
            "IMAGE",
        )
        assert LocalImageLoaderNode.RETURN_NAMES == (
            "image",
            "info",
            "folder",
            "refs",
            "refs_preview",
        )
        assert len(LocalImageLoaderNode.OUTPUT_TOOLTIPS) == 5
        assert LocalImageLoaderNode.FUNCTION == "load_media"
        assert LocalImageLoaderNode.CATEGORY == "🫶 ComfyAssets/💾 Images"

    @patch("kikotools.tools.local_image_loader.node.load_selections")
    def test_load_media_no_selection(self, mock_load_selections):
        """Test loading media with no selection returns empty values."""
        mock_load_selections.return_value = {}

        node = LocalImageLoaderNode()
        image, info, folder, *_ = node.load_media("test_id")

        # Check empty returns
        assert isinstance(image, torch.Tensor)
        assert image.shape == (1, 1, 1, 4)
        assert torch.all(image == 0)
        assert info == ""
        assert folder == ""

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

        # Mock os.path.exists and the allowed roots
        with (
            patch("os.path.exists", return_value=True),
            patch(
                "kikotools.tools.local_image_loader.node.get_allowed_roots",
                return_value=["/path/to"],
            ),
        ):
            node = LocalImageLoaderNode()
            image, info, folder, *_ = node.load_media("test_id")

        # Check returns
        assert torch.equal(image, test_tensor)
        assert json.loads(info) == test_metadata
        assert folder == os.path.realpath("/path/to")

    @patch("kikotools.tools.local_image_loader.node.load_selections")
    def test_load_media_ignores_video_audio_selection(self, mock_load_selections):
        """Video/audio selections are not outputs of this node any more."""
        mock_load_selections.return_value = {
            "test_id": {
                "video": {"path": "/path/to/video.mp4"},
                "audio": {"path": "/path/to/audio.mp3"},
            }
        }

        image, info, folder, *_ = LocalImageLoaderNode().load_media("test_id")

        assert image.shape == (1, 1, 1, 4)
        assert info == ""
        assert folder == ""

    def test_load_media_outputs_browsed_folder(self, tmp_path):
        """The folder the gallery is showing is output even with no image picked."""
        (tmp_path / "dataset").mkdir()
        folder_path = str(tmp_path / "dataset")
        with (
            patch(
                "kikotools.tools.local_image_loader.node.load_selections",
                return_value={"test_id": {"folder": {"path": folder_path}}},
            ),
            patch(
                "kikotools.tools.local_image_loader.node.get_allowed_roots",
                return_value=[str(tmp_path)],
            ),
        ):
            image, info, folder, *_ = LocalImageLoaderNode().load_media("test_id")

        assert image.shape == (1, 1, 1, 4)
        assert folder == os.path.realpath(folder_path)

    def test_load_media_browsed_folder_wins_over_image_folder(self, tmp_path):
        """Browsing away after picking an image outputs the folder now shown."""
        for d in ("a", "b"):
            (tmp_path / d).mkdir()
        Image.new("RGB", (4, 4)).save(tmp_path / "a" / "x.png")
        selection = {
            "image": {"path": str(tmp_path / "a" / "x.png")},
            "folder": {"path": str(tmp_path / "b")},
        }
        with (
            patch(
                "kikotools.tools.local_image_loader.node.load_selections",
                return_value={"test_id": selection},
            ),
            patch(
                "kikotools.tools.local_image_loader.node.get_allowed_roots",
                return_value=[str(tmp_path)],
            ),
        ):
            _, _, folder, *_ = LocalImageLoaderNode().load_media("test_id")

        assert folder == os.path.realpath(tmp_path / "b")

    def test_load_media_refuses_folder_outside_roots(self, tmp_path):
        """A tampered selections.json cannot point the folder output elsewhere."""
        (tmp_path / "root").mkdir()
        (tmp_path / "elsewhere").mkdir()
        with (
            patch(
                "kikotools.tools.local_image_loader.node.load_selections",
                return_value={
                    "test_id": {"folder": {"path": str(tmp_path / "elsewhere")}}
                },
            ),
            patch(
                "kikotools.tools.local_image_loader.node.get_allowed_roots",
                return_value=[str(tmp_path / "root")],
            ),
        ):
            _, _, folder, *_ = LocalImageLoaderNode().load_media("test_id")

        assert folder == ""

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


class TestLoadMediaRefs:
    def _run(self, tmp_path, refs):
        with (
            patch(
                "kikotools.tools.local_image_loader.node.load_selections",
                return_value={"n": {"refs": {"paths": refs}}},
            ),
            patch(
                "kikotools.tools.local_image_loader.node.get_allowed_roots",
                return_value=[str(tmp_path / "root")],
            ),
        ):
            return LocalImageLoaderNode().load_media("n")

    def _root(self, tmp_path):
        (tmp_path / "root").mkdir()
        return tmp_path / "root"

    def test_no_refs_gives_empty_list_and_tensor(self, tmp_path):
        self._root(tmp_path)
        _, _, _, refs, preview = self._run(tmp_path, [])
        assert refs == []
        assert preview.shape == (1, 1, 1, 4)

    def test_refs_in_order_matched_to_first(self, tmp_path):
        root = self._root(tmp_path)
        Image.new("RGB", (64, 32), "red").save(root / "a.png")
        Image.new("RGB", (20, 40), "blue").save(root / "b.png")
        image, _, _, refs, preview = self._run(
            tmp_path, [str(root / "a.png"), str(root / "b.png")]
        )
        assert [r.shape for r in refs] == [(1, 32, 64, 3)] * 2
        assert preview.shape == (2, 32, 64, 3)
        assert refs[0][0, 0, 0, 0] > 0.9
        assert refs[1][0, 0, 0, 2] > 0.9
        assert image.shape == (1, 1, 1, 4)

    def test_missing_and_disallowed_skipped_keeping_order(self, tmp_path, caplog):
        root = self._root(tmp_path)
        Image.new("RGB", (8, 8), "red").save(root / "a.png")
        Image.new("RGB", (8, 8), "blue").save(root / "c.png")
        (tmp_path / "other.png").write_bytes(b"x")
        Image.new("RGB", (8, 8)).save(tmp_path / "out.png")
        with caplog.at_level("WARNING"):
            _, _, _, refs, preview = self._run(
                tmp_path,
                [
                    str(root / "a.png"),
                    str(root / "gone.png"),
                    str(tmp_path / "out.png"),
                    str(root / "c.png"),
                ],
            )
        assert len(refs) == 2 and preview.shape[0] == 2
        assert refs[1][0, 0, 0, 2] > 0.9
        assert "gone.png" in caplog.text and "out.png" in caplog.text

    def test_corrupt_file_skipped(self, tmp_path):
        root = self._root(tmp_path)
        (root / "bad.png").write_bytes(b"not an image")
        Image.new("RGB", (8, 8)).save(root / "ok.png")
        _, _, _, refs, _ = self._run(
            tmp_path, [str(root / "bad.png"), str(root / "ok.png")]
        )
        assert len(refs) == 1

    def test_all_unusable_gives_empty(self, tmp_path):
        root = self._root(tmp_path)
        _, _, _, refs, preview = self._run(tmp_path, [str(root / "gone.png")])
        assert refs == [] and preview.shape == (1, 1, 1, 4)
