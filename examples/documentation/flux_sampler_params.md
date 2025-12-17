# Flux Sampler Params

## Overview
The **Flux Sampler Params** node provides a specialized parameter generator for FLUX model sampling. This tool was adapted from the excellent [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) project (now in maintenance mode) and enhanced for the ComfyAssets ecosystem.

## Attribution
This node is based on work from [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) by cubiq. The original project is in maintenance-only mode, and we've adopted and enhanced these tools to ensure continued support and compatibility with modern ComfyUI workflows.

## Features
- **FLUX-Optimized Parameters**: Specifically tuned for FLUX model requirements
- **Batch Processing Support**: Generate multiple parameter sets for comparative testing
- **Interactive UI Elements**: Visual controls for quick parameter adjustments
- **Smart Defaults**: Pre-configured optimal settings for FLUX workflows
- **Comprehensive Parameter Control**: Fine-tune all aspects of FLUX sampling

## Node Properties
- **Category**: `ComfyAssets/🧰 xyz-helpers`
- **Node Name**: `FluxSamplerParams`
- **Function**: `get_value`

## Inputs

### Required
| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `scheduler` | DROPDOWN | normal | [normal, simple, sgm_uniform] | Scheduler algorithm for sampling |
| `steps` | INT | 20 | 1-100 | Number of sampling steps |
| `guidance` | FLOAT | 3.5 | 0.0-100.0 | Guidance scale for conditioning |
| `max_shift` | FLOAT | 1.0 | 0.0-100.0 | Maximum shift value for FLUX |
| `base_shift` | FLOAT | 0.5 | 0.0-100.0 | Base shift value for FLUX |
| `denoise` | FLOAT | 1.0 | 0.0-1.0 | Denoising strength |
| `batch_mode` | DROPDOWN | single | [single, batch] | Single value or batch processing |

### Optional
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `batch_count` | INT | 1 | Number of batch variations (1-100) |
| `batch_seed_mode` | DROPDOWN | incremental | Seed generation mode for batches |
| `variation_seed` | INT | None | Optional seed for variations |
| `lora_params` | LORA_PARAMS | None | LoRA parameters from LoRAFolderBatch |

## Outputs
| Name | Type | Description |
|------|------|-------------|
| `sampler_params` | SAMPLER_PARAMS | Complete FLUX sampling parameters |
| `scheduler` | STRING | Selected scheduler algorithm |
| `steps` | INT | Number of sampling steps |
| `guidance` | FLOAT | Guidance scale value |

## Usage Examples

### Basic FLUX Sampling
```
FluxSamplerParams → KSampler → VAE Decode → Save Image
    scheduler: normal
    steps: 20
    guidance: 3.5
```

### Batch Parameter Testing
```
FluxSamplerParams → KSampler → Image Grid → Save
    batch_mode: batch
    batch_count: 5
    guidance: 2.0...5.0
```

### With LoRA Integration
```
LoRAFolderBatch → FluxSamplerParams → KSampler
    ↓                    ↓
    lora_params → Combined parameters
```

## Best Practices

### FLUX-Specific Settings
- **Guidance**: FLUX typically works best with lower guidance (2.0-5.0)
- **Steps**: 15-25 steps usually sufficient for FLUX
- **Scheduler**: `normal` or `sgm_uniform` recommended for FLUX
- **Shift Values**: Adjust for different quality/speed tradeoffs

### Batch Testing Workflow
1. Set `batch_mode` to `batch`
2. Configure parameter ranges using `...` syntax
3. Set appropriate `batch_count`
4. Use with image grid nodes for comparison

### Memory Optimization
- Start with smaller batch counts for testing
- Monitor VRAM usage with high batch counts
- Use incremental seed mode for reproducibility

## Integration with Other Nodes

### Works Well With
- **LoRA Folder Batch**: Combine multiple LoRAs with FLUX parameters
- **Plot Parameters**: Visualize parameter effects
- **Sampler Select Helper**: Dynamic sampler selection
- **Text Encode Sampler Params**: Add text conditioning

### Common Workflows
1. **Parameter Sweep**: Test multiple guidance/step combinations
2. **LoRA Testing**: Evaluate different LoRA strengths with FLUX
3. **Quality Comparison**: Compare different shift values
4. **Seed Exploration**: Generate variations with controlled seeds

## Tips and Tricks

### Optimal FLUX Settings
```python
# High Quality (Slower)
scheduler: "sgm_uniform"
steps: 25
guidance: 3.5
max_shift: 1.0
base_shift: 0.5

# Fast Preview
scheduler: "simple"
steps: 12
guidance: 2.5
max_shift: 0.8
base_shift: 0.4
```

### Batch Parameter Ranges
- Steps: `15...25+5` (test 15, 20, 25)
- Guidance: `2.0...5.0+0.5` (test 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)
- Denoise: `0.8...1.0+0.1` (test 0.8, 0.9, 1.0)

## Troubleshooting

### Common Issues
1. **Out of Memory**: Reduce batch_count or image resolution
2. **Poor Quality**: Increase steps or adjust guidance
3. **Artifacts**: Check shift values aren't too high
4. **Slow Generation**: Use `simple` scheduler for previews

### Parameter Guidelines
- Don't set guidance too high (>10) for FLUX
- Keep denoise at 1.0 for initial generation
- Adjust shift values gradually for best results

## Version History
- **1.0.0**: Initial adaptation from comfyui-essentials-nodes
- **1.0.1**: Added batch processing support
- **1.0.2**: Enhanced FLUX-specific optimizations
- **1.0.3**: Improved UI elements and parameter validation

## Credits
Original implementation by cubiq in [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials). Adapted and maintained by the ComfyAssets team.
