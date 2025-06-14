# Contributing to ComfyUI-KikoTools

We love contributions! ComfyUI-KikoTools is built by the community, for the community. This guide will help you get started with contributing to our collection of essential ComfyUI tools.

## 🌟 Ways to Contribute

### 🐛 Bug Reports

- Found a bug? Please [open an issue](https://github.com/ComfyAssets/ComfyUI-KikoTools/issues)
- Include ComfyUI version, tool name, and reproduction steps
- Screenshots and error logs are super helpful!

### 💡 Feature Requests

- Have an idea for a new tool? [Start a discussion](https://github.com/ComfyAssets/ComfyUI-KikoTools/discussions)
- Describe the use case and expected behavior
- Check existing tools to avoid duplication

### 🔧 Code Contributions

- Fix bugs, improve performance, add new tools
- Follow our development principles (see below)
- All contributions must include tests

### 📚 Documentation

- Improve README, add examples, write tutorials
- Update tool documentation in `examples/documentation/`
- Create example workflows in `examples/workflows/`

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- ComfyUI installation (for testing)
- Git knowledge
- Basic understanding of PyTorch tensors

### Development Setup

1. **Fork and Clone**

   ```bash
   git clone https://github.com/YOUR_USERNAME/ComfyUI-KikoTools.git
   cd ComfyUI-KikoTools
   ```

2. **Create Virtual Environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Verify Setup**

   ```bash
   python -c "
   import sys, os
   sys.path.insert(0, os.getcwd())
   from kikotools.tools.resolution_calculator.node import ResolutionCalculatorNode
   import torch

   node = ResolutionCalculatorNode()
   result = node.calculate_resolution(2.0, image=torch.randn(1, 512, 512, 3))
   print(f'✅ Setup successful! Test result: {result[0]}x{result[1]}')
   "
   ```

## 🏗️ Development Principles

We follow these principles to maintain high code quality:

### KISS (Keep It Simple, Stupid)

- Single responsibility per tool
- Simple, intuitive interfaces
- Minimal dependencies

### Separation of Concerns

```
tool_name/
├── logic.py      # Pure functions, no ComfyUI dependencies
├── node.py       # ComfyUI interface only
└── __init__.py   # Module exports
```

### DRY (Don't Repeat Yourself)

- Shared functionality goes in `base/`
- Reusable utilities in `base/utils.py`
- Common validation patterns

### SOLID Principles

- **S**ingle Responsibility: Each class has one reason to change
- **O**pen/Closed: Open for extension, closed for modification
- **L**iskov Substitution: Subclasses are substitutable for base classes
- **I**nterface Segregation: Minimal, focused interfaces
- **D**ependency Inversion: Depend on abstractions, not concretions

## 🧪 Test-Driven Development (TDD)

We use TDD for all new features:

### 1. Write Tests First

```python
def test_new_feature_behavior():
    """Test what the feature should do before implementing it"""
    # Arrange
    input_data = create_test_input()
    expected_output = calculate_expected_result()

    # Act
    actual_output = new_feature_function(input_data)

    # Assert
    assert actual_output == expected_output
```

### 2. Run Tests (Should Fail)

```bash
python -c "import sys; sys.path.insert(0, '.'); from tests.unit.test_new_feature import *; test_new_feature_behavior()"
```

### 3. Implement Minimal Code

Write just enough code to make the test pass.

### 4. Refactor and Expand

- Add error handling
- Optimize performance
- Add comprehensive validation
- Ensure divisible-by-8 constraints

### 5. Integration Testing

Test the complete workflow in a ComfyUI-like environment.

## 🛠️ Adding a New Tool

Follow this step-by-step process:

### Step 1: Planning

1. **Create Issue**: Describe the tool's purpose and requirements
2. **Update plan.md**: Add detailed specifications
3. **Design Interface**: Define inputs, outputs, and constraints

### Step 2: Project Structure

```bash
# Create tool directory
mkdir -p kikotools/tools/your_tool_name

# Create files
touch kikotools/tools/your_tool_name/__init__.py
touch kikotools/tools/your_tool_name/logic.py
touch kikotools/tools/your_tool_name/node.py

# Create tests
touch tests/unit/tools/test_your_tool_name.py
```

### Step 3: Write Tests (TDD)

```python
# tests/unit/tools/test_your_tool_name.py
import pytest
import torch
from kikotools.tools.your_tool_name.logic import your_main_function
from kikotools.tools.your_tool_name.node import YourToolNode

class TestYourToolLogic:
    def test_basic_functionality(self):
        # Test core logic here
        pass

    def test_error_handling(self):
        # Test edge cases and errors
        pass

class TestYourToolNode:
    def test_comfyui_interface(self):
        # Test ComfyUI integration
        pass
```

### Step 4: Implement Logic

```python
# kikotools/tools/your_tool_name/logic.py
import torch
from typing import Tuple, Optional

def your_main_function(input_tensor: torch.Tensor, param: float) -> Tuple[int, int]:
    """
    Pure function implementing the core logic

    Args:
        input_tensor: Input tensor from ComfyUI
        param: Tool-specific parameter

    Returns:
        Tuple of results

    Raises:
        ValueError: If validation fails
    """
    # Implement logic here
    pass
```

### Step 5: Create ComfyUI Node

```python
# kikotools/tools/your_tool_name/node.py
from ...base import ComfyAssetsBaseNode
from .logic import your_main_function

class YourToolNode(ComfyAssetsBaseNode):
    """ComfyUI node for Your Tool"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "param": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 10.0}),
            },
            "optional": {
                "input_tensor": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("result1", "result2")
    FUNCTION = "execute_tool"

    def execute_tool(self, param, input_tensor=None):
        try:
            self.validate_inputs(param=param, input_tensor=input_tensor)
            return your_main_function(input_tensor, param)
        except Exception as e:
            self.handle_error(f"Tool execution failed: {str(e)}", e)
```

### Step 6: Register Tool

```python
# kikotools/tools/your_tool_name/__init__.py
from .node import YourToolNode
__all__ = ["YourToolNode"]

# Update kikotools/__init__.py
from .tools.your_tool_name import YourToolNode

NODE_CLASS_MAPPINGS = {
    "YourTool": YourToolNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "YourTool": "Your Tool Name",
}
```

### Step 7: Documentation

```markdown
# examples/documentation/your_tool_name.md

# Your Tool Name

## Overview

Brief description of what the tool does.

## Inputs

- param (FLOAT): Description of parameter

## Outputs

- result1 (INT): Description of first output
- result2 (INT): Description of second output

## Use Cases

1. Use case 1
2. Use case 2

## Examples

Example workflows and usage patterns.
```

### Step 8: Testing and Validation

```bash
# Run your tests
python -c "import sys; sys.path.insert(0, '.'); [run your test functions]"

# Test integration
python -c "from kikotools.tools.your_tool_name import YourToolNode; print('✅ Integration successful')"

# Code quality
black kikotools/tools/your_tool_name/
flake8 kikotools/tools/your_tool_name/
```

## 📋 Pull Request Process

### Before Submitting

- [ ] All tests pass locally
- [ ] Code follows our style guidelines
- [ ] Documentation is updated
- [ ] Example workflows included (if applicable)

### PR Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New tool
- [ ] Enhancement
- [ ] Documentation update

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist

- [ ] Code follows project style
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

### Review Process

1. **Automated Checks**: CI runs tests and quality checks
2. **Code Review**: Maintainer reviews code and provides feedback
3. **Testing**: Manual testing in ComfyUI environment
4. **Merge**: After approval, changes are merged to main

## 🎨 Code Style Guidelines

### Python Style

- **Formatting**: Use `black` (line length: 127)
- **Linting**: Follow `flake8` guidelines
- **Type Hints**: Use type annotations for all functions
- **Docstrings**: Google-style docstrings for all public functions

### Example Code Style

```python
from typing import Tuple, Optional
import torch

def calculate_dimensions(
    input_tensor: torch.Tensor,
    scale_factor: float
) -> Tuple[int, int]:
    """
    Calculate scaled dimensions from input tensor.

    Args:
        input_tensor: Input image or latent tensor
        scale_factor: Scaling factor to apply

    Returns:
        Tuple of (width, height) as integers

    Raises:
        ValueError: If input validation fails
    """
    if scale_factor <= 0:
        raise ValueError(f"Scale factor must be positive, got {scale_factor}")

    # Implementation here
    return width, height
```

### File Organization

```python
# Standard library imports
import os
import sys
from typing import Tuple, Optional

# Third-party imports
import torch
import numpy as np

# Local imports
from ...base import ComfyAssetsBaseNode
from .logic import helper_function
```

## 🐛 Debugging Guidelines

### Common Issues

1. **Import Errors**: Check `sys.path` and relative imports
2. **Tensor Shape Issues**: Validate input tensor dimensions
3. **ComfyUI Integration**: Ensure proper INPUT_TYPES format
4. **Memory Issues**: Test with various image sizes

### Debugging Tools

```python
# Debug tensor shapes
print(f"Tensor shape: {tensor.shape}")
print(f"Tensor dtype: {tensor.dtype}")

# Debug ComfyUI interface
input_types = YourNode.INPUT_TYPES()
print(f"Input types: {input_types}")

# Debug calculations
result = your_function(test_input)
print(f"Result: {result}, type: {type(result)}")
```

## 📊 Performance Guidelines

### Optimization Priorities

1. **Correctness**: Always prioritize correct results
2. **Memory Efficiency**: Minimize tensor copying
3. **Speed**: Optimize hot paths
4. **Compatibility**: Support various tensor sizes

### Performance Testing

```python
import time
import torch

def benchmark_function():
    large_tensor = torch.randn(1, 2048, 2048, 3)

    start_time = time.time()
    result = your_function(large_tensor)
    end_time = time.time()

    print(f"Processing time: {end_time - start_time:.3f}s")
    print(f"Memory usage: {torch.cuda.memory_allocated() / 1024**2:.1f}MB")
```

## 🤝 Community Guidelines

### Be Respectful

- Use welcoming and inclusive language
- Respect different viewpoints and experiences
- Focus on what's best for the community

### Be Constructive

- Provide helpful feedback in reviews
- Suggest improvements rather than just pointing out problems
- Help others learn and grow

### Be Patient

- Maintainers are volunteers with limited time
- New contributors may need extra guidance
- Complex features take time to implement properly

## ❓ Getting Help

### Documentation

- **README.md**: Project overview and quick start
- **examples/documentation/**: Tool-specific documentation

### Community

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **ComfyUI Discord**: Community chat (mention our tools)

### Maintainers

- Review pull requests and issues
- Provide guidance on architecture decisions
- Help with complex technical problems

## 🎉 Recognition

Contributors are recognized in several ways:

- **README.md**: Listed in contributors section
- **Release Notes**: Mentioned in relevant releases
- **GitHub**: Automatic contribution tracking
- **Community**: Recognition in ComfyUI community

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to ComfyUI-KikoTools! Together, we're building essential tools that make ComfyUI workflows more powerful and efficient. 🚀
