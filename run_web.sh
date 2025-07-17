#!/bin/bash

echo "Starting MCP Optimization Web Dashboard..."
echo "=========================================="
echo "Dashboard will be available at: http://localhost:8080"
echo "Press Ctrl+C to stop the server"
echo "=========================================="

uv run python web_server.py