#!/bin/bash

echo "MCP Optimization Demo Setup"
echo "=========================="

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    pip install uv
    if [ $? -ne 0 ]; then
        echo "Failed to install uv. Please install pip first."
        exit 1
    fi
else
    echo "uv is already installed"
fi

# Sync dependencies
echo "Installing project dependencies..."
uv sync

if [ $? -ne 0 ]; then
    echo "Failed to install dependencies"
    exit 1
fi

# Check if .env file exists and has API key
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found"
    echo "Please create .env file with your OpenAI API key"
elif grep -q "your-openai-api-key" .env; then
    echo "Warning: Please update your OpenAI API key in .env file"
fi

# Make scripts executable
echo "Making scripts executable..."
chmod +x run.sh
chmod +x setup.sh

echo "=========================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update your OpenAI API key in .env file"
echo "2. Run the demo with: ./run.sh"
echo "=========================="