# XYZ Grid Nodes for ComfyUI

Advanced parameter comparison grid generator for ComfyUI with Power Lora Loader-inspired interface.

## Features

### XYZ Plot Controller
- **Dynamic Multi-Selection**: Native dropdown widgets for selecting multiple models, VAEs, LoRAs, samplers, and schedulers
- **Smart Widget Management**: Widgets automatically show/hide based on selected axis types
- **Visual Organization**: Grouped widgets with headers for better organization
- **Right-Click Context Menu**:
  - Clear all selections for a specific type
  - Show image count breakdown
  - Keyboard shortcuts (Ctrl+Shift+C to clear all)
- **Real-time Image Count**: Node title shows total images that will be generated
- **Warning System**: Visual warning when generating over 100 images

### Supported Parameter Types
- **Models**: Multiple checkpoint selection
- **VAEs**: Multiple VAE selection with "Automatic" option
- **LoRAs**: Multiple LoRA selection with "None" option
- **Samplers**: euler, euler_ancestral, heun, dpm_2, etc.
- **Schedulers**: normal, karras, exponential, etc.
- **Numeric Parameters**:
  - CFG Scale
  - Steps
  - Seed
  - Denoise
  - CLIP Skip
  - Support for ranges (e.g., "5:15:2.5" generates 5, 7.5, 10, 12.5, 15)
- **Prompts**: Multiple prompts (one per line)

### Image Grid Combiner
- Automatic grid assembly with customizable spacing
- Smart labeling with parameter values
- Z-axis support for generating multiple grid pages
- Font size and label customization options

## Usage

1. Add an XYZ Plot Controller node
2. Select axis types (X, Y, and optionally Z)
3. Use the dropdown widgets to select values for each axis
4. Connect to your workflow (models, samplers, etc.)
5. Add Image Grid Combiner at the end to create the labeled grid

## Workflow Example

```
[XYZ Plot Controller] → [Checkpoint Loader] → [Sampling] → [Image Grid Combiner] → [Save Image]
```

The controller outputs the current iteration values which can be connected to corresponding nodes in your workflow.

## Tips

- Use the right-click menu to quickly clear selections
- Check the image count in the node title before running
- For large grids, consider using the Z-axis to split into multiple pages
- Numeric ranges are more efficient than listing each value

## Implementation Details

The implementation uses a hybrid approach:
- Python backend with native ComfyUI widget support
- JavaScript frontend for enhanced UI features
- Inspired by Power Lora Loader's dynamic widget management
- Context menus and keyboard shortcuts for power users