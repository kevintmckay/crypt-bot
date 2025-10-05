#!/bin/bash
# Validation script - runs all tests

set -e

cd "$(dirname "$0")"

echo "=========================================="
echo "Trend Following Bot - Validation"
echo "=========================================="
echo ""

# Run unit tests
echo "[1/2] Running unit tests..."
./venv/bin/python -m pytest tests/ -v
echo ""

# Run dry test
echo "[2/2] Running dry test..."
./venv/bin/python test_run.py
echo ""

echo "=========================================="
echo "All validation passed!"
echo "=========================================="
