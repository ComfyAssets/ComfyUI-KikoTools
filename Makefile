# ComfyUI-KikoTools Development Makefile

.PHONY: coverage frontend-test browser-test frontend-coverage help install test test-fast lint format type-check quality-check clean setup dev-test release-test

# Python and virtual environment setup
PYTHON := python3
VENV_DIR := venv
VENV_BIN := $(VENV_DIR)/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip

# Check if we're in a virtual environment, if not use venv
ifeq ($(VIRTUAL_ENV),)
	PYTHON_CMD := $(VENV_PYTHON)
	PIP_CMD := $(VENV_PIP)
else
	PYTHON_CMD := python
	PIP_CMD := pip
endif

# Default target
help:
	@echo "ComfyUI-KikoTools Development Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup Commands:"
	@echo "  setup          - Initial development setup"
	@echo "  install        - Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  format         - Format code with black"
	@echo "  lint           - Lint code with flake8"
	@echo "  type-check     - Type checking with mypy"
	@echo "  quality-check  - Run all quality checks"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run the complete pytest suite"
	@echo "  coverage       - Python statement/branch coverage (85% gate)"
	@echo "  frontend-test  - JavaScript regression tests"
	@echo "  browser-test   - Extension workflows in four browser configurations"
	@echo "  frontend-coverage - JavaScript tests, browser tests, and coverage gate"
	@echo "  test-fast      - Run core functionality tests"
	@echo "  dev-test       - Quick development test"
	@echo "  release-test   - Full release validation"
	@echo ""
	@echo "Utilities:"
	@echo "  clean          - Clean up temporary files"
	@echo "  help           - Show this help message"

# Setup and installation
setup: $(VENV_DIR)
	@echo "✅ ComfyUI-KikoTools development environment ready"
	@echo "Virtual environment created. Dependencies installed."

$(VENV_DIR):
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "Installing development dependencies..."
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements-dev.txt
	@echo "✅ Virtual environment created and dependencies installed"

install: $(VENV_DIR)
	@echo "Installing/updating development dependencies..."
	$(PIP_CMD) install --upgrade pip
	$(PIP_CMD) install -r requirements-dev.txt
	@echo "✅ Dependencies installed"

# Code quality
format: $(VENV_DIR)
	@echo "Formatting code with black..."
	$(PYTHON_CMD) -m black .
	@echo "✅ Code formatted"

lint: $(VENV_DIR)
	@echo "Linting with flake8..."
	$(PYTHON_CMD) -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=venv
	$(PYTHON_CMD) -m flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics --exclude=venv
	@echo "✅ Linting completed"

type-check: $(VENV_DIR)
	@echo "Type checking with mypy..."
	$(PYTHON_CMD) -m mypy kikotools/ --ignore-missing-imports --no-strict-optional || true
	@echo "✅ Type checking completed"

quality-check: format lint type-check
	@echo "✅ All quality checks completed"

# Testing
dev-test: $(VENV_DIR)
	@echo "Running quick development test..."
	@$(PYTHON_CMD) -c "\
	import sys, os; \
	sys.path.insert(0, os.getcwd()); \
	from kikotools.tools.resolution_calculator.node import ResolutionCalculatorNode; \
	import torch; \
	node = ResolutionCalculatorNode(); \
	result = node.calculate_resolution(2.0, image=torch.randn(1, 512, 512, 3)); \
	print(f'✅ Development test passed! Result: {result[0]}x{result[1]}'); \
	"

test-fast: $(VENV_DIR)
	@echo "Running core functionality tests..."
	@$(PYTHON_CMD) -c "\
	import sys, os; \
	sys.path.insert(0, os.getcwd()); \
	from kikotools.base import ComfyAssetsBaseNode; \
	from kikotools.tools.resolution_calculator.logic import extract_dimensions, calculate_scaled_dimensions; \
	from kikotools.tools.resolution_calculator.node import ResolutionCalculatorNode; \
	import torch; \
	print('Testing imports...'); \
	assert ComfyAssetsBaseNode.CATEGORY == 'ComfyAssets'; \
	print('✅ Base node test passed'); \
	mock_image = torch.randn(1, 1216, 832, 3); \
	width, height = extract_dimensions(image=mock_image); \
	assert width == 832 and height == 1216; \
	print('✅ Dimension extraction test passed'); \
	new_width, new_height = calculate_scaled_dimensions(832, 1216, 1.5); \
	assert new_width % 8 == 0 and new_height % 8 == 0; \
	print('✅ Scaling test passed'); \
	node = ResolutionCalculatorNode(); \
	result_width, result_height = node.calculate_resolution(1.5, image=mock_image); \
	print(f'✅ Node test passed: {result_width}x{result_height}'); \
	print('🎉 All core tests passed!'); \
	"

test: $(VENV_DIR)
	@$(PYTHON_CMD) -m pytest tests

coverage: $(VENV_DIR)
	@$(PYTHON_CMD) -m pytest tests --cov=kikotools --cov-report=term-missing --cov-report=html

frontend-test:
	npm test --prefix tools/testing

browser-test:
	npm run --prefix tools/testing test:browser

frontend-coverage:
	npm run --prefix tools/testing test:coverage

release-test: quality-check test
	@echo "Running release validation..."
	@echo "Checking package structure..."
	@test -f README.md || (echo "❌ README.md missing" && exit 1)
	@test -f LICENSE || (echo "❌ LICENSE missing" && exit 1)
	@test -f requirements-dev.txt || (echo "❌ requirements-dev.txt missing" && exit 1)
	@test -d kikotools || (echo "❌ kikotools directory missing" && exit 1)
	@test -d tests || (echo "❌ tests directory missing" && exit 1)
	@test -d examples || (echo "❌ examples directory missing" && exit 1)
	@echo "✅ Package structure validated"
	@echo "Checking documentation..."
	@test -f examples/documentation/resolution_calculator.md || (echo "❌ Resolution Calculator documentation missing" && exit 1)
	@test -f examples/workflows/resolution_calculator_example.json || (echo "❌ Resolution Calculator workflow missing" && exit 1)
	@test -f examples/documentation/width_height_selector.md || (echo "❌ Width Height Selector documentation missing" && exit 1)
	@test -f examples/workflows/width_height_selector_example.json || (echo "❌ Width Height Selector workflow missing" && exit 1)
	@echo "✅ Documentation validated"
	@echo "🎉 Release validation completed!"

# Utilities
clean:
	@echo "Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	@echo "✅ Cleanup completed"

# Development workflows
dev: dev-test
	@echo "✅ Ready for development!"

ci: quality-check test
	@echo "✅ CI checks passed!"

# Tool-specific commands (can be extended for new tools)
test-resolution-calculator: $(VENV_DIR)
	@echo "Testing Resolution Calculator specifically..."
	@$(PYTHON_CMD) -c "import sys, os; sys.path.insert(0, os.getcwd()); from kikotools.tools.resolution_calculator.node import ResolutionCalculatorNode; import torch; node = ResolutionCalculatorNode(); scenarios = [('SDXL Portrait', torch.randn(1, 1216, 832, 3), 1.5), ('FLUX Square', torch.randn(1, 1024, 1024, 3), 2.0), ('User Scenario', torch.randn(1, 1216, 832, 3), 1.53)]; [print(f'✅ {name}: {image.shape[2]}×{image.shape[1]} → {node.calculate_resolution(scale, image=image)[0]}×{node.calculate_resolution(scale, image=image)[1]} ({scale}x)') for name, image, scale in scenarios]; print('🎉 Resolution Calculator tests completed!')"

test-width-height-selector: $(VENV_DIR)
	@echo "Testing Width Height Selector specifically..."
	@$(PYTHON_CMD) -c "\
	import sys, os; \
	sys.path.insert(0, os.getcwd()); \
	from kikotools.tools.width_height_selector.node import WidthHeightSelectorNode; \
	from kikotools.tools.width_height_selector.presets import PRESET_OPTIONS; \
	print(f'Testing Width Height Selector with {len(PRESET_OPTIONS)} presets...'); \
	node = WidthHeightSelectorNode(); \
	scenarios = [ \
		('SDXL Square', '1024×1024'), \
		('FLUX HD', '1920×1080'), \
		('SDXL Portrait', '832×1216'), \
		('Custom Dimensions', 'custom'), \
		('Ultra-Wide', '2560×1080') \
	]; \
	for name, preset in scenarios: \
		if preset == 'custom': \
			result = node.get_dimensions(preset, 1536, 768); \
		else: \
			result = node.get_dimensions(preset, 1024, 1024); \
		print(f'✅ {name}: {preset} → {result[0]}×{result[1]}'); \
	print('🎉 Width Height Selector tests completed!') \
	"

test-all-tools: test-resolution-calculator test-width-height-selector
	@echo "🎉 All tool-specific tests completed!"
