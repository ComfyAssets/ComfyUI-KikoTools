# Kiko Film Grain

## Overview
The **Kiko Film Grain** node applies realistic film grain effects to images, simulating the aesthetic of analog film photography. It provides comprehensive controls for grain size, intensity, color saturation, and shadow lifting to achieve various film looks.

## Node Details
- **Category**: ComfyAssets/image
- **Node Name**: KikoFilmGrain
- **Display Name**: Kiko Film Grain

## Inputs

### Required
- **image** (`IMAGE`)
  - The input image to apply film grain to
  - Supports batch processing
  - Preserves alpha channel if present

### Parameters
- **scale** (`FLOAT`)
  - Controls the size of the grain pattern
  - Range: 0.25 to 2.0
  - Default: 0.5
  - Lower values = finer grain, higher values = coarser grain

- **strength** (`FLOAT`)
  - Intensity of the grain effect
  - Range: 0.0 to 10.0
  - Default: 0.5
  - 0.0 = no grain, higher values = more pronounced grain

- **saturation** (`FLOAT`)
  - Color saturation of the grain
  - Range: 0.0 to 2.0
  - Default: 0.7
  - 0.0 = monochrome grain, 1.0 = full color, >1.0 = oversaturated

- **toe** (`FLOAT`)
  - Lifts blacks/shadows for a film-like look
  - Range: -0.2 to 0.5
  - Default: 0.0
  - Positive values lift shadows, negative values crush blacks

- **seed** (`INT`)
  - Random seed for grain pattern generation
  - Range: 0 to maximum integer
  - Default: 0
  - Use for reproducible grain patterns

## Outputs
- **image** (`IMAGE`)
  - The processed image with film grain applied
  - Same dimensions and batch size as input
  - Alpha channel preserved if present

## Usage Examples

### Subtle Film Look
```
Scale: 0.5
Strength: 0.3
Saturation: 0.8
Toe: 0.05
```
Creates a subtle, fine-grained film aesthetic suitable for portraits.

### Vintage Film
```
Scale: 1.0
Strength: 0.8
Saturation: 0.5
Toe: 0.15
```
Simulates vintage film with moderate grain and lifted shadows.

### High ISO Film
```
Scale: 0.75
Strength: 1.5
Saturation: 0.6
Toe: 0.1
```
Emulates high ISO film stock with pronounced grain.

### Black & White Film
```
Scale: 0.6
Strength: 0.6
Saturation: 0.0
Toe: 0.08
```
Creates monochrome grain perfect for black and white photography.

## Technical Details

### Improvements Over Standard Implementations
1. **Pure PyTorch Operations**: No OpenCV dependencies, better GPU utilization
2. **ITU-R BT.709 Color Space**: Accurate color conversion for grain application
3. **Screen Blend Mode**: Preserves highlights better than multiply blending
4. **Channel-Specific Weighting**: Film grain is stronger in blue channel (3x), moderate in red (2x), matching real film characteristics
5. **Efficient Memory Management**: Minimizes tensor copies and conversions

### Algorithm Overview
1. Generate random noise at specified scale
2. Convert to YCbCr color space for realistic grain distribution
3. Apply different blur kernels to each channel:
   - Y (luminance): 3x3 kernel for fine detail
   - Cb (blue-yellow): 15x15 kernel for color noise
   - Cr (red-green): 11x11 kernel for color noise
4. Convert back to RGB and apply strength/saturation
5. Use screen blend mode to combine with original image
6. Apply toe adjustment for film-like shadow response

## Tips
- Start with low strength values (0.2-0.5) and adjust upward
- For color images, saturation between 0.5-0.8 looks most natural
- Combine with color grading nodes for complete film emulation
- Use consistent seed values across batch for uniform grain
- Scale parameter affects both grain size and render performance (smaller scale = more computation)

## Compatibility
- Works with any image format supported by ComfyUI
- Preserves image properties (alpha channel, batch size)
- Compatible with both RGB and RGBA images
- Efficient batch processing support
