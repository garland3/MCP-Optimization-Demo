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
def fit_response_surface(data: List[dict]) -> dict:
    """
    Fits a quadratic response surface model to experimental data.
    Returns model coefficients and goodness of fit metrics.
    """
    # data is expected to be a list of dicts like {'vars': [x1, x2], 'measurement': y}
    x = np.array([d['vars'] for d in data])
    y = np.array([d['measurement'] for d in data])

    # Design matrix for a quadratic model with two variables (x1, x2)
    # Model: y = a*x1^2 + b*x2^2 + c*x1*x2 + d*x1 + e*x2 + f
    A = np.c_[x[:, 0]**2, x[:, 1]**2, x[:, 0]*x[:, 1], x[:, 0], x[:, 1], np.ones(x.shape[0])]

    # Solve for the model coefficients using least squares
    try:
        coeffs, residuals, rank, s = np.linalg.lstsq(A, y, rcond=None)
        
        # Calculate R-squared
        y_pred = A @ coeffs
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
    except np.linalg.LinAlgError:
        return {"error": "Failed to fit the model. The data may be singular."}

    return {
        "status": "Response Surface Model Fitted",
        "model_coefficients": coeffs.tolist(),
        "r_squared": float(r_squared),
        "num_data_points": len(data),
        "model_equation": "y = a*x1² + b*x2² + c*x1*x2 + d*x1 + e*x2 + f",
        "coefficient_names": ["a (x1²)", "b (x2²)", "c (x1*x2)", "d (x1)", "e (x2)", "f (intercept)"]
    }

@mcp.tool()
def optimize_from_model(model_coefficients: List[float], bounds: List[List[float]] = None) -> dict:
    """
    Finds the optimal point using the fitted response surface model.
    Uses gradient descent to find the minimum of the quadratic surface.
    """
    if bounds is None:
        bounds = [[0.0, 1.0], [0.0, 1.0]]  # Default bounds for x1 and x2
    
    coeffs = np.array(model_coefficients)
    
    def objective_function(x):
        """Quadratic model: y = a*x1^2 + b*x2^2 + c*x1*x2 + d*x1 + e*x2 + f"""
        x1, x2 = x
        return coeffs[0]*x1**2 + coeffs[1]*x2**2 + coeffs[2]*x1*x2 + coeffs[3]*x1 + coeffs[4]*x2 + coeffs[5]
    
    def gradient(x):
        """Gradient of the quadratic model"""
        x1, x2 = x
        dx1 = 2*coeffs[0]*x1 + coeffs[2]*x2 + coeffs[3]
        dx2 = 2*coeffs[1]*x2 + coeffs[2]*x1 + coeffs[4]
        return np.array([dx1, dx2])
    
    # Simple gradient descent optimization
    x = np.array([0.5, 0.5])  # Start from center
    learning_rate = 0.1
    max_iterations = 100
    tolerance = 1e-6
    
    for i in range(max_iterations):
        grad = gradient(x)
        x_new = x - learning_rate * grad
        
        # Apply bounds constraints
        x_new[0] = np.clip(x_new[0], bounds[0][0], bounds[0][1])
        x_new[1] = np.clip(x_new[1], bounds[1][0], bounds[1][1])
        
        if np.linalg.norm(x_new - x) < tolerance:
            break
            
        x = x_new
    
    optimal_value = objective_function(x)
    
    return {
        "status": "Optimization Complete",
        "optimal_point": x.tolist(),
        "optimal_value": float(optimal_value),
        "iterations": i + 1,
        "converged": i < max_iterations - 1
    }

@mcp.tool()
def suggest_refinement_points(optimal_point: List[float], num_points: int = 5, radius: float = 0.1) -> List[List[float]]:
    """
    Suggests additional sampling points around the predicted optimum for refinement.
    Uses a small radius around the optimal point for local exploration.
    """
    center = np.array(optimal_point)
    points = []
    
    # Add the optimal point itself
    points.append(optimal_point)
    
    # Generate points in a circle around the optimum
    for i in range(num_points - 1):
        angle = 2 * np.pi * i / (num_points - 1)
        offset = radius * np.array([np.cos(angle), np.sin(angle)])
        point = center + offset
        
        # Ensure points are within bounds [0, 1]
        point = np.clip(point, 0.0, 1.0)
        points.append(point.tolist())
    
    return points

if __name__ == "__main__":
    mcp.run()