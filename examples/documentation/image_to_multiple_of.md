# Image to Multiple Of

## Overview

The **Image to Multiple Of** node adjusts image dimensions to be multiples of a specified value. This is particularly useful for models that require input dimensions to be multiples of certain values (e.g., 8, 16, 32, 64) for optimal performance or compatibility.

## Purpose

Many AI models, especially diffusion models and VAEs, require input dimensions to be multiples of specific values due to their architecture (e.g., downsampling layers). This node ensures your images meet these requirements without manual calculation.

## Inputs

- **image** (IMAGE, required): The input image to process
- **multiple_of** (INT, required): The value that dimensions should be multiple of
  - Default: 64
  - Range: 1-256
  - Step: 16
- **method** (COMBO, required): Processing method
  - Options: "center crop", "rescale"

## Outputs

- **image** (IMAGE): Processed image with dimensions adjusted to multiples of the specified value

## Processing Methods

### Center Crop
- Crops the image from the center to achieve the target dimensions
- Preserves image quality but may lose edge content
- Best for images where the important content is centered

### Rescale
- Resizes the image to the target dimensions using bilinear interpolation
- Keeps all content but may slightly affect image quality
- Best when you need to preserve all image content

## Usage Examples

### Example 1: Prepare for VAE Encoding
```
Load Image → Image to Multiple Of (multiple_of: 64) → VAE Encode
```

### Example 2: Prepare for Specific Model Requirements
```
Load Image → Image to Multiple Of (multiple_of: 32) → Model Processing
```

### Example 3: Batch Processing
```
Load Images → Image to Multiple Of (multiple_of: 16, method: rescale) → Batch Process
```

## Technical Details

- Supports batch processing (processes all images in a batch)
- Works with any number of channels (RGB, RGBA, grayscale, etc.)
- Calculates the largest dimensions that are less than or equal to the original size
- For center crop: crops equally from all sides to maintain centering
- For rescale: uses bilinear interpolation with align_corners=False

## Common Use Cases

1. **VAE Preprocessing**: Ensure images are compatible with VAE encoders that require dimensions divisible by 64
2. **Model Compatibility**: Adjust images for models with specific architectural requirements
3. **Batch Uniformity**: Ensure all images in a batch have dimensions that meet model requirements
4. **Performance Optimization**: Some models perform better with dimensions that are powers of 2

## Tips

- Use **center crop** when your subject is centered and you don't mind losing edge details
- Use **rescale** when you need to preserve all image content
- Common multiple_of values: 8, 16, 32, 64, 128
- For Stable Diffusion models, 64 is typically recommended
- For some upscaling models, 32 or 16 may be sufficient

## Error Handling

The node will raise an error if:
- The image dimensions are smaller than the specified multiple_of value
- Invalid input types are provided
- The resulting dimensions would be 0 or negative
