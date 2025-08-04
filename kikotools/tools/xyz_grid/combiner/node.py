"""Image Grid Combiner node implementation."""

from typing import Dict, List, Any, Tuple, Optional
import torch
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io

from ..utils.constants import GRID_DEFAULTS


class ImageGridCombiner:
    """Combines images into labeled grid output."""
    
    @classmethod  
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "grid_data": ("XYZ_GRID",),
            },
            "optional": {
                "font_size": ("INT", {"default": GRID_DEFAULTS["font_size"], "min": 8, "max": 72}),
                "grid_gap": ("INT", {"default": GRID_DEFAULTS["grid_gap"], "min": 0, "max": 50}),
                "label_height": ("INT", {"default": GRID_DEFAULTS["label_height"], "min": 0, "max": 100}),
                "max_label_length": ("INT", {"default": GRID_DEFAULTS["max_label_length"], "min": 10, "max": 100}),
                "include_labels": ("BOOLEAN", {"default": True}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("grid_image", "grid_info")
    FUNCTION = "combine_images"
    CATEGORY = "ComfyAssets/XYZ Grid"
    OUTPUT_NODE = True
    
    def __init__(self):
        self.image_buffer = {}  # Store images by batch_id
        self.grid_configs = {}  # Store configs by batch_id
        
    def combine_images(self, images, grid_data, font_size=20, grid_gap=10, 
                      label_height=30, max_label_length=30, include_labels=True):
        """Combine images into grid with labels."""
        
        batch_id = grid_data["batch_id"]
        
        # Initialize buffer for this batch if needed
        if batch_id not in self.image_buffer:
            self.image_buffer[batch_id] = []
            self.grid_configs[batch_id] = grid_data
        
        # Add current image(s) to buffer
        if len(images.shape) == 4:  # Batch of images
            for img in images:
                self.image_buffer[batch_id].append(img)
        else:  # Single image
            self.image_buffer[batch_id].append(images)
        
        # Check if we have all images for this grid
        config = self.grid_configs[batch_id]
        expected_images = config["dimensions"]["total_images"]
        current_count = len(self.image_buffer[batch_id])
        
        if current_count < expected_images:
            # Not ready yet, return placeholder
            placeholder = torch.zeros((1, 64, 64, 3))
            info = f"Grid progress: {current_count}/{expected_images} images"
            return (placeholder, info)
        
        # We have all images, create grid(s)
        grids = self._create_grids(batch_id, font_size, grid_gap, label_height, 
                                  max_label_length, include_labels)
        
        # Clean up buffers
        del self.image_buffer[batch_id]
        del self.grid_configs[batch_id]
        
        # Return grid(s) and info
        info = self._generate_grid_info(config)
        
        # Convert PIL images back to tensor format
        grid_tensors = []
        for grid in grids:
            grid_np = np.array(grid).astype(np.float32) / 255.0
            grid_tensor = torch.from_numpy(grid_np)
            grid_tensors.append(grid_tensor)
        
        # Stack if multiple grids (Z axis)
        if len(grid_tensors) > 1:
            output = torch.stack(grid_tensors)
        else:
            output = grid_tensors[0].unsqueeze(0)
        
        return (output, info)
    
    def _create_grids(self, batch_id: str, font_size: int, grid_gap: int,
                     label_height: int, max_label_length: int, include_labels: bool) -> List[Image.Image]:
        """Create grid images from buffer."""
        
        config = self.grid_configs[batch_id]
        images = self.image_buffer[batch_id]
        dims = config["dimensions"]
        
        # Convert tensors to PIL images
        pil_images = []
        for img_tensor in images:
            img_np = (img_tensor.cpu().numpy() * 255).astype(np.uint8)
            pil_images.append(Image.fromarray(img_np))
        
        # Get dimensions
        img_width = pil_images[0].width
        img_height = pil_images[0].height
        cols = dims["cols"]
        rows = dims["rows"]
        grids_count = dims["grids_count"]
        
        # Calculate grid dimensions
        if include_labels:
            grid_width = cols * img_width + (cols - 1) * grid_gap
            grid_height = rows * img_height + (rows - 1) * grid_gap + label_height
        else:
            grid_width = cols * img_width + (cols - 1) * grid_gap
            grid_height = rows * img_height + (rows - 1) * grid_gap
        
        grids = []
        
        # Create each grid (for Z axis)
        for z_idx in range(grids_count):
            # Create blank grid
            grid = Image.new('RGB', (grid_width, grid_height), color=(32, 32, 32))
            draw = ImageDraw.Draw(grid)
            
            # Add labels if enabled
            if include_labels:
                # Try to use a better font if available
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                
                # Draw column labels (X axis)
                x_labels = config["axes"]["x"]["labels"]
                for col_idx, label in enumerate(x_labels):
                    x = col_idx * (img_width + grid_gap)
                    self._draw_label(draw, label, x, 0, img_width, label_height, font, max_label_length)
            
            # Place images
            for y_idx in range(rows):
                for x_idx in range(cols):
                    img_idx = z_idx * (rows * cols) + y_idx * cols + x_idx
                    if img_idx < len(pil_images):
                        x = x_idx * (img_width + grid_gap)
                        y = y_idx * (img_height + grid_gap) + (label_height if include_labels else 0)
                        grid.paste(pil_images[img_idx], (x, y))
                        
                        # Add row label (Y axis) on first column
                        if include_labels and x_idx == 0:
                            y_labels = config["axes"]["y"]["labels"]
                            if y_idx < len(y_labels):
                                label_y = y + img_height // 2 - font_size // 2
                                self._draw_label(draw, y_labels[y_idx], x - 5, label_y, 
                                               img_width // 3, font_size, font, max_label_length, 
                                               align="right")
            
            grids.append(grid)
        
        return grids
    
    def _draw_label(self, draw, text: str, x: int, y: int, width: int, height: int,
                   font, max_length: int, align: str = "center"):
        """Draw a label with background."""
        
        # Truncate if needed
        if len(text) > max_length:
            text = text[:max_length-3] + "..."
        
        # Get text dimensions
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Calculate position based on alignment
        if align == "center":
            text_x = x + (width - text_width) // 2
        elif align == "right":
            text_x = x + width - text_width - 5
        else:
            text_x = x + 5
            
        text_y = y + (height - text_height) // 2
        
        # Draw background
        padding = 3
        draw.rectangle([text_x - padding, text_y - padding, 
                       text_x + text_width + padding, text_y + text_height + padding],
                      fill=(0, 0, 0, 180))
        
        # Draw text
        draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
    
    def _generate_grid_info(self, config: Dict) -> str:
        """Generate information string about the grid."""
        dims = config["dimensions"]
        axes = config["axes"]
        
        info_parts = [f"Grid: {dims['cols']}x{dims['rows']}"]
        
        for axis_name, axis_data in axes.items():
            if axis_data["type"] and axis_data["values"]:
                axis_type = axis_data["type"].value
                value_count = len(axis_data["values"])
                info_parts.append(f"{axis_name.upper()}: {axis_type} ({value_count} values)")
        
        info_parts.append(f"Total images: {dims['total_images']}")
        
        return " | ".join(info_parts)