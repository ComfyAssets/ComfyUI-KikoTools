# ComfyUI-KikoTools

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![ComfyUI](https://img.shields.io/badge/ComfyUI-compatible-green.svg)
![Tests](https://github.com/ComfyAssets/ComfyUI-KikoTools/workflows/Tests/badge.svg)
![Code Quality](https://github.com/ComfyAssets/ComfyUI-KikoTools/workflows/Code%20Quality/badge.svg)

> A modular collection of essential custom ComfyUI nodes missing from the standard release.

ComfyUI-KikoTools provides carefully crafted, production-ready nodes grouped under the **"ComfyAssets"** category. Each tool is designed with clean interfaces, comprehensive testing, and optimized performance for SDXL and FLUX workflows.

## 🚀 Features

### ✨ Current Tools

#### 📐 Resolution Calculator
Calculate upscaled dimensions from image or latent inputs with precision.

- **Smart Input Handling**: Works with both IMAGE and LATENT tensors
- **Model Optimized**: Specific optimizations for SDXL (~1MP) and FLUX (0.2-2MP) models
- **Constraint Enforcement**: Automatically ensures dimensions divisible by 8
- **Flexible Scaling**: Supports scale factors from 1.0x to 8.0x with 0.1 precision
- **Aspect Ratio Preservation**: Maintains original proportions during scaling

**Use Cases:**
- Calculate target dimensions for upscaler nodes
- Plan memory usage for large generations  
- Ensure ComfyUI tensor compatibility
- Optimize batch processing workflows

#### 📏 Width Height Selector
Advanced preset-based dimension selection with visual swap button.

- **26 Curated Presets**: SDXL, FLUX, and Ultra-Wide optimized resolutions
- **Smart Categories**: Organized by model type and aspect ratio
- **Visual Swap Button**: Modern blue button for quick orientation changes
- **Intelligent Swapping**: Preset-aware orientation switching
- **Custom Support**: Manual dimension input with validation

**Use Cases:**
- Quick dimension selection for different models
- Consistent aspect ratios across workflows
- Mobile and ultra-wide format support
- Integration with upscaling pipelines

#### 🎲 Seed History
Advanced seed tracking with interactive history management and UI.

- **Automatic Tracking**: Monitors all seed changes with timestamps
- **Interactive History**: Click any historical seed to reload instantly
- **Smart Deduplication**: 500ms window prevents duplicate rapid additions
- **Persistent Storage**: History survives browser sessions and ComfyUI restarts
- **Auto-Hide UI**: Clean interface that hides after 2.5 seconds of inactivity
- **Visual Feedback**: Toast notifications and selection highlighting

**Use Cases:**
- Track promising seeds during creative exploration
- Quickly return to successful generation parameters
- Maintain reproducibility across sessions
- Compare results from different seeds efficiently

#### ⚙️ Sampler Combo
Unified sampling configuration interface combining sampler, scheduler, steps, and CFG.

- **All-in-One Interface**: Single node for complete sampling configuration
- **Smart Recommendations**: Optimal settings suggestions per sampler type
- **Compatibility Validation**: Ensures sampler/scheduler combinations work well
- **Intelligent Defaults**: Context-aware parameter recommendations
- **Range Validation**: Prevents invalid parameter combinations
- **Comprehensive Tooltips**: Detailed guidance for each parameter

**Use Cases:**
- Simplify complex sampling workflows
- Ensure optimal sampler/scheduler combinations
- Reduce node clutter in workflows
- Quick sampling parameter experimentation

### 🔧 Architecture Highlights

- **Modular Design**: Each tool is self-contained and independently testable
- **Test-Driven Development**: 100% test coverage with comprehensive unit tests
- **Clean Interfaces**: Standardized input/output patterns across all tools
- **Separation of Concerns**: Clear distinction between logic, UI, and integration layers
- **SOLID Principles**: Extensible architecture following software engineering best practices

## 📦 Installation

### ComfyUI Manager (Recommended)

1. Open ComfyUI Manager
2. Search for "ComfyUI-KikoTools"
3. Click Install
4. Restart ComfyUI

### Manual Installation

```bash
cd ComfyUI/custom_nodes/
git clone https://github.com/ComfyAssets/ComfyUI-KikoTools.git
cd ComfyUI-KikoTools
pip install -r requirements-dev.txt
```

Restart ComfyUI and look for **ComfyAssets** nodes in the node browser.

## 🎯 Quick Start

### Resolution Calculator Example

```
Image Loader → Resolution Calculator → Upscaler
             ↘ scale_factor: 1.5    ↗
```

**Input:** 832×1216 (SDXL portrait format)  
**Scale:** 1.5x  
**Output:** 1248×1824 (ready for upscaling)

### Width Height Selector Example

```
Width Height Selector → EmptyLatentImage → Model
preset: "1920×1080"   ↘ 1920×1080      ↗
[swap button]
```

**Preset:** FLUX HD (1920×1080)  
**Output:** 1920×1080 (16:9 cinematic)  
**Swap Button:** Click to get 1080×1920 (9:16 portrait)

### Seed History Example

```
Seed History → KSampler → VAE Decode → Save Image
🎲 12345    ↘ seed    ↗
[History UI: 54321, 99999, 11111...]
```

**Current Seed:** 12345  
**History:** Auto-tracked previous seeds with timestamps  
**Interaction:** Click any historical seed to reload instantly

### Sampler Combo Example

```
Sampler Combo → KSampler → VAE Decode → Save Image
⚙️ All Settings ↘ sampler/scheduler/steps/cfg ↗
```

**Configuration:** euler, normal, 20 steps, CFG 7.0  
**Output:** Complete sampling configuration in one node  
**Smart Features:** Recommendations and compatibility validation

### Common Workflows

<details>
<summary><b>SDXL Portrait Upscaling</b></summary>

```json
{
  "workflow": "Load SDXL portrait → Calculate 1.5x dimensions → Feed to upscaler",
  "input_resolution": "832×1216", 
  "scale_factor": 1.5,
  "output_resolution": "1248×1824",
  "memory_efficient": true
}
```
</details>

<details>
<summary><b>FLUX Batch Processing</b></summary>

```json
{
  "workflow": "Generate latents → Calculate target size → Batch upscale",
  "input_resolution": "1024×1024",
  "scale_factor": 2.0, 
  "output_resolution": "2048×2048",
  "batch_optimized": true
}
```
</details>

## 📚 Documentation

### Available Tools

| Tool | Description | Status | Documentation |
|------|-------------|--------|---------------|
| **Resolution Calculator** | Calculate upscaled dimensions with model optimization | ✅ Complete | [Docs](examples/documentation/resolution_calculator.md) |
| **Width Height Selector** | Preset-based dimension selection with 26 curated options | ✅ Complete | [Docs](examples/documentation/width_height_selector.md) |
| **Seed History** | Advanced seed tracking with interactive history management | ✅ Complete | [Docs](examples/documentation/seed_history.md) |
| **Sampler Combo** | Unified sampling configuration with smart recommendations | ✅ Complete | [Docs](examples/documentation/sampler_combo.md) |
| **Batch Image Processor** | Process multiple images with consistent settings | 🚧 Planned | Coming Soon |
| **Advanced Prompt Utilities** | Enhanced prompt manipulation and generation | 🚧 Planned | Coming Soon |

### Technical Specifications

#### Resolution Calculator

**Inputs:**
- `scale_factor` (FLOAT): 1.0-8.0, default 2.0
- `image` (IMAGE, optional): Input image tensor  
- `latent` (LATENT, optional): Input latent tensor

**Outputs:**
- `width` (INT): Calculated target width
- `height` (INT): Calculated target height

**Constraints:**
- All outputs divisible by 8 (ComfyUI requirement)
- Preserves aspect ratio
- Validates input tensors
- Graceful error handling

#### Width Height Selector

**Inputs:**
- `preset` (DROPDOWN): 26 preset options + custom
- `width` (INT): 64-8192, step 8, default 1024
- `height` (INT): 64-8192, step 8, default 1024

**Outputs:**
- `width` (INT): Selected or calculated width
- `height` (INT): Selected or calculated height  

**UI Features:**
- Visual blue swap button in bottom-right corner
- Intelligent preset switching when swapping
- Modern hover effects and cursor feedback

**Preset Categories:**
- SDXL Presets (9): 1024×1024 to 1536×640 (~1MP optimized)
- FLUX Presets (8): 1920×1080 to 1152×1728 (high resolution)
- Ultra-Wide (8): 2560×1080 to 768×2304 (modern ratios)

#### Seed History

**Inputs:**
- `seed` (INT): 0 to 18,446,744,073,709,551,615, default 12345

**Outputs:**
- `seed` (INT): Validated and processed seed value

**UI Features:**
- Interactive history display with timestamps
- Generate random seed button (🎲 Generate)
- Clear history button (🗑️ Clear)
- Auto-hide after 2.5 seconds of inactivity
- Click-to-restore hidden history

**History Management:**
- Maximum 10 entries for optimal performance
- Smart deduplication with 500ms window
- Persistent localStorage storage
- Newest entries displayed first
- Human-readable time formatting (5m ago, 2h ago)

#### Sampler Combo

**Inputs:**
- `sampler_name` (DROPDOWN): Available ComfyUI samplers (euler, dpmpp_2m, etc.)
- `scheduler` (DROPDOWN): Available schedulers (normal, karras, exponential, etc.)
- `steps` (INT): 1-1000, default 20
- `cfg` (FLOAT): 0.0-30.0, default 7.0

**Outputs:**
- `sampler_name` (STRING): Selected sampler algorithm
- `scheduler` (STRING): Selected scheduler algorithm  
- `steps` (INT): Validated step count
- `cfg` (FLOAT): Validated CFG scale

**Features:**
- Smart parameter validation and sanitization
- Sampler-specific recommendations for optimal settings
- Compatibility checking between samplers and schedulers
- Graceful error handling with safe defaults
- Comprehensive tooltips for user guidance

## 🛠️ Development

### Prerequisites

- Python 3.8+
- ComfyUI installation
- PyTorch 2.0+

### Development Setup

```bash
# Clone the repository
git clone https://github.com/ComfyAssets/ComfyUI-KikoTools.git
cd ComfyUI-KikoTools

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -c "
import sys, os
sys.path.insert(0, os.getcwd())
from kikotools.tools.resolution_calculator.node import ResolutionCalculatorNode
import torch

# Quick test
node = ResolutionCalculatorNode()
result = node.calculate_resolution(2.0, image=torch.randn(1, 512, 512, 3))
print(f'✅ Development setup successful! Test result: {result[0]}x{result[1]}')
"
```

### Code Quality

We maintain high code quality standards:

```bash
# Format code
black .

# Lint code  
flake8 .

# Type checking
mypy .

# Run all quality checks
make quality-check  # If Makefile exists
```

### Testing Philosophy

Following **Test-Driven Development (TDD)**:

1. **Write Tests First**: Define expected behavior before implementation
2. **Red-Green-Refactor**: Fail → Pass → Improve cycle
3. **Comprehensive Coverage**: Unit, integration, and scenario testing
4. **Real-World Validation**: Test with actual ComfyUI workflows

```bash
# Test structure
tests/
├── unit/                    # Individual component tests
├── integration/            # ComfyUI workflow tests  
└── fixtures/              # Test data and workflows
```

### Adding New Tools

1. **Plan**: Define tool purpose, inputs, outputs in `plan.md`
2. **Test**: Write comprehensive tests following TDD
3. **Implement**: Build tool logic with proper validation
4. **Integrate**: Create ComfyUI node interface
5. **Document**: Add usage examples and workflows
6. **Validate**: Test in real ComfyUI environment

See our [Contributing Guide](CONTRIBUTING.md) for detailed instructions.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Principles

- **KISS**: Keep It Simple, Stupid
- **Separation of Concerns**: Clear module boundaries
- **DRY**: Don't Repeat Yourself
- **SOLID**: Object-oriented design principles
- **TDD**: Test-driven development

### Reporting Issues

Please use GitHub Issues with:
- ComfyUI version
- Tool/node name
- Expected vs actual behavior
- Minimal reproduction steps
- Error logs if applicable

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🏷️ Tags

`comfyui` `custom-nodes` `image-processing` `ai-tools` `sdxl` `flux` `upscaling` `resolution` `batch-processing` `python` `pytorch`

## 🔗 Links

- **ComfyUI**: [https://github.com/comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- **Documentation**: [examples/documentation/](examples/documentation/)
- **Example Workflows**: [examples/workflows/](examples/workflows/)
- **Issue Tracker**: [GitHub Issues](https://github.com/ComfyAssets/ComfyUI-KikoTools/issues)

## 📈 Stats

- **Nodes**: 4 (Resolution Calculator, Width Height Selector, Seed History, Sampler Combo)
- **Presets**: 26 curated resolution presets
- **Interactive Features**: 2 (Swap Button, History UI)
- **Test Coverage**: 100% (180+ comprehensive tests)
- **Python Version**: 3.8+
- **ComfyUI Compatibility**: Latest
- **Dependencies**: Minimal (PyTorch, NumPy)

---

<div align="center">

**Made with ❤️ for the ComfyUI community**

[⭐ Star this repo](https://github.com/ComfyAssets/ComfyUI-KikoTools) • [🐛 Report Bug](https://github.com/ComfyAssets/ComfyUI-KikoTools/issues) • [💡 Request Feature](https://github.com/ComfyAssets/ComfyUI-KikoTools/issues)

</div>