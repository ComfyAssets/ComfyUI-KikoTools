# Text Encode Sampler Params

## Overview
The **Text Encode Sampler Params** node combines text encoding with sampler parameter management, providing a unified interface for prompt processing and sampling configuration. Adapted from [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) (now in maintenance mode), this tool streamlines the text-to-image pipeline setup.

## Attribution
This node is based on work from [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials) by cubiq. The original project is in maintenance-only mode, and we've adopted and enhanced these tools to ensure continued support and compatibility with modern ComfyUI workflows.

## Features
- **Unified Interface**: Combine text encoding and sampler params in one node
- **Dynamic Prompt Processing**: Support for wildcards and syntax
- **Parameter Templates**: Pre-configured settings for common scenarios
- **Batch Text Processing**: Handle multiple prompts efficiently
- **Model-Aware Encoding**: Optimize for different text encoders

## Node Properties
- **Category**: `ComfyAssets/🧰 xyz-helpers`
- **Node Name**: `TextEncodeSamplerParams`
- **Function**: `encode_and_params`

## Inputs

### Required
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | STRING | - | Prompt text to encode |
| `clip` | CLIP | - | CLIP model for encoding |
| `sampler_name` | DROPDOWN | dpmpp_2m | Sampling algorithm |
| `scheduler` | DROPDOWN | karras | Noise scheduler |
| `steps` | INT | 20 | Sampling steps |
| `cfg` | FLOAT | 7.0 | CFG scale |

### Optional
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `negative_text` | STRING | "" | Negative prompt |
| `seed` | INT | -1 | Random seed (-1 for random) |
| `denoise` | FLOAT | 1.0 | Denoising strength |
| `template` | DROPDOWN | none | Parameter template |

## Outputs
| Name | Type | Description |
|------|------|-------------|
| `positive` | CONDITIONING | Encoded positive prompt |
| `negative` | CONDITIONING | Encoded negative prompt |
| `sampler_params` | DICT | Complete sampler parameters |

## Templates

### Portrait Photography
```python
template: "portrait"
→ steps: 25
→ cfg: 7.5
→ sampler: dpmpp_2m_sde
→ scheduler: karras
```

### Landscape Art
```python
template: "landscape"
→ steps: 30
→ cfg: 8.0
→ sampler: dpmpp_3m_sde
→ scheduler: exponential
```

### Quick Preview
```python
template: "preview"
→ steps: 12
→ cfg: 6.0
→ sampler: euler
→ scheduler: normal
```

### High Detail
```python
template: "detailed"
→ steps: 40
→ cfg: 7.0
→ sampler: dpm_adaptive
→ scheduler: karras
```

## Usage Examples

### Basic Text-to-Image
```
TextEncodeSamplerParams → KSampler → VAE Decode
    text: "beautiful landscape"
    negative_text: "ugly, blurry"
    steps: 20
```

### Template-Based Generation
```
TextEncodeSamplerParams → KSampler
    text: "portrait of a person"
    template: "portrait"
    → Optimized portrait settings
```

### Batch Processing
```
Multiple Prompts → TextEncodeSamplerParams → Batch Generate
    → Encode all prompts with same settings
```

## Prompt Syntax Support

### Wildcards
```
{red|blue|green} car
→ Randomly selects color
```

### Emphasis
```
(important:1.2) detail
→ Increases weight to 1.2
```

### Alternation
```
[cat|dog] in garden
→ Alternates between options
```

## Best Practices

### Text Encoding
1. Keep prompts concise and descriptive
2. Use emphasis for important elements
3. Structure prompts logically
4. Test negative prompts impact

### Parameter Selection
```python
# Quality over speed
steps: 30-40
cfg: 7-8
sampler: dpmpp_3m_sde

# Speed over quality
steps: 10-15
cfg: 5-6
sampler: euler
```

### Negative Prompts
```python
# Common negatives
"ugly, tiling, poorly drawn, out of frame"

# Style-specific
"cartoon, anime" (for realism)
"realistic, photo" (for artwork)
```

## Integration with Other Nodes

### Complete Pipeline
```
TextEncodeSamplerParams → KSampler → VAE Decode
         ↓                    ↑
    All parameters      From Model Loader
```

### With LoRA
```
LoRAFolderBatch → TextEncodeSamplerParams → Generate
    → Apply LoRA to encoded text
```

### Multi-Pass Processing
```
TextEncodeSamplerParams → First Pass (low res)
                       ↘ Second Pass (high res)
```

## Advanced Features

### Dynamic Templates
```python
# Load template based on prompt content
if "portrait" in text:
    use_template("portrait")
elif "landscape" in text:
    use_template("landscape")
```

### Prompt Weighting
```python
# Automatic weight calculation
analyze_prompt_importance()
apply_semantic_weights()
```

### CLIP Skip Support
- Adjust CLIP layers used
- Model-specific optimization
- Quality vs style balance

## Tips and Tricks

### Prompt Optimization
1. Front-load important elements
2. Use commas for separation
3. Avoid contradictions
4. Test with different CFG values

### Performance Tuning
```python
# Memory efficient
encode_in_batches = True
clear_cache_between = True

# Speed priority
use_half_precision = True
minimize_conditioning = True
```

### Quality Enhancement
- Higher CFG for prompt adherence
- Lower CFG for creativity
- Balance with step count

## Common Workflows

### Style Transfer
```
Reference Image → Extract Style
                ↓
TextEncodeSamplerParams → Apply Style
    text: "in the style of [extracted]"
```

### Prompt Evolution
```
Base Prompt → Variations → TextEncodeSamplerParams
    → Test different phrasings
```

### A/B Testing
```
Same prompt → Different parameters → Compare
    template A vs template B
```

## Troubleshooting

### Poor Text Adherence
- Increase CFG scale
- Simplify prompt
- Check CLIP model compatibility

### Over-saturation
- Reduce CFG scale
- Adjust negative prompt
- Check sampler settings

### Encoding Errors
- Verify CLIP model loaded
- Check text formatting
- Remove special characters

## Parameter Guidelines

### CFG Scale Effects
```
Low (3-5): Creative, loose interpretation
Medium (6-8): Balanced adherence
High (9-12): Strict prompt following
Very High (13+): Potential artifacts
```

### Step Count Impact
```
Low (10-15): Fast, rough
Medium (20-30): Good balance
High (40-50): Maximum quality
Very High (50+): Diminishing returns
```

## Model-Specific Settings

### SDXL
- CFG: 6-8
- CLIP Skip: 1-2
- Emphasis: Moderate

### SD 1.5
- CFG: 7-9
- CLIP Skip: 1-2
- Emphasis: Standard

### FLUX
- CFG: 3-5
- CLIP Skip: 0
- Emphasis: Subtle

## Version History
- **1.0.0**: Initial adaptation from comfyui-essentials-nodes
- **1.0.1**: Added template system
- **1.0.2**: Enhanced prompt syntax support
- **1.0.3**: Improved batch processing

## Credits
Original implementation by cubiq in [comfyui-essentials-nodes](https://github.com/cubiq/ComfyUI_essentials). Adapted and maintained by the ComfyAssets team.
