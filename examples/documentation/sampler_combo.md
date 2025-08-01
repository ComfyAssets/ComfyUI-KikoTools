# Sampler Combo Documentation

## Overview

The Sampler Combo is a unified ComfyUI node that combines sampler, scheduler, steps, and CFG settings into a single interface. It reduces workflow complexity while ensuring compatible parameter combinations and providing optimization recommendations.

## Features

### 🎯 **Unified Configuration**
- Single node for all sampling parameters
- Compatible sampler + scheduler combinations
- Optimized steps and CFG recommendations
- Reduced workflow complexity

### 🧠 **Smart Recommendations**
- Scheduler suggestions based on selected sampler
- Optimal steps range for each sampler
- CFG scale recommendations
- Compatibility warnings and suggestions

### ✅ **Built-in Validation**
- Parameter validation and sanitization
- Error handling with safe defaults
- Performance optimization hints
- Real-time compatibility checking

### 📊 **Analysis Tools**
- Combo configuration analysis
- Performance assessment
- Optimization recommendations
- Compatibility scoring

## Node Interface

### Inputs
- **sampler_name**: Dropdown with available sampling algorithms
- **scheduler**: Dropdown with compatible schedulers
- **steps**: Integer slider (1-100 steps)
- **cfg**: Float slider (0.0-20.0 CFG scale)

### Outputs
- **sampler_name**: Selected sampler algorithm
- **scheduler**: Selected scheduler algorithm
- **steps**: Number of sampling steps
- **cfg**: CFG scale value

## Available Samplers

### Primary Samplers
| Sampler | Type | Speed | Quality | Best For |
|---------|------|-------|---------|----------|
| euler | Deterministic | Fast | Good | General use |
| euler_ancestral | Stochastic | Fast | Good | Creative variation |
| heun | Higher-order | Medium | Better | Quality focus |
| dpm_2 | Multi-step | Medium | Good | Balanced |
| dpm_2_ancestral | Stochastic | Medium | Good | Creative quality |
| lms | Linear | Fast | Good | Simple scenes |
| dpm_fast | Optimized | Very Fast | Good | Speed priority |
| dpm_adaptive | Adaptive | Variable | Best | Automatic tuning |

### Advanced Samplers
| Sampler | Type | Speed | Quality | Best For |
|---------|------|-------|---------|----------|
| dpmpp_2s_ancestral | Advanced | Medium | Better | High quality |
| dpmpp_2m | Optimized | Fast | Better | Speed + quality |
| dpmpp_2m_sde | Stochastic | Medium | Best | Maximum quality |
| dpmpp_3m_sde | Latest | Medium | Best | Cutting edge |
| ddim | Classic | Fast | Good | Compatibility |
| uni_pc | Unified | Fast | Better | Efficiency |

## Available Schedulers

### Linear Schedulers
- **normal**: Standard linear schedule
- **linear**: Basic linear distribution
- **sgm_uniform**: Uniform distribution

### Advanced Schedulers
- **karras**: Karras noise schedule (recommended)
- **exponential**: Exponential decay
- **polyexponential**: Polynomial exponential
- **beta**: Beta distribution schedule

### Specialized Schedulers
- **cosine**: Cosine annealing schedule
- **simple**: Simplified schedule
- **ddim_uniform**: DDIM uniform schedule
- **laplace**: Laplace distribution

## Optimization Guidelines

### Recommended Combinations

#### Speed Optimized
```
Sampler: euler or dpm_fast
Scheduler: normal or simple
Steps: 15-25
CFG: 6.0-8.0
```

#### Quality Optimized
```
Sampler: dpmpp_2m_sde or dpmpp_3m_sde
Scheduler: karras
Steps: 25-35
CFG: 7.0-9.0
```

#### Balanced
```
Sampler: dpmpp_2m or heun
Scheduler: karras or normal
Steps: 20-30
CFG: 7.0-8.5
```

### Steps Recommendations

| Sampler Type | Min Steps | Optimal | Max Steps |
|--------------|-----------|---------|-----------|
| Fast (euler, dpm_fast) | 10 | 20 | 30 |
| Standard (heun, dpm_2) | 15 | 25 | 40 |
| Advanced (dpmpp_*) | 20 | 30 | 50 |
| Adaptive | 10 | 25 | 100 |

### CFG Scale Guidelines

| Content Type | CFG Range | Recommended |
|--------------|-----------|-------------|
| Photorealistic | 5.0-8.0 | 7.0 |
| Artistic/Stylized | 7.0-12.0 | 9.0 |
| Abstract/Creative | 8.0-15.0 | 11.0 |
| Text/Details | 10.0-20.0 | 13.0 |

## Usage Examples

### Basic Configuration
```
sampler_name: euler
scheduler: normal
steps: 20
cfg: 7.0
```

### High Quality Setup
```
sampler_name: dpmpp_2m_sde
scheduler: karras
steps: 30
cfg: 8.0
```

### Speed Priority
```
sampler_name: dpm_fast
scheduler: simple
steps: 15
cfg: 6.5
```

## Advanced Features

### Compatibility Analysis
The node provides real-time analysis of parameter compatibility:
- Scheduler compatibility with selected sampler
- Steps optimization for sampler type
- CFG scale recommendations
- Performance impact assessment

### Error Handling
- Invalid samplers default to 'euler'
- Invalid schedulers default to 'normal'
- Out-of-range steps clamped to valid range
- Invalid CFG values sanitized to safe defaults

### Performance Tips
1. **Use Karras scheduler** for most samplers (better quality)
2. **Start with 20-30 steps** for most use cases
3. **Keep CFG 6.0-9.0** for realistic images
4. **Try dpmpp_2m** for best speed/quality balance
5. **Use euler** for fastest generation

## Troubleshooting

### Common Issues
- **Slow generation**: Try euler or dpm_fast samplers
- **Poor quality**: Increase steps or try dpmpp_2m_sde
- **Overcooked images**: Lower CFG scale
- **Underdetailed**: Increase CFG or steps
- **Artifacts**: Try karras scheduler or different sampler

### Performance Optimization
- **GPU Memory**: Lower steps if running out of VRAM
- **Speed**: Use euler + normal + 15-20 steps
- **Quality**: Use dpmpp_2m_sde + karras + 25-30 steps
- **Compatibility**: Stick to euler/heun for broad model support

## Integration

The Sampler Combo node outputs are compatible with all standard ComfyUI sampling nodes:
- KSampler
- KSamplerAdvanced
- Custom sampling workflows
- Upscaling pipelines
- Img2img workflows

Connect the outputs directly to your sampling node inputs for streamlined configuration.
