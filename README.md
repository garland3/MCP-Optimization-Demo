# MCP Optimization Demo

An engineering optimization workflow demonstration using Model Context Protocol (MCP) servers for Design of Experiments (DoE) and data collection simulation.

## Overview

This project demonstrates a distributed optimization workflow where:
- An **optimization server** provides DoE generation and optimization tools
- A **robot server** simulates data collection from experimental designs
- A **client** orchestrates the entire workflow

## Project Structure

```
├── optimization_server.py  # MCP server for DoE and optimization
├── robot_server.py         # MCP server for data collection simulation
├── client.py              # Command-line orchestration script
├── web_server.py           # FastAPI web dashboard server
├── templates/
│   └── index.html          # Web dashboard HTML
├── static/
│   ├── css/style.css       # Dashboard styling
│   └── js/dashboard.js     # Real-time updates JavaScript
├── .env                   # Configuration file
├── run.sh                 # CLI execution script
├── run_web.sh             # Web dashboard script
├── setup.sh               # Project setup script
└── pyproject.toml         # Project dependencies
```

## Installation

This project uses `uv` for Python package management:

```bash
pip install uv
uv sync
```

## Configuration

The `.env` file contains the configuration:

```
BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY="your-openai-api-key"
MODEL_NAME="gpt-4"
```

## Running the Demo

### Option 1: Web Dashboard (Recommended)

Launch the interactive web dashboard:

```bash
./run_web.sh
```

Then open your browser to http://localhost:8080 to:
- Start/stop optimization workflows
- View real-time progress with interactive plots
- Monitor data collection with 2D scatter plots
- Visualize 3D response surfaces after modeling
- See optimization results with predicted optimum points
- Reset the system

### Option 2: Command Line Interface

```bash
./run.sh
```

### Option 3: Manual Execution

```bash
uv run python client.py
```

## Workflow

1. **DoE Generation**: Client requests experimental design points from the optimization server
2. **Data Collection**: For each design point, the client requests measurements from the robot server
3. **Optimization**: Client sends collected data back to optimization server for analysis
4. **Results**: Final optimization results are displayed

## Features

### 🎛️ **Interactive Web Dashboard**
- **Real-time 2D scatter plots** showing data points as they're collected
- **3D response surface visualization** after model fitting
- **Interactive phase indicators** with live progress tracking
- **Tabbed plotting interface** switching between 2D and 3D views
- **Color-coded data points** (DoE points, refinement points, predicted optimum)

### 🔧 **MCP Tools Available**

**Optimization Server:**
- `suggest_doe_points`: Generates full factorial Design of Experiments
- `fit_response_surface`: Fits quadratic response surface model with R² metrics
- `optimize_from_model`: Finds optimal point using gradient descent
- `suggest_refinement_points`: Generates points around predicted optimum

**Robot Server:**
- `collect_measurement`: Simulates measurement collection with sensor noise

### 📊 **Visualization Capabilities**
- **2D Plot**: Design space exploration with differentiated point types
- **3D Surface**: Response surface with data points and predicted optimum
- **Real-time updates** as optimization progresses
- **Interactive controls** for plot switching and exploration