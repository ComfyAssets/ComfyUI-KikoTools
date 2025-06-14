# Resolution Calculator Tool

## Overview
The Resolution Calculator is a ComfyUI node that calculates upscaled dimensions from image or latent inputs with proper scaling factors optimized for SDXL and FLUX models.

## Inputs

### Required
- **scale_factor** (FLOAT): Scaling factor from 1.0 to 8.0
  - Default: 2.0
  - Common values: 1.2, 1.5, 2.0, 2.5, 3.0, 4.0
  - Optimized for typical upscaling workflows

### Optional (one required)
- **image** (IMAGE): Input image tensor to calculate dimensions from
- **latent** (LATENT): Input latent tensor to calculate dimensions from

## Outputs
- **width** (INT): Calculated target width
- **height** (INT): Calculated target height

## Features

### Model Optimization
- **SDXL**: Optimized for ~1 megapixel base resolution (1024×1024)
- **FLUX**: Supports flexible resolutions from 0.2-2 megapixels

### Automatic Constraints
- Ensures all outputs are divisible by 8 (ComfyUI requirement)
- Preserves aspect ratio during scaling
- Rounds to nearest valid dimensions

## Use Cases

### 1. Upscaler Preparation
Connect the width/height outputs to upscaler nodes to ensure proper target dimensions.

```
Image Loader → Resolution Calculator → Upscaler
             ↘ scale_factor: 2.0    ↗
```

### 2. Latent Upscaling
Calculate target dimensions from generated latents before upscaling.

```
VAE Encode → Resolution Calculator → Latent Upscaler
           ↘ scale_factor: 1.5    ↗
```

### 3. Memory Planning
Preview final dimensions to estimate memory usage before expensive operations.

## Example Scenarios

### SDXL Portrait Upscaling
- **Input**: 832×1216 (SDXL portrait format)
- **Scale**: 1.5x
- **Output**: 1248×1824
- **Use**: Perfect for 1.5x upscaling while maintaining SDXL ratios

### FLUX Square Generation
- **Input**: 1024×1024 (FLUX square format)
- **Scale**: 2.0x
- **Output**: 2048×2048
- **Use**: Standard 2x upscaling for square outputs

### Variable Scale Factors
The node supports any scale factor from 1.0 to 8.0, allowing for:
- **1.2x**: Subtle enhancement
- **1.5x**: Moderate upscaling
- **2.0x**: Standard doubling
- **4.0x**: Aggressive upscaling

## Technical Details

### Dimension Extraction
- **IMAGE tensors**: `[batch, height, width, channels]` format
- **LATENT tensors**: `{"samples": [batch, channels, height/8, width/8]}` format
- Automatic detection and conversion between formats

### Calculation Process
1. Extract original dimensions from input tensor
2. Apply scale factor: `new_size = original_size * scale_factor`
3. Round to nearest multiple of 8: `((size + 4) // 8) * 8`
4. Return integer width and height

### Error Handling
- Validates that at least one input (image or latent) is provided
- Ensures scale factor is within valid range (1.0-8.0)
- Graceful error messages for invalid inputs

## Category
All Resolution Calculator nodes appear under **ComfyAssets** in the ComfyUI node browser.

## Integration
The Resolution Calculator integrates seamlessly with:
- Standard ComfyUI image loaders
- VAE encode/decode operations
- Upscaler nodes (ESRGAN, Real-ESRGAN, etc.)
- Custom latent processing workflows