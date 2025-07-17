#!/bin/bash

echo "Starting MCP Optimization Demo..."
echo "=================================="

# Run the client - it will start MCP servers as needed
echo "Running optimization workflow..."
uv run python client.py

echo "=================================="
echo "Demo completed!"