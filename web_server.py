import asyncio
import json
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pathlib import Path
import uvicorn

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP Optimization Dashboard")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Store optimization state
optimization_state = {
    "phase": "idle",
    "progress": 0,
    "current_point": 0,
    "total_points": 0,
    "data_points": [],
    "model_results": {},
    "optimization_results": {},
    "messages": []
}

# WebSocket connections
connected_clients: List[WebSocket] = []

async def broadcast_update(message: Dict[str, Any]):
    """Broadcast updates to all connected WebSocket clients."""
    if connected_clients:
        message_str = json.dumps(message)
        disconnected = []
        for client in connected_clients:
            try:
                await client.send_text(message_str)
            except:
                disconnected.append(client)
        
        # Remove disconnected clients
        for client in disconnected:
            connected_clients.remove(client)

async def call_mcp_tool(server_params, tool_name, parameters):
    """Call an MCP tool using stdio transport."""
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, parameters)
                
                if result.content and len(result.content) > 0:
                    return result.content[0].text if hasattr(result.content[0], 'text') else result.content[0]
                return None
                
    except Exception as e:
        await broadcast_update({
            "type": "error",
            "message": f"Error calling {tool_name}: {str(e)}"
        })
        return None

async def collect_data_at_points(robot_server, points):
    """Helper function to collect measurements at given design points."""
    experimental_data = []
    for i, point in enumerate(points):
        await broadcast_update({
            "type": "data_collection",
            "point_index": i + 1,
            "total_points": len(points),
            "point": point,
            "message": f"Collecting data at point {i+1}/{len(points)}"
        })
        
        robot_params = {"design_variables": point}
        measurement = await call_mcp_tool(robot_server, "collect_measurement", robot_params)
        if measurement is not None:
            if isinstance(measurement, str):
                try:
                    measurement = float(measurement)
                except ValueError:
                    continue
            
            data_point = {"vars": point, "measurement": measurement}
            experimental_data.append(data_point)
            
            await broadcast_update({
                "type": "data_collected",
                "point": point,
                "measurement": measurement,
                "data_point": data_point
            })
    
    return experimental_data

async def run_optimization():
    """Run the complete optimization workflow."""
    global optimization_state
    
    logger.info("Starting optimization workflow")
    
    try:
        # Reset state
        optimization_state = {
            "phase": "starting",
            "progress": 0,
            "current_point": 0,
            "total_points": 0,
            "data_points": [],
            "model_results": {},
            "optimization_results": {},
            "messages": []
        }
        
        await broadcast_update({
            "type": "phase_change",
            "phase": "starting",
            "message": "Starting optimization workflow..."
        })
        
        # Server parameters
        opt_server = StdioServerParameters(
            command="uv", 
            args=["run", "python", "optimization_server.py"]
        )
        
        robot_server = StdioServerParameters(
            command="uv", 
            args=["run", "python", "robot_server.py"]
        )
        
        # Phase 1: Design of Experiments
        optimization_state["phase"] = "doe"
        await broadcast_update({
            "type": "phase_change",
            "phase": "doe",
            "message": "Phase 1: Design of Experiments - Exploring Design Space"
        })
        
        doe_params = {"num_variables": 2, "num_levels": 4}
        doe_points = await call_mcp_tool(opt_server, "suggest_doe_points", doe_params)
        
        if isinstance(doe_points, str):
            doe_points = json.loads(doe_points)
        
        optimization_state["total_points"] = len(doe_points)
        
        await broadcast_update({
            "type": "doe_generated",
            "points": doe_points,
            "message": f"Generated {len(doe_points)} DoE points"
        })
        
        # Collect DoE data
        doe_data = await collect_data_at_points(robot_server, doe_points)
        optimization_state["data_points"] = doe_data
        
        # Phase 2: Response Surface Modeling
        optimization_state["phase"] = "modeling"
        await broadcast_update({
            "type": "phase_change",
            "phase": "modeling",
            "message": "Phase 2: Response Surface Modeling"
        })
        
        rsm_params = {"data": doe_data}
        rsm_result = await call_mcp_tool(opt_server, "fit_response_surface", rsm_params)
        
        if isinstance(rsm_result, str):
            rsm_result = json.loads(rsm_result)
        
        optimization_state["model_results"] = rsm_result
        
        await broadcast_update({
            "type": "model_fitted",
            "model": rsm_result,
            "message": f"Response Surface Model Fitted (R² = {rsm_result.get('r_squared', 0):.4f})"
        })
        
        # Phase 3: Model-Based Optimization
        optimization_state["phase"] = "optimization"
        await broadcast_update({
            "type": "phase_change",
            "phase": "optimization",
            "message": "Phase 3: Model-Based Optimization"
        })
        
        opt_params = {"model_coefficients": rsm_result["model_coefficients"]}
        opt_result = await call_mcp_tool(opt_server, "optimize_from_model", opt_params)
        
        if isinstance(opt_result, str):
            opt_result = json.loads(opt_result)
        
        optimization_state["optimization_results"] = opt_result
        
        await broadcast_update({
            "type": "optimization_complete",
            "result": opt_result,
            "message": f"Predicted optimum found: {opt_result['optimal_point']}"
        })
        
        # Phase 4: Refinement
        optimization_state["phase"] = "refinement"
        await broadcast_update({
            "type": "phase_change",
            "phase": "refinement",
            "message": "Phase 4: Local Refinement Around Predicted Optimum"
        })
        
        ref_params = {
            "optimal_point": opt_result["optimal_point"], 
            "num_points": 5, 
            "radius": 0.1
        }
        refinement_points = await call_mcp_tool(opt_server, "suggest_refinement_points", ref_params)
        
        if isinstance(refinement_points, str):
            refinement_points = json.loads(refinement_points)
        
        refinement_data = await collect_data_at_points(robot_server, refinement_points)
        
        if refinement_data:
            best_point = min(refinement_data, key=lambda x: x['measurement'])
            
            await broadcast_update({
                "type": "refinement_complete",
                "best_point": best_point,
                "refinement_data": refinement_data,
                "message": f"Best experimental point: {best_point['vars']}, value: {best_point['measurement']:.4f}"
            })
        
        # Complete
        optimization_state["phase"] = "complete"
        await broadcast_update({
            "type": "workflow_complete",
            "phase": "complete",
            "message": "Optimization workflow completed successfully!",
            "summary": {
                "total_points": len(doe_data) + len(refinement_data),
                "r_squared": rsm_result.get('r_squared', 0),
                "predicted_optimum": opt_result["optimal_point"],
                "predicted_value": opt_result["optimal_value"],
                "experimental_optimum": best_point['vars'] if 'best_point' in locals() else None,
                "experimental_value": best_point['measurement'] if 'best_point' in locals() else None
            }
        })
        
        logger.info("Optimization workflow completed successfully")
        
    except Exception as e:
        logger.error(f"Optimization workflow failed: {str(e)}")
        optimization_state["phase"] = "error"
        await broadcast_update({
            "type": "error",
            "message": f"Optimization failed: {str(e)}"
        })

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the main dashboard page."""
    html_path = Path("templates/index.html")
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text())
    else:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>MCP Optimization Dashboard</title></head>
        <body>
        <h1>MCP Optimization Dashboard</h1>
        <p>Dashboard template not found. Please create templates/index.html</p>
        </body>
        </html>
        """)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    global optimization_state
    
    await websocket.accept()
    connected_clients.append(websocket)
    logger.info(f"WebSocket client connected. Total clients: {len(connected_clients)}")
    
    # Send current state to new client
    try:
        await websocket.send_text(json.dumps({
            "type": "state_update",
            "state": optimization_state
        }))
    except Exception as e:
        logger.error(f"Error sending initial state: {e}")
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.info(f"Received WebSocket message: {message}")
            
            if message.get("action") == "start_optimization":
                logger.info("Starting optimization from WebSocket request")
                asyncio.create_task(run_optimization())
            elif message.get("action") == "reset":
                logger.info("Resetting system from WebSocket request")
                optimization_state = {
                    "phase": "idle",
                    "progress": 0,
                    "current_point": 0,
                    "total_points": 0,
                    "data_points": [],
                    "model_results": {},
                    "optimization_results": {},
                    "messages": []
                }
                await broadcast_update({
                    "type": "reset_complete",
                    "message": "System reset successfully"
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        if websocket in connected_clients:
            connected_clients.remove(websocket)

@app.get("/api/state")
async def get_state():
    """Get current optimization state."""
    return optimization_state

if __name__ == "__main__":
    uvicorn.run("web_server:app", host="0.0.0.0", port=8080, reload=True)