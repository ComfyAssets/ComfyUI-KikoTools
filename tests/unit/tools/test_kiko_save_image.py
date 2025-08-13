"""
Unit tests for KikoSaveImage tool
Tests image saving functionality with multiple formats and quality settings
"""

import pytest
import torch
import tempfile
import os
from PIL import Image
from unittest.mock import patch

from kikotools.tools.kiko_save_image.node import KikoSaveImageNode
from kikotools.tools.kiko_save_image.logic import (
    convert_tensor_to_pil,
    process_image_batch,
    validate_save_inputs,
    save_image_with_format,
    get_save_image_path,
    create_png_metadata,
)


class TestKikoSaveImageLogic:
    """Test core logic functions"""

    def test_convert_tensor_to_pil(self):
        """Test tensor to PIL conversion"""
        # Create test tensor [height, width, channels] with values 0-1
        tensor = torch.rand(64, 64, 3)

        # Convert to PIL
        pil_image = convert_tensor_to_pil(tensor)

        # Verify conversion
        assert isinstance(pil_image, Image.Image)
        assert pil_image.size == (64, 64)  # PIL uses (width, height)
        assert pil_image.mode in ["RGB", "RGBA"]

    def test_convert_tensor_to_pil_rgba(self):
        """Test tensor to PIL conversion with alpha channel"""
        # Create RGBA tensor
        tensor = torch.rand(32, 32, 4)

        pil_image = convert_tensor_to_pil(tensor)

        assert isinstance(pil_image, Image.Image)
        assert pil_image.size == (32, 32)
        assert pil_image.mode == "RGBA"

    def test_get_save_image_path(self):
        """Test save path generation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test basic path generation
            full_path, filename, subfolder = get_save_image_path(
                "test_prefix", 0, ".png", temp_dir
            )

            assert full_path.startswith(temp_dir)
            assert filename.startswith("test_prefix_")
            assert filename.endswith("_00000.png")

            # Test with empty subfolder (standard behavior)
            full_path, filename, subfolder = get_save_image_path(
                "test", 1, ".jpg", temp_dir, ""
            )

            assert full_path.startswith(temp_dir)
            assert filename.startswith("test_")
            assert filename.endswith("_00001.jpg")

    def test_create_png_metadata(self):
        """Test PNG metadata creation"""
        # Test with no metadata
        metadata = create_png_metadata()
        assert metadata is None

        # Test with prompt data
        prompt_data = {"test": "value"}
        metadata = create_png_metadata(prompt=prompt_data)

        assert metadata is not None
        # Check that metadata is a PngInfo object
        from PIL.PngImagePlugin import PngInfo

        assert isinstance(metadata, PngInfo)

    @patch("kikotools.tools.kiko_save_image.logic.folder_paths")
    def test_process_image_batch_png(self, mock_folder_paths):
        """Test batch processing with PNG format"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_folder_paths.get_output_directory.return_value = temp_dir

            # Create test image batch [batch, height, width, channels]
            images = torch.rand(2, 32, 32, 3)

            # Process batch
            results, enhanced_data = process_image_batch(
                images=images,
                filename_prefix="test_batch",
                format_type="PNG",
                png_compress_level=6,
            )

            # Verify results (clean data)
            assert len(results) == 2
            for i, result in enumerate(results):
                assert "filename" in result
                assert "subfolder" in result
                assert "type" in result
                assert result["type"] == "output"

            # Verify enhanced data
            assert len(enhanced_data) == 2
            for i, enhanced in enumerate(enhanced_data):
                assert enhanced["format"] == "PNG"
                assert enhanced["compress_level"] == 6
                assert enhanced["dimensions"] == "32x32"
                assert enhanced["popup"] is True  # Default popup value
                assert "file_size" in enhanced

                # Verify file was saved
                filepath = os.path.join(temp_dir, enhanced["filename"])
                assert os.path.exists(filepath)

                # Verify image can be loaded
                saved_img = Image.open(filepath)
                assert saved_img.size == (32, 32)

    @patch("kikotools.tools.kiko_save_image.logic.folder_paths")
    def test_process_image_batch_jpeg(self, mock_folder_paths):
        """Test batch processing with JPEG format"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_folder_paths.get_output_directory.return_value = temp_dir

            # Create test image batch
            images = torch.rand(1, 64, 64, 3)

            # Process batch
            results, enhanced_data = process_image_batch(
                images=images,
                filename_prefix="test_jpeg",
                format_type="JPEG",
                quality=85,
            )

            # Verify results
            assert len(results) == 1
            assert len(enhanced_data) == 1
            enhanced = enhanced_data[0]
            assert enhanced["format"] == "JPEG"
            assert enhanced["quality"] == 85
            assert enhanced["filename"].endswith(".jpg")

            # Verify file exists and can be loaded
            filepath = os.path.join(temp_dir, results[0]["filename"])
            assert os.path.exists(filepath)

            saved_img = Image.open(filepath)
            assert saved_img.size == (64, 64)
            assert saved_img.mode == "RGB"  # JPEG converts to RGB

    @patch("kikotools.tools.kiko_save_image.logic.folder_paths")
    def test_process_image_batch_webp(self, mock_folder_paths):
        """Test batch processing with WebP format"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_folder_paths.get_output_directory.return_value = temp_dir

            # Create test image batch
            images = torch.rand(1, 48, 48, 3)

            # Test lossless WebP
            results, enhanced_data = process_image_batch(
                images=images,
                filename_prefix="test_webp",
                format_type="WEBP",
                quality=90,
                webp_lossless=True,
            )

            assert len(results) == 1
            assert len(enhanced_data) == 1
            assert enhanced_data[0]["format"] == "WEBP"
            assert enhanced_data[0]["lossless"] is True
            assert results[0]["filename"].endswith(".webp")

    def test_validate_save_inputs_valid(self):
        """Test input validation with valid inputs"""
        images = torch.rand(2, 64, 64, 3)

        # Should not raise exception
        validate_save_inputs(images, "PNG", 90, 4)
        validate_save_inputs(images, "JPEG", 85, 4)
        validate_save_inputs(images, "WEBP", 95, 6)

    def test_validate_save_inputs_invalid_tensor(self):
        """Test validation with invalid tensor"""
        # Wrong tensor dimensions
        invalid_tensor = torch.rand(64, 64)  # Missing batch and channel dims

        with pytest.raises(ValueError, match="4 dimensions"):
            validate_save_inputs(invalid_tensor, "PNG", 90, 4)

        # Non-tensor input
        with pytest.raises(ValueError, match="torch.Tensor"):
            validate_save_inputs("not_a_tensor", "PNG", 90, 4)

    def test_validate_save_inputs_invalid_format(self):
        """Test validation with invalid format"""
        images = torch.rand(1, 32, 32, 3)

        with pytest.raises(ValueError, match="format must be one of"):
            validate_save_inputs(images, "BMP", 90, 4)

    def test_validate_save_inputs_invalid_quality(self):
        """Test validation with invalid quality"""
        images = torch.rand(1, 32, 32, 3)

        # Quality out of range
        with pytest.raises(
            ValueError, match="quality must be an integer between 1 and 100"
        ):
            validate_save_inputs(images, "JPEG", 0, 4)

        with pytest.raises(
            ValueError, match="quality must be an integer between 1 and 100"
        ):
            validate_save_inputs(images, "JPEG", 101, 4)

    def test_validate_save_inputs_invalid_compress_level(self):
        """Test validation with invalid PNG compression level"""
        images = torch.rand(1, 32, 32, 3)

        with pytest.raises(
            ValueError, match="png_compress_level must be an integer between 0 and 9"
        ):
            validate_save_inputs(images, "PNG", 90, -1)

        with pytest.raises(
            ValueError, match="png_compress_level must be an integer between 0 and 9"
        ):
            validate_save_inputs(images, "PNG", 90, 10)

    def test_save_image_with_format_png(self):
        """Test saving with PNG format"""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Create test PIL image
            img = Image.new("RGB", (32, 32), color="red")

            # Save with PNG format
            result = save_image_with_format(img, temp_path, "PNG", png_compress_level=8)

            assert result["format"] == "PNG"
            assert result["compress_level"] == 8
            assert os.path.exists(temp_path)

            # Verify saved image
            saved_img = Image.open(temp_path)
            assert saved_img.size == (32, 32)

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_save_image_with_format_jpeg_rgba_conversion(self):
        """Test JPEG saving with RGBA to RGB conversion"""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Create RGBA image
            img = Image.new("RGBA", (32, 32), color=(255, 0, 0, 128))

            # Save as JPEG (should convert to RGB)
            result = save_image_with_format(img, temp_path, "JPEG", quality=95)

            assert result["format"] == "JPEG"
            assert result["quality"] == 95

            # Verify saved image is RGB
            saved_img = Image.open(temp_path)
            assert saved_img.mode == "RGB"

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestKikoSaveImageNode:
    """Test KikoSaveImageNode class"""

    def setup_method(self):
        """Setup test fixtures"""
        self.node = KikoSaveImageNode()

    def test_input_types(self):
        """Test INPUT_TYPES class method"""
        input_types = KikoSaveImageNode.INPUT_TYPES()

        # Check required inputs
        required = input_types["required"]
        assert "images" in required
        assert "filename_prefix" in required
        assert "format" in required

        # Check format options
        format_options = required["format"][0]
        assert "PNG" in format_options
        assert "JPEG" in format_options
        assert "WEBP" in format_options

        # Check optional inputs
        optional = input_types["optional"]
        assert "quality" in optional
        assert "png_compress_level" in optional
        assert "webp_lossless" in optional
        assert "popup" in optional

        # Check hidden inputs
        hidden = input_types["hidden"]
        assert "prompt" in hidden
        assert "extra_pnginfo" in hidden

    def test_node_attributes(self):
        """Test node class attributes"""
        assert KikoSaveImageNode.RETURN_TYPES == ()
        assert KikoSaveImageNode.FUNCTION == "save_images"
        assert KikoSaveImageNode.OUTPUT_NODE is True
        assert KikoSaveImageNode.CATEGORY == "🫶 ComfyAssets/💾 Images"

    @patch("kikotools.tools.kiko_save_image.node.process_image_batch")
    def test_save_images_success(self, mock_process):
        """Test successful image saving"""
        # Setup mock - new return format (results, enhanced_data)
        mock_results = [
            {
                "filename": "test_00001_00000.png",
                "subfolder": "",
                "type": "output",
            }
        ]
        mock_enhanced = [
            {
                "filename": "test_00001_00000.png",
                "popup": True,
                "type": "output",
                "format": "PNG",
                "file_size": 1024,
                "dimensions": "64x64",
            }
        ]
        mock_process.return_value = (mock_results, mock_enhanced)

        # Create test input
        images = torch.rand(1, 64, 64, 3)

        # Call save_images
        result = self.node.save_images(
            images=images,
            filename_prefix="test",
            format="PNG",
            quality=90,
            png_compress_level=4,
        )

        # Verify mock was called
        mock_process.assert_called_once()

        # Verify result format
        assert "ui" in result
        assert "images" in result["ui"]
        assert "kiko_enhanced" in result["ui"]
        assert result["ui"]["images"] == mock_results
        assert result["ui"]["kiko_enhanced"] == mock_enhanced

    def test_validate_inputs_success(self):
        """Test input validation with valid inputs"""
        images = torch.rand(1, 32, 32, 3)

        # Should not raise exception
        self.node.validate_inputs(
            images=images,
            format="PNG",
            quality=90,
            png_compress_level=4,
            webp_lossless=False,
            popup=True,
        )

    def test_validate_inputs_invalid_webp_lossless(self):
        """Test validation with invalid webp_lossless type"""
        images = torch.rand(1, 32, 32, 3)

        with pytest.raises(ValueError, match="webp_lossless must be a boolean"):
            self.node.validate_inputs(
                images=images,
                format="PNG",
                quality=90,
                png_compress_level=4,
                webp_lossless="not_boolean",
                popup=True,
            )

    def test_validate_inputs_invalid_popup(self):
        """Test validation with invalid popup"""
        images = torch.rand(1, 32, 32, 3)

        # Non-boolean popup
        with pytest.raises(ValueError, match="popup must be a boolean"):
            self.node.validate_inputs(
                images=images,
                format="PNG",
                quality=90,
                png_compress_level=4,
                webp_lossless=False,
                popup="not_boolean",
            )

    @patch("kikotools.tools.kiko_save_image.node.process_image_batch")
    def test_save_images_error_handling(self, mock_process):
        """Test error handling in save_images method"""
        # Setup mock to raise exception
        mock_process.side_effect = Exception("Test error")

        images = torch.rand(1, 32, 32, 3)

        # Should handle error and re-raise with context
        with pytest.raises(ValueError, match="Failed to save images"):
            self.node.save_images(images=images)

    def test_node_info(self):
        """Test get_node_info method"""
        info = self.node.get_node_info()

        assert info["class_name"] == "KikoSaveImageNode"
        assert info["category"] == "🫶 ComfyAssets/💾 Images"
        assert info["function"] == "save_images"


class TestNodeRegistration:
    """Test node registration mappings"""

    def test_node_class_mappings(self):
        """Test NODE_CLASS_MAPPINGS contains KikoSaveImage"""
        from kikotools.tools.kiko_save_image.node import NODE_CLASS_MAPPINGS

        assert "KikoSaveImage" in NODE_CLASS_MAPPINGS
        assert NODE_CLASS_MAPPINGS["KikoSaveImage"] is KikoSaveImageNode

    def test_node_display_name_mappings(self):
        """Test NODE_DISPLAY_NAME_MAPPINGS contains KikoSaveImage"""
        from kikotools.tools.kiko_save_image.node import NODE_DISPLAY_NAME_MAPPINGS

        assert "KikoSaveImage" in NODE_DISPLAY_NAME_MAPPINGS
        assert NODE_DISPLAY_NAME_MAPPINGS["KikoSaveImage"] == "Kiko Save Image"


# Integration test fixtures
@pytest.fixture
def sample_image_tensor():
    """Create sample image tensor for testing"""
    # Create a colorful test image [batch, height, width, channels]
    batch_size, height, width, channels = 2, 64, 64, 3

    # Create gradient pattern
    tensor = torch.zeros(batch_size, height, width, channels)
    for b in range(batch_size):
        for h in range(height):
            for w in range(width):
                # Create RGB gradient pattern
                tensor[b, h, w, 0] = h / height  # Red gradient
                tensor[b, h, w, 1] = w / width  # Green gradient
                tensor[b, h, w, 2] = (b + 1) * 0.5  # Blue varies by batch

    return tensor


class TestIntegration:
    """Integration tests using sample data"""

    @patch("kikotools.tools.kiko_save_image.logic.folder_paths")
    def test_full_pipeline_png(self, mock_folder_paths, sample_image_tensor):
        """Test complete pipeline with PNG format"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_folder_paths.get_output_directory.return_value = temp_dir

            node = KikoSaveImageNode()

            # Save images
            result = node.save_images(
                images=sample_image_tensor,
                filename_prefix="integration_test",
                format="PNG",
                png_compress_level=6,
            )

            # Verify result structure
            assert "ui" in result
            assert "images" in result["ui"]
            assert len(result["ui"]["images"]) == 2

            # Verify files were created
            for image_info in result["ui"]["images"]:
                filepath = os.path.join(temp_dir, image_info["filename"])
                assert os.path.exists(filepath)

                # Verify image properties
                img = Image.open(filepath)
                assert img.size == (64, 64)
                assert img.format == "PNG"

    @patch("kikotools.tools.kiko_save_image.logic.folder_paths")
    def test_full_pipeline_all_formats(self, mock_folder_paths, sample_image_tensor):
        """Test complete pipeline with all supported formats"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_folder_paths.get_output_directory.return_value = temp_dir

            node = KikoSaveImageNode()

            # Test each format
            formats_to_test = [
                ("PNG", {"png_compress_level": 8}),
                ("JPEG", {"quality": 85}),
                ("WEBP", {"quality": 90, "webp_lossless": False}),
                ("WEBP", {"quality": 100, "webp_lossless": True}),
            ]

            for format_type, kwargs in formats_to_test:
                result = node.save_images(
                    images=sample_image_tensor,
                    filename_prefix=f"test_{format_type.lower()}",
                    format=format_type,
                    **kwargs,
                )

                # Verify results
                assert len(result["ui"]["images"]) == 2

                # The results are the basic output - format is in enhanced data
                # Just check that files were created
                for image_info in result["ui"]["images"]:
                    assert "filename" in image_info

                    # Verify file exists and can be opened
                    filepath = os.path.join(temp_dir, image_info["filename"])
                    assert os.path.exists(filepath)

                    img = Image.open(filepath)
                    assert img.size == (64, 64)
