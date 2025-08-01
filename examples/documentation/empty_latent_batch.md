# Empty Latent Batch Documentation

## Overview

The Empty Latent Batch is a ComfyUI node that creates empty latent tensors with batch support and preset integration. It combines the preset functionality of Width Height Selector with efficient batch processing capabilities, making it ideal for batch workflows and optimized generation pipelines.

## Features

### 🎯 **Preset Integration**
- **26 Curated Presets**: Full access to SDXL, FLUX, and Ultra-wide presets
- **Formatted Display**: Shows aspect ratio, megapixels, and model group
- **Smart Fallback**: Automatic fallback to custom dimensions for invalid presets
- **Model Optimization**: Preset categories optimized for different model types

### 📦 **Batch Processing**
- **Configurable Batch Size**: Create 1-64 empty latents in single operation
- **Memory Efficient**: Uses torch.zeros for optimal memory allocation
- **Batch Validation**: Prevents excessive memory usage with warnings
- **ComfyUI Compatible**: Standard latent format for seamless integration

### 🔄 **Visual Swap Button**
- **Interactive UI**: Blue swap button with hover and click feedback
- **Preset-Aware Swapping**: Intelligent switching between matching presets
- **Custom Dimension Support**: Simple value swapping for custom inputs
- **Visual Feedback**: Button state changes during interaction

### ✅ **Smart Validation**
- **Dimension Sanitization**: Automatic adjustment to divisible-by-8 constraint
- **Memory Estimation**: Built-in memory usage calculation
- **Error Handling**: Graceful handling of invalid inputs with helpful messages
- **Logging**: Detailed operation logging for debugging

## Node Interface

### Inputs
- **preset**: Dropdown with 26 formatted preset options + custom
- **width**: Custom width (64-8192, step 8, default 1024)
- **height**: Custom height (64-8192, step 8, default 1024)
- **batch_size**: Number of latents to create (1-64, default 1)

### Outputs
- **latent**: Dictionary containing batch of empty latent tensors
- **width**: Final sanitized width (guaranteed divisible by 8)
- **height**: Final sanitized height (guaranteed divisible by 8)

## Preset Reference

The Empty Latent Batch node uses the same 26 curated presets as the Width Height Selector:

### SDXL Presets (~1 Megapixel)
Optimized for SDXL models with ~1MP resolution constraint.

### FLUX Presets (High Resolution)
Higher resolution presets optimized for FLUX models with better quality/speed balance.

### Ultra-Wide Presets (Modern Ratios)
Modern aspect ratios for ultra-wide and panoramic generation.

*For complete preset details, see [Width Height Selector Documentation](width_height_selector.md#preset-reference)*

## Usage Examples

### Basic Empty Latent Creation
1. **Select Preset**: Choose from dropdown (e.g., "1024×1024 - 1:1 (1.0MP) - SDXL")
2. **Set Batch Size**: Enter desired number of latents (e.g., 4)
3. **Connect Output**: Link latent output to KSampler or other processing nodes

### Custom Batch Creation
1. **Set Preset**: Select "custom"
2. **Enter Dimensions**: Input width and height manually
3. **Set Batch Size**: Configure number of latents needed
4. **Validation**: Automatic sanitization ensures compatibility

### Orientation Swapping
1. **Choose Preset**: Any preset (e.g., "1920×1080")
2. **Click Swap Button**: Blue button in bottom-right corner
3. **Result**: Gets swapped preset if available, or custom dimensions with swapped values
4. **Widget Update**: Width/height widgets automatically update

### Memory-Aware Batch Processing
1. **Large Batch**: Set batch_size to 16 or higher
2. **Memory Warning**: Node provides memory usage estimation
3. **Optimization**: Choose appropriate resolution preset for available VRAM

## Common Workflows

### Batch Generation Pipeline
```
Empty Latent Batch → KSampler → VAE Decode → Save Image
(batch_size: 4)      ↓         ↓            ↓
                   4 samples  4 images    4 files
```
- Create 4 empty latents at once
- Process all through sampling
- Generate 4 images in single operation
- Efficient for parameter exploration

### Model Comparison Workflow
```
Empty Latent Batch → [Multiple KSamplers] → [Multiple VAE Decoders] → Compare Results
(batch_size: 8)      ↓                      ↓                        ↓
                   Split batch            Process variants         Side-by-side
```
- Create consistent batch of empty latents
- Split across different samplers/models
- Compare results with identical starting conditions

### Upscaling Preparation
```
Empty Latent Batch → KSampler → VAE Decode → Resolution Calculator → Upscaler
(832×1216, batch:4)  ↓         ↓            ↓                     ↓
                   Sample    Decode       Calculate 2x           Upscale batch
```
- Generate batch at base resolution
- Calculate upscale dimensions
- Process entire batch through upscaler

### Aspect Ratio Exploration
```
Empty Latent Batch → [Clone to multiple orientations] → Parallel Processing
(1920×1080)          ↓                                  ↓
[Swap Button] →    Portrait & Landscape versions      Compare orientations
```
- Start with base preset
- Use swap button to create orientation variants
- Process both simultaneously

## Advanced Features

### Memory Estimation
The node provides built-in memory estimation for batch operations:

```python
# Example memory calculations
Batch Size: 4, Resolution: 1024×1024
Latent Tensor: 4 × 4 × 128 × 128 = 262,144 elements
Memory Usage: 262,144 × 4 bytes = 1.0 MB per batch
```

### Intelligent Preset Handling
- **Formatted Display**: Shows full metadata in dropdown
- **Original Extraction**: Extracts original preset name from formatted strings
- **Validation**: Verifies preset exists before processing
- **Fallback Logic**: Uses custom dimensions if preset is invalid

### Batch Size Optimization
- **Performance Warnings**: Alerts for large batch sizes
- **Memory Limits**: Prevents excessive memory allocation
- **Hardware Awareness**: Considers available system resources

## Tips and Best Practices

### Batch Size Selection
- **Small Batches (1-4)**: Good for testing and development
- **Medium Batches (5-16)**: Efficient for most production workflows
- **Large Batches (17-64)**: Only for high-memory systems and specific use cases

### Preset Selection
- **SDXL Projects**: Use SDXL presets for memory efficiency
- **FLUX Projects**: Use FLUX presets for optimal quality
- **Ultra-wide Projects**: Ensure sufficient VRAM for large resolutions
- **Custom Projects**: Use custom dimensions for specific requirements

### Memory Management
- Monitor memory usage with large batches
- Use appropriate resolution presets for available VRAM
- Consider splitting very large batches across multiple nodes
- Clear GPU memory between large batch operations

### Workflow Integration
- Always connect all three outputs (latent, width, height)
- Use width/height outputs for downstream dimension calculations
- Combine with Resolution Calculator for upscaling workflows
- Leverage batch processing for efficient parameter exploration

## Troubleshooting

### Common Issues
- **Out of Memory**: Reduce batch_size or use lower resolution presets
- **Invalid Dimensions**: Node automatically sanitizes to valid values
- **Preset Not Found**: Falls back to custom dimensions with warning
- **Swap Button Not Working**: Ensure node is not collapsed and button is visible

### Performance Optimization
- **Batch Size**: Start with smaller batches and increase as needed
- **Resolution**: Use appropriate presets for your model and VRAM
- **Memory Monitoring**: Watch for memory warnings and adjust accordingly
- **Cleanup**: Clear unused tensors between large batch operations

### Error Handling
- **Dimension Validation**: Automatic rounding to nearest valid values
- **Batch Size Limits**: Clamped to 1-64 range with warnings
- **Memory Allocation**: Graceful handling of insufficient memory
- **Preset Fallbacks**: Automatic fallback to custom dimensions

## Technical Details

### Latent Tensor Format
- **Shape**: [batch_size, 4, height//8, width//8]
- **Data Type**: torch.float32
- **Initialization**: torch.zeros for clean empty state
- **Memory Layout**: Contiguous tensor for optimal performance

### Validation Pipeline
1. **Preset Extraction**: Parse formatted preset strings
2. **Dimension Calculation**: Get base dimensions from preset or custom
3. **Sanitization**: Ensure divisible-by-8 constraint
4. **Batch Validation**: Check batch size limits
5. **Memory Estimation**: Calculate expected memory usage
6. **Tensor Creation**: Allocate and initialize latent tensor

### UI Integration
- **JavaScript Extension**: Custom UI for swap button functionality
- **Widget Synchronization**: Auto-update width/height when preset changes
- **Visual Feedback**: Hover effects and click animations
- **Event Handling**: Proper mouse event management

### Swap Button Implementation
- **Position Calculation**: Dynamic positioning based on node size
- **State Management**: Visual feedback for button interactions
- **Preset Intelligence**: Smart switching between compatible presets
- **Fallback Logic**: Custom dimension swapping when preset not available
