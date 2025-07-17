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
    mcp.run()