# Width Height Selector Documentation

## Overview

The Width Height Selector is a ComfyUI node that provides preset-based dimension selection with swap functionality, optimized for SDXL and FLUX models. It offers 26 carefully curated resolution presets plus custom dimension support.

## Features

### 🎯 **Preset Categories**
- **SDXL Presets** (9): ~1MP optimized resolutions
- **FLUX Presets** (8): Higher resolution options
- **Ultra-Wide Presets** (8): Modern aspect ratios
- **Custom**: Manual dimension input

### 🔄 **Smart Swap Logic**
- Visual swap button in bottom-right corner
- Intelligent orientation switching for presets
- Simple value swap for custom dimensions
- Maintains proper aspect ratios

### 🎨 **Enhanced UI**
- Modern blue swap button with hover effects
- Hidden swap parameter (controlled by button)
- Clean interface with visual feedback

### ✅ **Built-in Validation**
- Ensures divisible-by-8 constraint
- Auto-sanitization of invalid inputs
- Proper error handling and fallbacks

## Node Interface

### Inputs
- **preset**: Dropdown with 26 preset options + custom
- **width**: Custom width (64-8192, step 8)
- **height**: Custom height (64-8192, step 8)

### Outputs
- **width**: Integer width value
- **height**: Integer height value

## Preset Reference

### SDXL Presets (~1 Megapixel)
| Preset | Dimensions | Aspect Ratio | Use Case |
|--------|------------|--------------|----------|
| 1024×1024 | 1024×1024 | 1:1 | Square, base SDXL |
| 896×1152 | 896×1152 | 7:9 | Moderate portrait |
| 832×1216 | 832×1216 | 13:19 | Standard portrait |
| 768×1344 | 768×1344 | 4:7 | Tall portrait |
| 640×1536 | 640×1536 | 5:12 | Very tall portrait |
| 1152×896 | 1152×896 | 9:7 | Moderate landscape |
| 1216×832 | 1216×832 | 19:13 | Standard landscape |
| 1344×768 | 1344×768 | 7:4 | Wide landscape |
| 1536×640 | 1536×640 | 12:5 | Very wide landscape |

### FLUX Presets (High Resolution)
| Preset | Dimensions | Aspect Ratio | Use Case |
|--------|------------|--------------|----------|
| 1920×1080 | 1920×1080 | 16:9 | Full HD, best quality/speed |
| 1536×1536 | 1536×1536 | 1:1 | High-res square |
| 1280×768 | 1280×768 | 5:3 | Cinematic wide |
| 768×1280 | 768×1280 | 3:5 | Mobile optimized |
| 1440×1080 | 1440×1080 | 4:3 | Classic aspect ratio |
| 1080×1440 | 1080×1440 | 3:4 | Classic portrait |
| 1728×1152 | 1728×1152 | 3:2 | Photography standard |
| 1152×1728 | 1152×1728 | 2:3 | Portrait photography |

### Ultra-Wide Presets (Modern Ratios)
| Preset | Dimensions | Aspect Ratio | Use Case |
|--------|------------|--------------|----------|
| 2560×1080 | 2560×1080 | 64:27 | Ultra-wide gaming |
| 2048×768 | 2048×768 | 8:3 | Wide cinematic |
| 1792×768 | 1792×768 | 7:3 | Panoramic |
| 2304×768 | 2304×768 | 3:1 | Banner landscape |
| 1080×2560 | 1080×2560 | 27:64 | Mobile ultra-tall |
| 768×2048 | 768×2048 | 3:8 | Vertical cinematic |
| 768×1792 | 768×1792 | 3:7 | Vertical panoramic |
| 768×2304 | 768×2304 | 1:3 | Banner portrait |

## Usage Examples

### Basic Usage
1. **Select Preset**: Choose from dropdown (e.g., "1920×1080")
2. **Connect Outputs**: Link width/height to your target nodes
3. **Use Swap Button**: Click blue button in bottom-right corner to swap orientation

### Custom Dimensions
1. **Set Preset**: Select "custom"
2. **Enter Dimensions**: Input width and height manually
3. **Validation**: Automatic sanitization to divisible-by-8

### Orientation Swapping
1. **Choose Preset**: Any preset (e.g., "1920×1080")
2. **Click Swap Button**: Blue button in bottom-right corner of node
3. **Result**: Gets 1080×1920 (landscape → portrait) or switches to equivalent preset if available

### Integration with Resolution Calculator
```
Width Height Selector → EmptyLatentImage → Resolution Calculator
```
1. Set base dimensions with Width Height Selector
2. Create latent image with those dimensions
3. Calculate upscaled dimensions with Resolution Calculator

## Common Workflows

### SDXL Portrait Generation
```
Width Height Selector (832×1216) → EmptyLatentImage → SDXL Pipeline
```
- Perfect for portrait generation
- Optimized ~1MP resolution
- 13:19 aspect ratio

### FLUX HD Generation
```
Width Height Selector (1920×1080) → EmptyLatentImage → FLUX Pipeline
```
- Best quality/speed balance
- Full HD resolution
- 16:9 cinematic aspect ratio

### Ultra-Wide Panoramic
```
Width Height Selector (2560×1080) → EmptyLatentImage → Pipeline
```
- Modern ultra-wide format
- Great for panoramic scenes
- 64:27 gaming aspect ratio

### Upscaling Workflow
```
Width Height Selector → EmptyLatentImage → Resolution Calculator → Upscaler
```
1. Base dimensions from selector
2. Generate at base resolution
3. Calculate upscale dimensions
4. Feed to upscaler node

## Tips and Best Practices

### Model Optimization
- **SDXL**: Use SDXL presets for best results (~1MP)
- **FLUX**: Use FLUX presets for optimal quality/speed
- **Custom**: Ensure divisible by 8 for all models

### Aspect Ratio Considerations
- **Portrait**: 3:4, 2:3, 13:19 work well for people
- **Landscape**: 16:9, 19:13, 7:4 for scenes and objects  
- **Square**: 1:1 for centered compositions
- **Ultra-wide**: 21:9+ for panoramic and cinematic shots

### Memory Management
- Higher resolutions use more VRAM
- SDXL presets are memory-efficient
- FLUX presets require more resources
- Ultra-wide presets need substantial VRAM

### Workflow Integration
- Always connect width/height outputs
- Use swap button for quick orientation changes
- Combine with Resolution Calculator for upscaling
- Link to EmptyLatentImage for generation

## Troubleshooting

### Common Issues
- **Invalid dimensions**: Auto-sanitized to nearest valid values
- **Memory errors**: Use lower resolution presets
- **Orientation wrong**: Use the blue swap button instead of manual input
- **Swap button not visible**: Ensure node is not collapsed

### Error Handling
- Invalid presets fall back to custom dimensions
- Out-of-range values are clamped and rounded
- Division-by-8 constraint automatically enforced

## Technical Details

### Validation Rules
- Width/Height: 64-8192 pixels
- Must be divisible by 8
- Positive integers only

### Swap Button Implementation
- JavaScript-based visual interface
- Intelligent preset switching when possible
- Falls back to custom dimensions when needed
- Modern blue styling with hover effects

### Preset Organization
- Categorized by model optimization
- Sorted by aspect ratio within categories
- Comprehensive tooltips for each preset