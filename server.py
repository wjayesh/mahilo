from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict
import uvicorn
import asyncio
import uuid

from agent_manager import AgentManager, BaseAgent

app = FastAPI()
agent_manager = AgentManager()

# Store WebSocket connections
websocket_connections: Dict[str, Dict[str, WebSocket]] = {}

# Initialize the main agent
main_agent = BaseAgent("MainAgent", "The primary agent that users interact with")
agent_manager.register_agent(main_agent)
main_agent.activate()

@app.post("/ask")
async def ask_main_agent(question: str):
    response = main_agent.process_message(question)
    return JSONResponse(content=response)

@app.websocket("/ws/{agent_type}")
async def websocket_endpoint(websocket: WebSocket, agent_type: str):
    await websocket.accept()
    
    # Generate a unique ID for this connection
    connection_id = str(uuid.uuid4())
    
    if agent_type not in websocket_connections:
        websocket_connections[agent_type] = {}
    websocket_connections[agent_type][connection_id] = websocket

    try:
        agent = agent_manager.get_agent(agent_type)
        if agent and agent.is_active():
            while True:
                data = await websocket.receive_text()
                response = agent.process_message(data)
                await websocket.send_text(response["response"])
        else:
            await websocket.send_text(f"Agent {agent_type} is not active.")
    except WebSocketDisconnect:
        del websocket_connections[agent_type][connection_id]
        if not websocket_connections[agent_type]:
            del websocket_connections[agent_type]

@app.on_event("startup")
async def startup_event():
    # Start a background task to handle inter-agent communication
    asyncio.create_task(handle_inter_agent_communication())

async def handle_inter_agent_communication():
    while True:
        for agent in agent_manager.get_all_agents():
            if agent.is_active() and agent._queue:
                message = agent._queue.pop(0)
                if agent.TYPE in websocket_connections:
                    for ws in websocket_connections[agent.TYPE].values():
                        await ws.send_text(f"Agent {agent.TYPE}: {message}")
        await asyncio.sleep(1)  # Check every second

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)