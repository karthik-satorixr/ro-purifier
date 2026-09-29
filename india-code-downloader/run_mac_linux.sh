#!/bin/bash
cd "$(dirname "$0")"
echo "Installing required packages (first time only)..."
python3 -m pip install -r requirements.txt
echo
python3 download_legislation.py
