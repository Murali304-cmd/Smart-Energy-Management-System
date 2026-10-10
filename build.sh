#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "==> Upgrading pip..."
python -m pip install --upgrade pip

echo "==> Installing CPU-optimized PyTorch..."
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu

echo "==> Installing project dependencies..."
python -m pip install -r requirements.txt

echo "==> Build complete!"
