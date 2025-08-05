# XYZ Plot Controller - Advanced Implementation

## Overview

This is a complete reimplementation of the XYZ Plot Controller using the Power Lora Loader architecture from rgthree. The implementation provides dynamic widget management with an intuitive interface.

## Key Features

### Dynamic Widget System
- **"➕ Add [Type]" Buttons**: When you select models, vaes, loras, samplers, or schedulers for an axis, a button appears to add selections
- **Toggle On/Off**: Each dynamic widget has a checkbox to enable/disable it without removing
- **Right-Click Menu**: Right-click any dynamic widget to remove or toggle it
- **Live Count Updates**: Node title shows total image count in real-time

### Supported Axis Types
- **Models**: Dynamic dropdown widgets with available checkpoints
- **VAEs**: Dynamic dropdown widgets (includes "Automatic" option)
- **LoRAs**: Dynamic dropdown widgets (includes "None" option) 
- **Samplers**: Dynamic dropdown widgets with all sampler options
- **Schedulers**: Dynamic dropdown widgets with scheduler options
- **Numeric Parameters**: Text areas with helpful placeholders
  - CFG Scale
  - Steps
  - Seed
  - Denoise
  - CLIP Skip
- **Prompts**: Multi-line text area for prompt variations

### Technical Implementation

#### Python Backend (`xyz_plot_advanced.py`)
- Uses `FlexibleOptionalInputType` to accept any number of dynamic inputs
- Processes kwargs to extract widget values in format: `{axis}_{type}_{id}`
- Each dynamic widget sends: `{ "on": bool, "value": string }`

#### JavaScript Frontend (`xyz_plot_rgthree.js`)
- Manages dynamic widget creation/removal
- Custom widget drawing with toggle checkboxes
- Serialization/deserialization for workflow saving
- Real-time validation and counting

## Usage

1. Add the "XYZ Plot Controller (Advanced)" node
2. Select axis types (X, Y, Z)
3. Click "➕ Add [Type]" to add selections for that axis
4. Toggle widgets on/off with checkboxes
5. Right-click widgets for more options
6. For numeric types, use comma-separated values or ranges (e.g., "5:15:2.5")
7. For prompts, enter one per line

## Architecture Benefits

- **Clean Separation**: Python handles data, JavaScript handles UI
- **Flexible Input System**: Can accept unlimited dynamic widgets
- **Persistent State**: All widget states are saved with the workflow
- **Intuitive Interface**: Matches Power Lora Loader's proven UX patterns
- **Performance**: Only processes enabled widgets

## Future Enhancements

- Model/LoRA info display (CivitAI integration)
- Drag-and-drop reordering
- Preset management
- Batch widget operations