#!/usr/bin/env bash
set -e

# Create and activate a local Python 3 venv
python3.7 -m venv venv
source venv/bin/activate

# Ensure latest version of pip (avoids annoying warning notice)
pip install --upgrade pip

# Install requirements
pip install -U -r requirements.txt

echo "* Success: To activate the python venv, run"
echo "    source venv/bin/activate"
