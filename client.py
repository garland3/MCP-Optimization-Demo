import asyncio
import json
import subprocess
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def call_mcp_tool(server_params, tool_name, parameters):
    """Call an MCP tool using stdio transport."""
    print(f"\n--> Calling {tool_name}...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                result = await session.call_tool(tool_name, parameters)
                print(f"<-- Response: {result.content}")
                
                # Extract the actual result from MCP response
                if result.content and len(result.content) > 0:
                    return result.content[0].text if hasattr(result.content[0], 'text') else result.content[0]
                return None
                
    except Exception as e:
        print(f"<-- Error: {e}")
        return None

async def collect_data_at_points(robot_server, points):
    """Helper function to collect measurements at given design points."""
    experimental_data = []
    for i, point in enumerate(points):
        print(f"  Collecting data at point {i+1}/{len(points)}: {point}")
        robot_params = {"design_variables": point}
        measurement = await call_mcp_tool(robot_server, "collect_measurement", robot_params)
        if measurement is not None:
            # Parse measurement if it's a string
            if isinstance(measurement, str):
                try:
                    measurement = float(measurement)
                except ValueError:
                    print(f"Failed to parse measurement: {measurement}")
                    continue
            experimental_data.append({"vars": point, "measurement": measurement})
    return experimental_data

async def main():
    """Two-phase optimization: DoE exploration + model-based optimization."""
    print("="*50)
    print("   ENGINEERING OPTIMIZATION WORKFLOW")
    print("="*50)
    
    # Server parameters
    opt_server = StdioServerParameters(
        command="uv", 
        args=["run", "python", "optimization_server.py"]
    )
    
    robot_server = StdioServerParameters(
        command="uv", 
        args=["run", "python", "robot_server.py"]
    )
    
    # ===============================================
    # PHASE 1: DESIGN OF EXPERIMENTS (EXPLORATION)
    # ===============================================
    print("\nPHASE 1: Design of Experiments - Exploring Design Space")
    print("-" * 50)
    
    # Generate DoE points for initial exploration
    doe_params = {"num_variables": 2, "num_levels": 4}
    doe_points = await call_mcp_tool(opt_server, "suggest_doe_points", doe_params)

    if not doe_points:
        print("Could not retrieve DoE points. Exiting.")
        return

    # Parse the DoE points if they're in string format
    if isinstance(doe_points, str):
        try:
            doe_points = json.loads(doe_points)
        except json.JSONDecodeError:
            print("Failed to parse DoE points. Exiting.")
            return

    print(f"Generated {len(doe_points)} DoE points for initial exploration")
    
    # Collect data at all DoE points
    print("Collecting experimental data...")
    doe_data = await collect_data_at_points(robot_server, doe_points)
    
    if not doe_data:
        print("No experimental data collected. Exiting.")
        return

    print(f"Collected {len(doe_data)} data points from DoE phase")
    
    # ===============================================  
    # PHASE 2: RESPONSE SURFACE MODELING
    # ===============================================
    print("\nPHASE 2: Response Surface Modeling")
    print("-" * 50)
    
    # Fit response surface model to DoE data
    rsm_params = {"data": doe_data}
    rsm_result = await call_mcp_tool(opt_server, "fit_response_surface", rsm_params)

    if not rsm_result:
        print("Failed to fit response surface model. Exiting.")
        return

    if isinstance(rsm_result, str):
        try:
            rsm_result = json.loads(rsm_result)
        except json.JSONDecodeError:
            print(f"Response Surface Result: {rsm_result}")
            return

    print(f"Response Surface Model Fitted:")
    print(f"  R² = {rsm_result.get('r_squared', 'N/A'):.4f}")
    print(f"  Model: {rsm_result.get('model_equation', 'N/A')}")
    
    # ===============================================
    # PHASE 3: MODEL-BASED OPTIMIZATION  
    # ===============================================
    print("\nPHASE 3: Model-Based Optimization")
    print("-" * 50)
    
    # Find optimal point using the fitted model
    opt_params = {"model_coefficients": rsm_result["model_coefficients"]}
    opt_result = await call_mcp_tool(opt_server, "optimize_from_model", opt_params)

    if not opt_result:
        print("Failed to optimize from model. Exiting.")
        return

    if isinstance(opt_result, str):
        try:
            opt_result = json.loads(opt_result)
        except json.JSONDecodeError:
            print(f"Optimization Result: {opt_result}")
            return

    predicted_optimal = opt_result["optimal_point"]
    predicted_value = opt_result["optimal_value"]
    
    print(f"Predicted optimal point: {predicted_optimal}")
    print(f"Predicted optimal value: {predicted_value:.4f}")
    
    # ===============================================
    # PHASE 4: REFINEMENT AROUND OPTIMUM
    # ===============================================
    print("\nPHASE 4: Local Refinement Around Predicted Optimum")
    print("-" * 50)
    
    # Generate refinement points around the predicted optimum
    ref_params = {"optimal_point": predicted_optimal, "num_points": 5, "radius": 0.1}
    refinement_points = await call_mcp_tool(opt_server, "suggest_refinement_points", ref_params)
    
    if isinstance(refinement_points, str):
        try:
            refinement_points = json.loads(refinement_points)
        except json.JSONDecodeError:
            refinement_points = []
    
    if refinement_points:
        print(f"Generated {len(refinement_points)} refinement points around optimum")
        
        # Collect data at refinement points
        print("Collecting refinement data...")
        refinement_data = await collect_data_at_points(robot_server, refinement_points)
        
        # Find the best point from refinement data
        if refinement_data:
            best_point = min(refinement_data, key=lambda x: x['measurement'])
            print(f"Best refinement point: {best_point['vars']}")
            print(f"Best measured value: {best_point['measurement']:.4f}")
            
            # Compare with prediction
            print(f"Prediction accuracy: {abs(predicted_value - best_point['measurement']):.4f}")
    
    # ===============================================
    # FINAL RESULTS
    # ===============================================
    print("\n" + "="*50)
    print("   OPTIMIZATION WORKFLOW COMPLETE")
    print("="*50)
    
    print(f"Total data points collected: {len(doe_data) + len(refinement_data if 'refinement_data' in locals() else [])}")
    print(f"Response surface R²: {rsm_result.get('r_squared', 'N/A'):.4f}")
    print(f"Model-predicted optimum: {predicted_optimal}")
    print(f"Model-predicted value: {predicted_value:.4f}")
    
    if 'best_point' in locals():
        print(f"Experimentally verified optimum: {best_point['vars']}")
        print(f"Experimentally verified value: {best_point['measurement']:.4f}")
    
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())