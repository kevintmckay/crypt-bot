#!/bin/bash
# Setup script for trend-following bot

set -e

echo "Setting up Trend Following Bot..."
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

# Activate and install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run validation: ./validate.sh"
echo "  2. Run dry test: ./venv/bin/python test_run.py"
echo "  3. Run unit tests: ./venv/bin/python -m pytest tests/ -v"
