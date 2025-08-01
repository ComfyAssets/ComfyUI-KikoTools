#!/bin/bash
# Run mypy type checking on kikotools package
# This is used as an alternative to pre-commit due to package name issues

set -e

echo "Running mypy type checking..."
cd "$(dirname "$0")/.."

# Run mypy with the configuration
python -m mypy kikotools/ --ignore-missing-imports --no-strict-optional || {
    echo "❌ Mypy type checking failed"
    exit 1
}

echo "✓ Mypy type checking passed"