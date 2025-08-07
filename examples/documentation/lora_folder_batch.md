# LoRA Folder Batch

## Overview
The **LoRA Folder Batch** node automates the process of testing multiple LoRA models from a folder. This tool was adapted from [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) (now in maintenance mode) and enhanced with batch processing capabilities for efficient LoRA evaluation workflows.

## Attribution
This node is based on work from [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) by cubiq. The original project is in maintenance-only mode, and we've adopted and enhanced these tools to ensure continued support and compatibility with modern ComfyUI workflows.

## Features
- **Automatic Folder Scanning**: Discovers all .safetensors files in specified folders
- **Natural Sorting**: Intelligently sorts epochs (e.g., epoch_004, epoch_020, epoch_100)
- **Pattern Filtering**: Include/exclude LoRAs using regex patterns
- **Flexible Strength Control**: Single, multiple, or range-based strength values
- **Batch Modes**: Sequential or combinatorial strength application
- **Epoch Detection**: Automatically extracts epoch numbers from filenames

## Node Properties
- **Category**: `ComfyAssets/🧰 xyz-helpers`
- **Node Name**: `LoRAFolderBatch`
- **Function**: `batch_loras`

## Inputs

### Required
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder_path` | STRING | "." | Folder path relative to models/loras (or absolute) |
| `strength` | STRING | "1.0" | Strength values (see formats below) |
| `batch_mode` | DROPDOWN | sequential | [sequential, combinatorial] processing mode |

### Optional
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_pattern` | STRING | "" | Regex pattern to include files |
| `exclude_pattern` | STRING | "" | Regex pattern to exclude files |

### Strength Format Options
- **Single**: `"1.0"` - Apply same strength to all LoRAs
- **Multiple**: `"0.5, 0.75, 1.0"` - Comma-separated values
- **Range**: `"0.5...1.0+0.25"` - Start...End+Step format

## Outputs
| Name | Type | Description |
|------|------|-------------|
| `lora_params` | LORA_PARAMS | Batch parameters for processing |
| `lora_list` | STRING | List of discovered LoRAs with epoch info |
| `lora_count` | INT | Number of LoRAs found |

## Usage Examples

### Test All Epochs of a LoRA
```
LoRAFolderBatch → FluxSamplerParams → KSampler
    folder_path: "my_lora_training"
    strength: "1.0"
    batch_mode: sequential
```

### Strength Testing for Each LoRA
```
LoRAFolderBatch → KSampler → Image Grid
    folder_path: "test_loras"
    strength: "0.5, 0.75, 1.0"
    batch_mode: combinatorial
```

### Filter Specific Epochs
```
LoRAFolderBatch → Processing Pipeline
    folder_path: "training_results"
    include_pattern: "epoch_0[2-5]0"
    strength: "0.8...1.2+0.1"
```

## Batch Modes Explained

### Sequential Mode
Each LoRA gets one strength value in order:
- LoRA1 → strength[0]
- LoRA2 → strength[1]
- LoRA3 → strength[0] (cycles if fewer strengths than LoRAs)

### Combinatorial Mode
Each LoRA is tested with ALL strength values:
- LoRA1 → [0.5, 0.75, 1.0]
- LoRA2 → [0.5, 0.75, 1.0]
- LoRA3 → [0.5, 0.75, 1.0]

## File Naming Patterns

### Supported Epoch Formats
- `model-v1-000004.safetensors` → Epoch 4
- `style_epoch_020.safetensors` → Epoch 20
- `lora-000100.safetensors` → Epoch 100

### Natural Sorting Examples
Files are sorted intelligently:
1. `model-000004.safetensors`
2. `model-000020.safetensors`
3. `model-000100.safetensors`

## Best Practices

### Folder Organization
```
models/loras/
├── my_style/
│   ├── style-000010.safetensors
│   ├── style-000020.safetensors
│   └── style-000030.safetensors
└── character/
    ├── char-v2-000005.safetensors
    └── char-v2-000010.safetensors
```

### Testing Workflows
1. **Initial Testing**: Use single strength (1.0) to evaluate all epochs
2. **Fine-tuning**: Use combinatorial mode with multiple strengths
3. **Final Selection**: Filter to specific epochs and test strength range

### Pattern Filtering Examples
```python
# Include only specific versions
include_pattern: "v2|v3"

# Exclude test/backup files
exclude_pattern: "test|backup|old"

# Include specific epoch range
include_pattern: "epoch_0[3-7]0"
```

## Integration with Other Nodes

### Common Pipelines
1. **LoRA Comparison Grid**:
   ```
   LoRAFolderBatch → KSampler → Image Grid → Save
   ```

2. **Strength Testing**:
   ```
   LoRAFolderBatch → PlotParameters → Graph Display
   ```

3. **Combined with FLUX**:
   ```
   LoRAFolderBatch → FluxSamplerParams → KSampler
   ```

## Tips and Tricks

### Memory Management
- Start with fewer LoRAs when testing combinatorial mode
- Use sequential mode for initial epoch evaluation
- Clear LoRA cache between large batch runs

### Optimal Strength Ranges
- **Style LoRAs**: 0.5-1.0
- **Character LoRAs**: 0.7-1.2
- **Detail LoRAs**: 0.3-0.7

### Debugging
- Check `lora_list` output to verify correct files were found
- Use `lora_count` to confirm expected number of LoRAs
- Test patterns with include/exclude before full runs

## Troubleshooting

### No LoRAs Found
- Verify folder path (relative to models/loras or use absolute)
- Check file extensions (.safetensors)
- Test without filters first

### Pattern Not Working
- Patterns use Python regex syntax
- Test patterns in regex tester first
- Case-sensitive by default

### Memory Issues
- Reduce batch_count in combinatorial mode
- Process LoRAs in smaller groups
- Use sequential mode for large sets

## Advanced Examples

### Multi-Version Testing
```python
# Test different versions at different strengths
folder_path: "character_loras"
include_pattern: "v[1-3]"
strength: "0.6, 0.8, 1.0"
batch_mode: combinatorial
```

### Epoch Progression Analysis
```python
# Test every 10th epoch
folder_path: "training_output"
include_pattern: "0[0-9]0\\.safetensors$"
strength: "1.0"
batch_mode: sequential
```

## Version History
- **1.0.0**: Initial adaptation from comfyui-essentials-nodes
- **1.0.1**: Added natural sorting for epochs
- **1.0.2**: Enhanced pattern filtering
- **1.0.3**: Improved batch modes and strength parsing

## Credits
Original implementation by cubiq in [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials). Adapted and maintained by the ComfyAssets team.