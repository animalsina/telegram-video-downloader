#!/bin/bash

PROJECT_DIR="./telegram-video-downloader"
VENV_DIR="$PROJECT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Error: virtual environment not exists in $VENV_DIR. Making in progress..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "Check and installation of packages from requirements.txt..."
    pip install --upgrade -r "$PROJECT_DIR/requirements.txt"
else
    echo "requirements.txt file not found, continue without packages installation."
fi

echo "Script Python start..."
python3 "$PROJECT_DIR/run.py"
