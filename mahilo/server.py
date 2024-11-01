import json
import os
import aiohttp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import uvicorn
import asyncio
import uuid

import websockets

## TODO add instructor

from .agent_manager import AgentManager

class ServerManager:
    def __init__(self, agent_manager: AgentManager):
        self.app = FastAPI()
        self.agent_manager = agent_manager
        self.websocket_connections: Dict[str, Dict[str, WebSocket]] = {}
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", None)
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", None)
        self.key = os.getenv("AZURE_OPENAI_KEY", None)
        self.token_provider = None

        self.agent_manager.populate_can_contact_for_agents()
        self._setup_routes()

    def _setup_routes(self):
        @self.app.websocket("/ws/voice-stream/{agent_type}")
        async def voice_stream_endpoint(websocket: WebSocket, agent_type: str):
            print(f"Received voice stream connection request for agent type: {agent_type}")
            await websocket.accept()
            
            if not all([self.endpoint, self.deployment, self.key]):
                await websocket.send_text("Azure OpenAI credentials not configured. Voice streaming is unavailable.")
                await websocket.close()
                return
            
            connection_id = str(uuid.uuid4())
            
            if agent_type not in self.websocket_connections:
                self.websocket_connections[agent_type] = {}            
            self.websocket_connections[agent_type][connection_id] = websocket

            try:
                agent = self.agent_manager.get_agent(agent_type)
                
                headers = {}
                if self.key is not None:
                    headers = { "api-key": self.key }
                # add params to the url without using urllib
                ws_url = f"{self.endpoint}/openai/realtime?api-version=2024-10-01-preview&deployment={self.deployment}"
                async with websockets.connect(ws_url, extra_headers=headers) as openai_ws:
                    await agent._send_session_update(openai_ws)
                    await asyncio.gather(
                        agent._receive_from_client(websocket, openai_ws),
                        agent._send_to_client(websocket, openai_ws)
                    )

            except WebSocketDisconnect:
                print(f"WebSocket disconnected for agent type: {agent_type}")
                del self.websocket_connections[agent_type][connection_id]
                if not self.websocket_connections[agent_type]:
                    del self.websocket_connections[agent_type]
            except Exception as e:
                print(f"Error in voice_stream_endpoint: {str(e)}")
        
        @self.app.websocket("/ws/{agent_type}")
        async def websocket_endpoint(websocket: WebSocket, agent_type: str):
            print(f"Received WebSocket connection request for agent type: {agent_type}")
            await websocket.accept()
            
            connection_id = str(uuid.uuid4())
            
            if agent_type not in self.websocket_connections:
                print(f"Creating new entry for agent type: {agent_type}")
                self.websocket_connections[agent_type] = {}            
            self.websocket_connections[agent_type][connection_id] = websocket

            try:
                agent = self.agent_manager.get_agent(agent_type)
                print(f"Agent retrieved: {agent}")
                while True:
                    data = await websocket.receive_text()
                    print(f"Received message: {data}")
                    # if the agent is not active, ignore the message
                    if not agent.is_active():
                        print(f"Agent {agent_type} is not active")
                        await websocket.send_text(f"Agent {agent_type} is not active.")
                        continue
                    response = agent.process_message(data)
                    await websocket.send_text(response["response"])
            except WebSocketDisconnect:
                print(f"WebSocket disconnected for agent type: {agent_type}")
                del self.websocket_connections[agent_type][connection_id]
                if not self.websocket_connections[agent_type]:
                    print(f"No connections left for agent type: {agent_type}")
                    del self.websocket_connections[agent_type]
            except Exception as e:
                print(f"Error in websocket_endpoint: {str(e)}")

        @self.app.on_event("startup")
        async def startup_event():
            asyncio.create_task(self._handle_inter_agent_communication())

    async def _handle_inter_agent_communication(self):
        while True:
            for agent in self.agent_manager.get_all_agents():
                if agent.is_active() and agent._queue:
                    message = agent._queue.pop(0)
                    agent_type = agent.TYPE
                    if agent_type in self.websocket_connections:
                        for ws in self.websocket_connections[agent_type].values():
                            print("Sending message to: ", ws)
                            ## TODO log to file
                            await ws.send_text(message)
            await asyncio.sleep(1)

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        uvicorn.run(self.app, host=host, port=port)