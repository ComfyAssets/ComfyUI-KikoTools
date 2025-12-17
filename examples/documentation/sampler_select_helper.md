# Sampler Select Helper

## Overview
The **Sampler Select Helper** node provides intelligent sampler selection with model-specific recommendations and compatibility checking. Adapted from [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) (now in maintenance mode), this tool ensures optimal sampler-scheduler combinations for different model architectures.

## Attribution
This node is based on work from [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) by cubiq. The original project is in maintenance-only mode, and we've adopted and enhanced these tools to ensure continued support and compatibility with modern ComfyUI workflows.

## Features
- **Model-Aware Selection**: Automatic recommendations based on model type
- **Compatibility Validation**: Ensures sampler-scheduler pairs work well together
- **Performance Profiles**: Pre-configured settings for quality vs speed
- **Dynamic Updates**: Adapts to newly available samplers
- **Batch Support**: Test multiple samplers in sequence

## Node Properties
- **Category**: `ComfyAssets/🧰 xyz-helpers`
- **Node Name**: `SamplerSelectHelper`
- **Function**: `select_sampler`

## Inputs

### Required
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_type` | DROPDOWN | auto | [auto, sdxl, sd15, flux, custom] |
| `quality_preset` | DROPDOWN | balanced | [fast, balanced, quality, extreme] |
| `sampler_override` | DROPDOWN | auto | Specific sampler selection |

### Optional
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `scheduler_override` | DROPDOWN | auto | Specific scheduler selection |
| `model_name` | STRING | - | Model name for auto-detection |
| `custom_rules` | STRING | - | JSON rules for custom selection |

## Outputs
| Name | Type | Description |
|------|------|-------------|
| `sampler_name` | STRING | Selected sampler |
| `scheduler` | STRING | Selected scheduler |
| `recommended_steps` | INT | Suggested step count |
| `recommended_cfg` | FLOAT | Suggested CFG scale |

## Model-Specific Recommendations

### SDXL Models
```python
quality_preset: "balanced"
→ sampler: "dpmpp_2m"
→ scheduler: "karras"
→ steps: 25
→ cfg: 7.0
```

### SD 1.5 Models
```python
quality_preset: "quality"
→ sampler: "dpmpp_2m_sde"
→ scheduler: "exponential"
→ steps: 30
→ cfg: 7.5
```

### FLUX Models
```python
quality_preset: "fast"
→ sampler: "euler"
→ scheduler: "simple"
→ steps: 15
→ cfg: 3.5
```

## Quality Presets Explained

### Fast (Preview)
- **Goal**: Quick iterations
- **Steps**: 10-15
- **Samplers**: euler, dpm_fast
- **Use Case**: Testing prompts

### Balanced (Default)
- **Goal**: Good quality/speed ratio
- **Steps**: 20-25
- **Samplers**: dpmpp_2m, dpmpp_2m_sde
- **Use Case**: Regular generation

### Quality
- **Goal**: Best visual quality
- **Steps**: 30-40
- **Samplers**: dpmpp_3m_sde, dpm_adaptive
- **Use Case**: Final renders

### Extreme
- **Goal**: Maximum quality
- **Steps**: 50-100
- **Samplers**: dpm_adaptive, dpmpp_3m_sde
- **Use Case**: Hero images

## Usage Examples

### Auto Model Detection
```
Load Model → SamplerSelectHelper → KSampler
    model_type: auto
    quality_preset: balanced
```

### Custom Override
```
SamplerSelectHelper → KSampler
    sampler_override: "dpmpp_3m_sde"
    scheduler_override: "exponential"
```

### Batch Testing
```
SamplerSelectHelper → Batch Process
    quality_preset: [fast, balanced, quality]
    → Compare outputs
```

## Compatibility Matrix

### Recommended Combinations
| Sampler | Best Schedulers | Avoid |
|---------|----------------|--------|
| euler | normal, karras | sgm_uniform |
| euler_a | normal, karras | simple |
| dpmpp_2m | karras, exponential | - |
| dpmpp_2m_sde | karras, exponential | simple |
| dpmpp_3m_sde | exponential | simple |
| dpm_adaptive | normal | karras |

## Best Practices

### Model Type Detection
1. Use `auto` for automatic detection
2. Override only when necessary
3. Provide model_name for better accuracy

### Performance Optimization
```python
# Quick preview workflow
quality_preset: "fast"
→ 10 steps, euler sampler

# Final production
quality_preset: "quality"
→ 35 steps, dpmpp_3m_sde

# Experimental/artistic
quality_preset: "extreme"
→ 75 steps, dpm_adaptive
```

### Custom Rules Format
```json
{
  "model_pattern": "anime.*",
  "sampler": "dpmpp_2m_sde",
  "scheduler": "karras",
  "steps": 28,
  "cfg": 7.0
}
```

## Integration with Other Nodes

### Complete Pipeline
```
Model Loader → SamplerSelectHelper → KSampler
             ↘ FluxSamplerParams ↗
```

### A/B Testing
```
SamplerSelectHelper → KSampler → Image A
    quality: fast
SamplerSelectHelper → KSampler → Image B
    quality: quality
→ Compare Results
```

## Advanced Features

### Dynamic Sampler Discovery
- Automatically detects new samplers
- Updates compatibility matrix
- Maintains optimal pairings

### Performance Profiling
- Tracks generation times
- Suggests optimal settings
- Adapts to hardware capabilities

### Model Fingerprinting
- Identifies model architecture
- Applies specific optimizations
- Learns from usage patterns

## Tips and Tricks

### Speed vs Quality
1. Start with "fast" for prompt testing
2. Move to "balanced" for iteration
3. Use "quality" for final output
4. Reserve "extreme" for special cases

### Sampler Selection Logic
```python
if model_type == "flux":
    prefer ["euler", "dpmpp_2m"]
elif model_type == "sdxl":
    prefer ["dpmpp_2m_sde", "dpmpp_3m_sde"]
else:
    use ["dpmpp_2m", "euler_a"]
```

### Memory Considerations
- Fast presets use less memory
- Extreme presets may require more VRAM
- Adaptive samplers adjust dynamically

## Troubleshooting

### Wrong Sampler Selected
- Check model_type setting
- Verify model detection
- Use manual override if needed

### Poor Quality Output
- Increase quality preset
- Check recommended steps
- Verify CFG scale

### Performance Issues
- Start with fast preset
- Reduce step count
- Try simpler samplers

## Common Workflows

### Model Comparison
Test same prompt across different models with optimal settings for each.

### Quality Ladder
Progress from fast to extreme quality to find optimal balance.

### Sampler Shootout
Compare all compatible samplers for specific model/prompt combination.

## Version History
- **1.0.0**: Initial adaptation from comfyui-essentials-nodes
- **1.0.1**: Added FLUX model support
- **1.0.2**: Enhanced compatibility matrix
- **1.0.3**: Improved auto-detection

## Credits
Original implementation by cubiq in [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials). Adapted and maintained by the ComfyAssets team.
