import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Response
from typing import Dict, Optional
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
        # Add metrics and traces endpoints
        @self.app.get("/metrics")
        async def get_metrics(agent_id: Optional[str] = None):
            """Get system metrics, optionally filtered by agent"""
            return self.agent_manager.get_agent_metrics(agent_id)
            
        @self.app.get("/traces")
        async def get_traces(
            limit: int = Query(100, description="Maximum number of traces to return"),
            agent_id: Optional[str] = None
        ):
            """Get system traces, optionally filtered by agent"""
            return self.agent_manager.telemetry.get_traces(limit=limit, agent_id=agent_id)

        # Add Prometheus-format metrics endpoint
        @self.app.get("/metrics/prometheus")
        async def get_prometheus_metrics():
            """Get metrics in Prometheus format"""
            metrics = self.agent_manager.get_agent_metrics()
            prometheus_lines = []
            
            # Convert our metrics to Prometheus format
            for key, value in metrics.items():
                if isinstance(value, dict):
                    # Handle nested metrics like processing_time
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, (int, float)):
                            prometheus_lines.append(f"mahilo_{key}_{subkey} {subvalue}")
                else:
                    prometheus_lines.append(f"mahilo_{key} {value}")
            
            return Response(
                content="\n".join(prometheus_lines),
                media_type="text/plain"
            )

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
                
                try:
                    async with websockets.connect(ws_url, extra_headers=headers) as openai_ws:
                        # Add the OpenAI WS to agent's voice connections
                        agent._voice_connections.append(openai_ws)
                        try:
                            await agent._send_session_update(openai_ws)
                            while True:
                                await asyncio.gather(
                                    agent._receive_from_client(websocket, openai_ws),
                                    agent._send_to_client(websocket, openai_ws)
                                )
                        finally:
                            # Remove connection when done
                            if openai_ws in agent._voice_connections:
                                agent._voice_connections.remove(openai_ws)
                except Exception as e:
                    self.console.print(f"[bold red]Error with OpenAI WS connection: {e}[/bold red]")
                    await asyncio.sleep(1)

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
                if agent.is_active():
                    # Get pending messages from broker for this agent
                    pending_messages = self.agent_manager.message_broker.get_pending_messages(agent.name)
                    if pending_messages:
                        websockets = []
                        try:
                            websockets = self.websocket_connections[agent.name].values()
                        except KeyError:
                            # no websockets means no one is listening to this agent. this is fine
                            # but the contact human function will not work.
                            # don't wanna log this because it's inside a continuous loop
                            pass
                        list_websockets = [ws for ws in websockets]
                        await agent.process_queue_message(websockets=list_websockets)
            await asyncio.sleep(1)
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        uvicorn.run(self.app, host=host, port=port)