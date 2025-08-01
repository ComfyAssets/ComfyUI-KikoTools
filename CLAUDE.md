# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ComfyUI-KikoTools is a planned modular collection of custom ComfyUI nodes that will provide essential tools missing from the standard ComfyUI release. All nodes will be grouped under "ComfyAssets" in the ComfyUI interface. The project is designed for extensibility, allowing new tools to be added easily while maintaining clean separation of concerns.

**Current Status**: Project is in initial planning phase. Only documentation and licensing files exist.

## Architecture

### Design Principles
- **Modular Design**: Each tool is a separate, self-contained module
- **ComfyAssets Grouping**: All nodes appear under the "ComfyAssets" category
- **Test-Driven Development**: Every tool includes comprehensive tests
- **Clean Interfaces**: Standardized input/output patterns across tools

### Core Components
- **Tool Registry**: Central registration system for all KikoTools nodes
- **Base Classes**: Shared functionality for consistent tool behavior
- **Individual Tools**: Self-contained modules for specific functionality

### Current Tools

#### 1. Resolution Calculator (First Tool)
- **Purpose**: Calculate upscale resolution from image or latent inputs
- **Inputs**: 
  - Image or Latent tensor
  - Scale factor (1, 2, 3, 1.2, 1.5, 2.0)
- **Outputs**: 
  - Width (INT)
  - Height (INT)
- **Target Models**: Flux and SDXL optimized
- **Use Case**: Connect calculated dimensions to upscaler nodes

## Technology Stack

- **Backend**: Python with ComfyUI node patterns
- **Node Framework**: ComfyUI INPUT_TYPES, RETURN_TYPES, execute() patterns
- **Testing**: pytest with ComfyUI test fixtures
- **Code Quality**: black, flake8, mypy
- **Integration**: ComfyUI execution queue and tensor systems

## Development Commands

**Note**: These commands are planned for when the project structure is implemented.

### Initial Setup
```bash
# Create basic project structure
mkdir -p kikotools/{base,tools} tests/{unit,integration,fixtures} scripts examples

# Create entry point files
touch __init__.py kikotools/__init__.py
```

### Code Quality (Future)
```bash
# Format Python code
black .

# Python linting
flake8 .

# Type checking
mypy .
```

### Testing (Future TDD Workflow)
```bash
# Run all tests
pytest tests/

# Run tests for specific tool
pytest tests/unit/tools/test_{tool_name}.py

# Test coverage
pytest --cov=kikotools tests/
```

## Project Structure (Planned)

**Current State**: Only `CLAUDE.md` and `LICENSE` files exist.

**Planned Structure**:
```
├── __init__.py                 # ComfyUI node registration entry point
├── kikotools/                  # Main package
│   ├── __init__.py            # Package initialization and tool registry
│   ├── base/                  # Base classes and shared utilities
│   │   ├── __init__.py
│   │   ├── base_node.py       # Base node class with ComfyAssets grouping
│   │   └── utils.py           # Shared utility functions
│   ├── tools/                 # Individual tool implementations
│   │   ├── __init__.py
│   │   ├── resolution_calculator/  # First planned tool
│   │   │   ├── __init__.py
│   │   │   ├── node.py        # ResolutionCalculatorNode implementation
│   │   │   └── logic.py       # Core calculation logic
│   │   └── template/          # Template for new tools
│   │       ├── __init__.py
│   │       ├── node.py
│   │       └── logic.py
├── tests/                     # Comprehensive test suite (TDD approach)
│   ├── __init__.py
│   ├── conftest.py           # pytest fixtures and ComfyUI test setup
│   ├── unit/                 # Unit tests for individual components
│   │   ├── test_base_node.py
│   │   └── tools/
│   │       └── test_resolution_calculator.py
│   ├── integration/          # ComfyUI integration tests
│   │   ├── test_node_registration.py
│   │   └── test_workflow_execution.py
│   └── fixtures/             # Test data and workflow files
│       ├── workflows/        # .json workflow files for testing
│       ├── images/          # Test images
│       └── latents/         # Test latent tensors
├── scripts/                  # Development automation
│   ├── create_tool.py       # Tool template generator
│   ├── register_tool.py     # Tool registration helper
│   └── validate_nodes.py    # Node validation script
├── examples/                 # Usage examples and demonstrations
│   ├── workflows/           # Example workflow .json files
│   └── documentation/       # Usage documentation per tool
└── requirements-dev.txt     # Development dependencies
```

## Key ComfyUI Integration Points

### Node Registration Pattern
```python
# Each tool follows this pattern in kikotools/tools/{tool_name}/node.py
class ResolutionCalculatorNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scale_factor": ("FLOAT", {"default": 2.0, "min": 1.0, "max": 8.0, "step": 0.1}),
            },
            "optional": {
                "image": ("IMAGE",),
                "latent": ("LATENT",),
            }
        }
    
    RETURN_TYPES = ("INT", "INT")
    RETURN_NAMES = ("width", "height")
    FUNCTION = "calculate_resolution"
    CATEGORY = "ComfyAssets"  # All tools use this category
    
    def calculate_resolution(self, scale_factor, image=None, latent=None):
        # Implementation here
        pass
```

### Base Node Class
- Provides consistent "ComfyAssets" categorization
- Standardizes error handling and logging
- Implements common validation patterns
- Ensures consistent return type handling

### Tool Registry System
- Automatic discovery of tools in `kikotools/tools/`
- Dynamic node registration during ComfyUI startup
- Version compatibility checking
- Dependency validation

## Test-Driven Development (TDD) Workflow

### 1. Write Tests First
```python
# tests/unit/tools/test_resolution_calculator.py
def test_resolution_calculator_with_image():
    """Test resolution calculation with image input."""
    # Arrange
    node = ResolutionCalculatorNode()
    test_image = create_test_image(512, 512)  # fixture
    scale_factor = 2.0
    
    # Act
    width, height = node.calculate_resolution(scale_factor, image=test_image)
    
    # Assert
    assert width == 1024
    assert height == 1024

def test_resolution_calculator_with_latent():
    """Test resolution calculation with latent input."""
    # Similar pattern for latent inputs
    pass
```

### 2. Run Tests (Should Fail)
```bash
pytest tests/unit/tools/test_resolution_calculator.py -v
```

### 3. Implement Minimal Code
```python
# kikotools/tools/resolution_calculator/logic.py
def calculate_upscale_resolution(input_tensor, scale_factor):
    """Calculate new resolution based on input and scale factor."""
    # Minimal implementation to pass tests
    pass
```

### 4. Refactor and Expand
- Add error handling
- Optimize for Flux/SDXL specific requirements
- Add comprehensive validation
- Implement edge case handling

### 5. Integration Testing
```python
# tests/integration/test_workflow_execution.py
def test_resolution_calculator_in_workflow():
    """Test resolution calculator in full ComfyUI workflow."""
    workflow = load_test_workflow("resolution_calculator_example.json")
    result = execute_comfyui_workflow(workflow)
    assert result.success
```

## Tool-Specific Implementation Notes

### Resolution Calculator
- **Input Validation**: Handle both image and latent tensors
- **Scale Factors**: Support integer (1, 2, 3) and float (1.2, 1.5, 2.0) multipliers
- **Model Optimization**: Consider Flux and SDXL specific resolution requirements
- **Output Format**: Integer width/height suitable for upscaler node connections
- **Error Handling**: Graceful handling of invalid inputs or edge cases

### Future Tools (Planned)
- Batch Image Processor
- Advanced Prompt Utilities
- Model Management Tools
- Custom Sampling Methods

## Development Workflow

### Adding a New Tool
1. **Plan**: Define tool purpose, inputs, outputs, and test cases
2. **Generate**: Use `python scripts/create_tool.py --name "NewTool"`
3. **Test**: Write comprehensive tests following TDD principles
4. **Implement**: Build tool logic with proper ComfyUI integration
5. **Register**: Add tool to registry and validate registration
6. **Document**: Update examples and documentation
7. **Validate**: Test in real ComfyUI environment with actual workflows

### Code Quality Standards
- **Type Hints**: Full type annotation for all functions
- **Documentation**: Docstrings for all public methods and classes
- **Testing**: Minimum 90% test coverage for all tools
- **Linting**: Pass all flake8 and mypy checks
- **Formatting**: Auto-formatted with black

### Release Process
1. Run full test suite: `pytest tests/`
2. Validate in ComfyUI: `python scripts/validate_nodes.py`
3. Update version numbers and changelog
4. Create example workflows demonstrating new features
5. Update ComfyUI-Manager compatibility metadata

## Critical Implementation Notes

### ComfyUI Compatibility
- Follow ComfyUI tensor format conventions
- Implement proper memory management for large tensors
- Handle ComfyUI execution context correctly
- Ensure compatibility with ComfyUI's automatic typing system

### Performance Considerations
- Optimize for real-time workflow execution
- Minimize memory allocation during processing
- Cache expensive computations when appropriate
- Profile performance with typical Flux/SDXL workflows

### User Experience
- Clear, descriptive node names and parameter labels
- Helpful tooltips and parameter descriptions
- Consistent visual styling within ComfyAssets group
- Robust error messages with actionable guidance

### Extensibility
- Plugin architecture for easy tool addition
- Shared utilities for common operations
- Consistent API patterns across all tools
- Future-proof design for ComfyUI updates
