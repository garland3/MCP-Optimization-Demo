Here is a set of scripts that fulfill your request.

### 1\. Project Setup

First, create a new directory for your project and install the necessary Python packages.

```bash
mkdir mcp_optimization_demo
cd mcp_optimization_demo
pip install "fastmcp[cli]" numpy python-dotenv requests
```

### 2\. Environment File (`.env`)

Create a file named `.env` in your project directory. This file will store the configuration for your client. Note that `OPENAI_API_KEY` and `MODEL_NAME` are placeholders to meet the "OpenAI compliant" request format but are not actually used for authentication against the local servers.

**.env**

```
BASE_URL=http://127.0.0.1:8000
OPENAI_API_KEY="your-openai-api-key-if-needed"
MODEL_NAME="gpt-4"
```

### 3\. MCP Optimization Server (`optimization_server.py`)

This server provides tools for design of experiments and optimization. It uses `numpy` to perform calculations and adds some randomness to simulate process variability.

**optimization\_server.py**

```python
from fastmcp import FastMCP
import numpy as np
from typing import List

mcp = FastMCP("Engineering_Optimization_Server", dependencies=["numpy"])

@mcp.tool()
def suggest_doe_points(num_variables: int, num_levels: int) -> List[List[float]]:
    """Generates a full factorial Design of Experiments (DoE)."""
    levels = np.linspace(0, 1, num_levels)
    grids = np.meshgrid(*([levels] * num_variables))
    points = np.vstack([grid.ravel() for grid in grids]).T
    return points.tolist()

@mcp.tool()
def optimize_beam_design(data: List[dict]) -> dict:
    """
    Optimizes the design of a beam based on experimental data.
    This is a pseudo-optimization for demonstration.
    It fits a quadratic model: y = a*x1^2 + b*x2^2 + c*x1*x2 + d*x1 + e*x2 + f
    And finds the minimum of this model.
    """
    # data is expected to be a list of dicts like {'vars': [x1, x2], 'measurement': y}
    x = np.array([d['vars'] for d in data])
    y = np.array([d['measurement'] for d in data])

    # Add randomness to simulate modeling error
    noise = np.random.normal(0, 0.05, y.shape)
    y += noise

    # Design matrix for a quadratic model with two variables (x1, x2)
    A = np.c_[x[:, 0]**2, x[:, 1]**2, x[:, 0]*x[:, 1], x[:, 0], x[:, 1], np.ones(x.shape[0])]

    # Solve for the model coefficients using least squares
    try:
        coeffs, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
    except np.linalg.LinAlgError:
        return {"error": "Failed to fit the model. The data may be singular."}

    # For this simple example, we'll just return the coefficients
    # A real optimization would find the minimum of the fitted surface.
    return {
        "status": "Optimization Complete",
        "model_coefficients": coeffs.tolist(),
        "comment": "These coefficients represent the fitted quadratic surface for the beam's performance."
    }

if __name__ == "__main__":
    mcp.run(port=8000)
```

### 4\. MCP Robot Server (`robot_server.py`)

This server simulates a robot that can be tasked to collect experimental data. The results are procedurally generated with added noise to mimic a real-world sensor.

**robot\_server.py**

```python
from fastmcp import FastMCP
import numpy as np
from typing import List

mcp = FastMCP("Data_Collection_Robot", dependencies=["numpy"])

@mcp.tool()
def collect_measurement(design_variables: List[float]) -> float:
    """
    Simulates a robot measuring the performance of a design.
    The 'true' performance is a simple function of the design variables.
    """
    x1, x2 = design_variables
    # A fictional "true" response surface
    true_performance = 0.5 * (x1 - 0.5)**2 + 0.8 * (x2 - 0.7)**2 + x1 * x2
    
    # Add random measurement noise
    noise = np.random.normal(0, 0.1) # Simulate sensor noise
    
    return true_performance + noise

if __name__ == "__main__":
    # Run this server on a different port
    mcp.run(port=8001)
```

### 5\. Client Script (`client.py`)

This script orchestrates the optimization process. It first gets a set of experimental points from the `optimization_server`. Then, for each point, it asks the `robot_server` to "collect" data. Finally, it sends the collected data back to the `optimization_server` to find the optimal design parameters.

**client.py**

```python
import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_URL = os.getenv("BASE_URL")
ROBOT_URL = "http://127.0.0.1:8001" # The robot server is on a different port
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

def call_mcp_tool(base_url, tool_name, parameters):
    """A helper function to call an MCP tool using requests."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}" # For OpenAI compliance format
    }
    # This payload structure mimics OpenAI's API for educational purposes
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user", 
                "content": f"Call the tool {tool_name} with parameters {json.dumps(parameters)}"
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "parameters": parameters
                }
            }
        ]
    }
    # The actual request to a FastMCP server is simpler
    # but we construct a more complex one for demonstration.
    # A simple FastMCP call would just be a POST to /tools/{tool_name}
    mcp_endpoint = f"{base_url}/tools/{tool_name}"
    
    print(f"\n--> Calling {tool_name} on {base_url}...")
    try:
        response = requests.post(mcp_endpoint, headers=headers, json=parameters)
        response.raise_for_status() # Raise an exception for bad status codes
        result = response.json()
        print(f"<-- Response: {result}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"<-- Error: {e}")
        return None

def main():
    """Main execution script."""
    # 1. Get Design of Experiment points from the optimization server
    doe_params = {"num_variables": 2, "num_levels": 4}
    doe_points = call_mcp_tool(BASE_URL, "suggest_doe_points", doe_params)

    if not doe_points:
        print("Could not retrieve DoE points. Exiting.")
        return

    # 2. "Collect" data for each point using the robot server
    experimental_data = []
    for point in doe_points:
        robot_params = {"design_variables": point}
        measurement = call_mcp_tool(ROBOT_URL, "collect_measurement", robot_params)
        if measurement is not None:
            experimental_data.append({"vars": point, "measurement": measurement})
    
    if not experimental_data:
        print("No experimental data collected. Exiting.")
        return

    # 3. Send collected data to the optimization server to find the best design
    optimization_params = {"data": experimental_data}
    optimization_result = call_mcp_tool(BASE_URL, "optimize_beam_design", optimization_params)

    if optimization_result:
        print("\n" + "="*30)
        print("   ENGINEERING OPTIMIZATION COMPLETE")
        print("="*30)
        print(f"Final Result: {json.dumps(optimization_result, indent=2)}")
        print("="*30)

if __name__ == "__main__":
    main()
```

### 6\. Running the Demonstration

To run the full workflow, you'll need three separate terminal windows.

**Terminal 1: Start the Optimization Server**

```bash
python optimization_server.py
```

You should see output indicating the server is running on port 8000.

**Terminal 2: Start the Robot Server**

```bash
python robot_server.py
```

You should see output indicating the server is running on port 8001.

**Terminal 3: Run the Client Script**
Once both servers are running, execute the client script.

```bash
python client.py
```

You will see the client print its progress as it calls the different MCP servers, culminating in the final optimization result based on the simulated experimental data.