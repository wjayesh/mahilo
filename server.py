from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict
import uvicorn
import asyncio
import uuid

from agent_manager import AgentManager, BaseAgent

class ServerManager:
    def __init__(self, agent_manager: AgentManager):
        self.app = FastAPI()
        self.agent_manager = agent_manager
        self.websocket_connections: Dict[str, Dict[str, WebSocket]] = {}

        self._setup_routes()

    def _setup_routes(self):
        @self.app.post("/ask")
        async def ask_main_agent(question: str):
            main_agent = self.agent_manager.get_main_agent()
            # if main_agent is not active, activate it
            if not main_agent.is_active():
                main_agent.activate()
            response = main_agent.process_message(question)
            return JSONResponse(content=response)

        @self.app.websocket("/ws/{agent_type}")
        async def websocket_endpoint(websocket: WebSocket, agent_type: str):
            await websocket.accept()
            
            connection_id = str(uuid.uuid4())
            
            if agent_type not in self.websocket_connections:
                self.websocket_connections[agent_type] = {}
            self.websocket_connections[agent_type][connection_id] = websocket

            try:
                agent = self.agent_manager.get_agent(agent_type)
                if agent and agent.is_active():
                    while True:
                        data = await websocket.receive_text()
                        response = agent.process_message(data)
                        await websocket.send_text(response["response"])
                else:
                    await websocket.send_text(f"Agent {agent_type} is not active.")
            except WebSocketDisconnect:
                del self.websocket_connections[agent_type][connection_id]
                if not self.websocket_connections[agent_type]:
                    del self.websocket_connections[agent_type]

        @self.app.on_event("startup")
        async def startup_event():
            asyncio.create_task(self._handle_inter_agent_communication())

    async def _handle_inter_agent_communication(self):
        while True:
            for agent in self.agent_manager.get_all_agents():
                if agent.is_active() and agent._queue:
                    message = agent._queue.pop(0)
                    if agent.TYPE in self.websocket_connections:
                        for ws in self.websocket_connections[agent.TYPE].values():
                            await ws.send_text(f"Agent {agent.TYPE}: {message}")
            await asyncio.sleep(1)

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        uvicorn.run(self.app, host=host, port=port)