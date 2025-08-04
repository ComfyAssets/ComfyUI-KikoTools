# XYZ Grid Examples

This directory contains example workflows demonstrating the XYZ Grid nodes for ComfyUI.

## Overview

The XYZ Grid system allows you to create parameter comparison grids with any combination of:
- Models/Checkpoints
- Samplers
- Schedulers
- CFG Scale
- Steps
- Clip Skip
- VAEs
- LoRAs
- Prompts
- Seeds
- Flux Guidance
- Denoise strength

## Basic Usage

1. Add an **XYZ Plot Controller** node to your workflow
2. Configure X and Y axes (and optionally Z for multiple grids)
3. Connect the appropriate outputs to your generation nodes
4. Add an **Image Grid Combiner** node
5. Connect your generated images to the combiner
6. Run once - the system handles all iterations automatically!

## Node Descriptions

### XYZ Plot Controller

The main configuration node that drives the grid generation.

**Inputs:**
- `x_axis_type`: Parameter type for X axis (horizontal)
- `x_values`: Values to iterate over (comma-separated or range syntax)
- `y_axis_type`: Parameter type for Y axis (vertical)
- `y_values`: Values to iterate over
- `z_axis_type`: (Optional) Parameter type for Z axis (multiple grids)
- `z_values`: Values for Z axis
- `auto_queue`: Enable automatic execution queuing

**Outputs:**
- `grid_data`: Configuration data for the combiner
- `x_string`, `x_int`, `x_float`: Current X value in different types
- `y_string`, `y_int`, `y_float`: Current Y value in different types
- `z_string`, `z_int`, `z_float`: Current Z value in different types
- `batch_id`: Unique identifier for this grid batch

### Image Grid Combiner

Collects generated images and assembles them into labeled grids.

**Inputs:**
- `images`: Generated images from your workflow
- `grid_data`: Configuration from XYZ Plot Controller
- `font_size`: Size of label text (default: 20)
- `grid_gap`: Pixel gap between images (default: 10)
- `label_height`: Height of label area (default: 30)
- `include_labels`: Whether to add labels (default: true)

**Outputs:**
- `grid_image`: The assembled grid image(s)
- `grid_info`: Information about the grid

## Value Syntax

### Lists
Use comma-separated values:
```
euler, euler_ancestral, dpm_2, dpm_2_ancestral
```

### Ranges
Use colon syntax for numeric ranges:
```
5:10:1     # From 5 to 10, step 1 → [5, 6, 7, 8, 9, 10]
0.5:2:0.5  # From 0.5 to 2, step 0.5 → [0.5, 1.0, 1.5, 2.0]
10:50:10   # From 10 to 50, step 10 → [10, 20, 30, 40, 50]
```

### Model/File Selection
Use the quick-select dropdowns or type filenames:
```
model1.safetensors, model2.ckpt, checkpoint_v3.pt
```

## Connection Examples

### Varying Sampler
1. Set X axis to "sampler"
2. Connect `x_string` output to KSampler's `sampler_name` input

### Varying CFG Scale
1. Set Y axis to "cfg_scale"
2. Connect `y_float` output to KSampler's `cfg` input

### Varying Model
1. Set X axis to "model"
2. Connect `x_string` output to CheckpointLoader's `ckpt_name` input

### Varying Prompt
1. Set Y axis to "prompt"
2. Enter different prompts on separate lines in `y_values`
3. Connect `y_string` output to CLIPTextEncode's `text` input

## Tips and Tricks

1. **Memory Management**: The system includes intelligent model caching. For large grids with multiple models, it will optimize loading order.

2. **Progress Tracking**: Watch the node title for progress updates (e.g., "XYZ Plot Controller [3/12]")

3. **Large Grids**: Be mindful of total image count. The node shows a warning for grids over 100 images.

4. **Z-Axis**: When using Z-axis, you'll get multiple grid images - one for each Z value.

5. **Label Customization**: Use prefixes to clarify labels (e.g., "CFG=" for CFG values)

## Workflow Files

- `basic_model_cfg_grid.json`: Compare 2 models across 3 CFG values
- `sampler_comparison.json`: Compare all samplers at different step counts
- `prompt_variations.json`: Test prompt variations across different models
- `advanced_3d_grid.json`: Use Z-axis for LoRA strength variations
- `flux_guidance_test.json`: Test Flux-specific parameters

Load these workflows in ComfyUI to see practical examples of the XYZ Grid system in action!