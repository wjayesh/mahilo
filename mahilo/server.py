import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import uvicorn
import asyncio
import uuid

import websockets

from rich.console import Console
from rich.traceback import install

## TODO add instructor

from .agent_manager import AgentManager

class ServerManager:
    def __init__(self, agent_manager: AgentManager):
        self.app = FastAPI()
        self.agent_manager = agent_manager
        self.websocket_connections: Dict[str, Dict[str, WebSocket]] = {}
        self.key = os.getenv("OPENAI_API_KEY", None)
        self.token_provider = None

        self.agent_manager.populate_can_contact_for_agents()
        self._setup_routes()

        self.console = Console()
        install()  # This enables rich traceback formatting for exceptions

    def _setup_routes(self):
        @self.app.websocket("/ws/voice-stream/{agent_name}")
        async def voice_stream_endpoint(websocket: WebSocket, agent_name: str):
            await websocket.accept()
            
            agent = self.agent_manager.get_agent(agent_name)
            if not agent:
                self.console.print(f"[bold red]⛔  Agent not found:[/bold red] [green]{agent_name}[/green]")
                await websocket.send_text(f"Error: Agent '{agent_name}' is not registered with the server")
                await websocket.close(1008)  # Using 1008 (Policy Violation) status code
                return

            self.console.print(f"[bold blue]🎙️ New voice stream connection[/bold blue] for agent: [green]{agent_name}[/green]")

            if not self.key:
                await websocket.send_text("OpenAI credentials not configured. Voice streaming is unavailable.")
                await websocket.close(1008)  # Using 1008 (Policy Violation) status code
                return
            
            connection_id = str(uuid.uuid4())
            
            if agent_name not in self.websocket_connections:
                self.websocket_connections[agent_name] = {}            
            self.websocket_connections[agent_name][connection_id] = websocket

            try:
                headers = {}
                if self.key is not None:
                    headers = {
                        "Authorization": f"Bearer {self.key}",
                        "OpenAI-Beta": "realtime=v1"
                    }
                # add params to the url without using urllib
                ws_url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
                async with websockets.connect(ws_url, extra_headers=headers) as openai_ws:
                    await agent._send_session_update(openai_ws)
                    await asyncio.gather(
                        agent._receive_from_client(websocket, openai_ws),
                        agent._send_to_client(websocket, openai_ws)
                    )

            except WebSocketDisconnect:
                self.console.print(f"[bold yellow]⚠️  WebSocket disconnected[/bold yellow] for agent: [green]{agent_name}[/green]")
                del self.websocket_connections[agent_name][connection_id]
                if not self.websocket_connections[agent_name]:
                    del self.websocket_connections[agent_name]
            except Exception as e:
                self.console.print(f"[bold red]⛔  Error in voice stream:[/bold red] {str(e)}", style="red")
        
        @self.app.websocket("/ws/{agent_name}")
        async def websocket_endpoint(websocket: WebSocket, agent_name: str):
            await websocket.accept()

            agent = self.agent_manager.get_agent(agent_name)
            if not agent:
                self.console.print(f"[bold red]⛔  Agent not found:[/bold red] [green]{agent_name}[/green]")
                await websocket.send_text(f"Error: Agent '{agent_name}' is not registered with the server")
                await websocket.close(1008)
                return
            
            self.console.print(f"[bold blue]🔌 New WebSocket connection[/bold blue] for agent: [green]{agent_name}[/green]")
            
            connection_id = str(uuid.uuid4())
            
            if agent_name not in self.websocket_connections:
                self.websocket_connections[agent_name] = {}            
            self.websocket_connections[agent_name][connection_id] = websocket

            try:
                print(f"Agent retrieved: {agent}")
                while True:
                    data = await websocket.receive_text()
                    self.console.print(f"[dim blue]📨 Received message for agent:[/dim blue] [green]{agent_name}[/green]: [dim]{data}[/dim]")
                    # if the agent is not active, ignore the message
                    if not agent.is_active():
                        self.console.print(f"[bold yellow]⚠️  Agent[/bold yellow] [green]{agent_name}[/green] [bold yellow]is not active[/bold yellow]")
                        await websocket.send_text(f"Agent {agent_name} is not active.")
                        continue
                    response = await agent.process_chat_message(data, websockets=[websocket])
                    await websocket.send_text(response["response"])
            except WebSocketDisconnect:
                self.console.print(f"[bold yellow]⚠️  WebSocket disconnected[/bold yellow] for agent: [green]{agent_name}[/green]")
                del self.websocket_connections[agent_name][connection_id]
                if not self.websocket_connections[agent_name]:
                    print(f"No connections left for agent: {agent_name}")
                    del self.websocket_connections[agent_name]
            except Exception as e:
                self.console.print(f"[bold red]⛔  Error in websocket:[/bold red] {str(e)}", style="red")

        @self.app.on_event("startup")
        async def startup_event():
            asyncio.create_task(self._handle_inter_agent_communication())

        @self.app.websocket("/health")
        async def health_check(websocket: WebSocket):
            await websocket.accept()
            await websocket.close()

    async def _handle_inter_agent_communication(self):
        while True:
            for agent in self.agent_manager.get_all_agents():
                if agent.is_active() and agent._queue:
                    message = agent._queue.pop(0)
                    websockets = []
                    try:
                        websockets = self.websocket_connections[agent.name].values()
                    except KeyError:
                        self.console.print(f"[bold yellow]⚠️  No WebSocket connections found for agent:[/bold yellow] [green]{agent.name}[/green]")
                    list_websockets = [ws for ws in websockets]
                    await agent.process_queue_message(message, websockets=list_websockets)
            await asyncio.sleep(1)
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        uvicorn.run(self.app, host=host, port=port)