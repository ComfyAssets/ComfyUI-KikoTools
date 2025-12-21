# Scheduler Select Helper

## Overview
The **Scheduler Select Helper** node provides intelligent scheduler selection with sampler-aware recommendations and model-specific optimizations. Adapted from [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) (now in maintenance mode), this tool ensures optimal scheduler selection for different sampling algorithms and models.

## Attribution
This node is based on work from [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) by cubiq. The original project is in maintenance-only mode, and we've adopted and enhanced these tools to ensure continued support and compatibility with modern ComfyUI workflows.

## Features
- **Sampler-Aware Selection**: Recommends best schedulers for each sampler
- **Model Optimization**: Specific scheduler tuning for different models
- **Noise Schedule Profiles**: Pre-configured curves for various use cases
- **Visual Feedback**: Preview noise schedules
- **Batch Testing**: Compare multiple schedulers

## Node Properties
- **Category**: `ComfyAssets/🧰 xyz-helpers`
- **Node Name**: `SchedulerSelectHelper`
- **Function**: `select_scheduler`

## Inputs

### Required
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sampler_name` | STRING | - | Current sampler being used |
| `model_type` | DROPDOWN | auto | [auto, sdxl, sd15, flux] |
| `schedule_type` | DROPDOWN | smooth | [smooth, sharp, linear, custom] |

### Optional
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `override` | DROPDOWN | none | Force specific scheduler |
| `beta_schedule` | STRING | - | Custom beta schedule values |
| `visualize` | BOOLEAN | False | Show schedule curve |

## Outputs
| Name | Type | Description |
|------|------|-------------|
| `scheduler` | STRING | Selected scheduler name |
| `schedule_curve` | IMAGE | Visualization of noise schedule |
| `beta_values` | FLOAT_ARRAY | Beta schedule values |

## Scheduler Types Explained

### Normal
- **Curve**: Linear noise reduction
- **Best For**: General purpose
- **Samplers**: euler, dpm_fast

### Karras
- **Curve**: Improved noise schedule
- **Best For**: High quality
- **Samplers**: dpmpp_2m, dpmpp_2m_sde

### Exponential
- **Curve**: Exponential decay
- **Best For**: Fine details
- **Samplers**: dpmpp_3m_sde

### Simple
- **Curve**: Basic linear
- **Best For**: Fast generation
- **Samplers**: euler, lcm

### SGM Uniform
- **Curve**: Uniform distribution
- **Best For**: FLUX models
- **Samplers**: euler, dpmpp_2m

## Schedule Types

### Smooth (Default)
```python
# Gradual noise reduction
# Good for most content
→ karras or exponential
```

### Sharp
```python
# Aggressive early reduction
# Good for high contrast
→ normal or simple
```

### Linear
```python
# Constant reduction rate
# Predictable results
→ normal
```

### Custom
```python
# User-defined curve
# Advanced control
→ based on beta_schedule
```

## Usage Examples

### Automatic Selection
```
KSampler Settings → SchedulerSelectHelper → KSampler
    sampler_name: "dpmpp_2m_sde"
    model_type: auto
    → scheduler: "karras"
```

### Visual Comparison
```
SchedulerSelectHelper → Display
    visualize: True
    → Shows noise schedule curve
```

### Batch Testing
```
For each scheduler:
    SchedulerSelectHelper → KSampler → Save
    → Compare results
```

## Sampler-Scheduler Compatibility

### Optimal Pairings
| Sampler | Best Scheduler | Good Alternatives |
|---------|---------------|-------------------|
| euler | normal | karras |
| euler_a | karras | normal |
| heun | normal | - |
| dpm_fast | normal | simple |
| dpm_adaptive | normal | - |
| dpmpp_2m | karras | exponential |
| dpmpp_2m_sde | karras | exponential |
| dpmpp_3m_sde | exponential | karras |
| dpmpp_2s_a | karras | normal |
| lcm | simple | normal |

## Model-Specific Recommendations

### SDXL
```python
preferred_schedulers = ["karras", "exponential"]
# Better convergence for high-res
```

### SD 1.5
```python
preferred_schedulers = ["karras", "normal"]
# Classic combinations
```

### FLUX
```python
preferred_schedulers = ["simple", "sgm_uniform"]
# Optimized for FLUX architecture
```

## Best Practices

### Selection Strategy
1. Let auto-detection handle defaults
2. Override for specific artistic goals
3. Test multiple schedulers for hero images
4. Use visualization to understand curves

### Performance Tips
- Simple/normal for quick previews
- Karras/exponential for quality
- SGM uniform specifically for FLUX
- Match scheduler to sampler type

### Testing Workflow
```python
schedulers = ["normal", "karras", "exponential"]
for scheduler in schedulers:
    generate_image(scheduler)
    save_with_metadata(scheduler)
compare_results()
```

## Advanced Features

### Beta Schedule Customization
```python
# Custom exponential curve
beta_schedule = "0.00085, 0.0012, 0.0018, ..."

# Sharp early reduction
beta_schedule = "0.001, 0.002, 0.004, 0.006, ..."
```

### Schedule Visualization
- Plots noise reduction curve
- Shows sigma values
- Compares with standard schedules
- Exports schedule data

### Adaptive Selection
- Learns from user preferences
- Adapts to hardware capabilities
- Optimizes for generation speed

## Integration Examples

### Complete Pipeline
```
Sampler Combo → SchedulerSelectHelper → KSampler
    ↓                    ↓
sampler_name → Optimal scheduler selection
```

### A/B Testing
```
Same prompt → Different schedulers → Grid comparison
    normal vs karras vs exponential
```

### Noise Schedule Analysis
```
SchedulerSelectHelper → Plot Parameters
    visualize: True
    → Analyze noise curves
```

## Tips and Tricks

### Quality Optimization
```python
# For maximum quality
if sampler in ["dpmpp_3m_sde"]:
    use scheduler="exponential"
elif sampler in ["dpmpp_2m_sde"]:
    use scheduler="karras"
```

### Speed Optimization
```python
# For fast generation
use scheduler="simple" or "normal"
reduce step count by 20%
```

### Artistic Effects
- **Sharp details**: normal scheduler
- **Smooth gradients**: karras scheduler
- **Fine textures**: exponential scheduler

## Troubleshooting

### Artifacts or Noise
- Try different scheduler
- Check sampler compatibility
- Adjust step count

### Slow Convergence
- Switch from simple to karras
- Increase step count
- Check model compatibility

### Inconsistent Results
- Use same scheduler for batch
- Avoid random scheduler selection
- Fix seed for testing

## Visual Guide

### Noise Schedule Curves
```
Normal:    ████████████████
           Linear reduction

Karras:    ███████████▓▓▓░░
           Smooth curve

Exponential: ██████▓▓▓░░░░░
            Fast early reduction
```

## Common Workflows

### Scheduler Comparison
Test same seed with different schedulers to find optimal setting.

### Model Migration
When switching models, automatically adjust scheduler for best results.

### Quality Ladder
Progress through schedulers from fast to quality for different use cases.

## Version History
- **1.0.0**: Initial adaptation from comfyui-essentials-nodes
- **1.0.1**: Added visualization features
- **1.0.2**: Enhanced model detection
- **1.0.3**: Improved compatibility matrix

## Credits
Original implementation by cubiq in [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials). Adapted and maintained by the ComfyAssets team.
