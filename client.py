import asyncio
import websockets
import requests
from typing import Dict, Optional

class Client:
    def __init__(self, url: str, agent_type: Optional[str] = None):
        self.base_url = url
        self.agent_type = agent_type
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None

    async def connect(self):
        if self.agent_type:
            self.websocket = await websockets.connect(f"{self.base_url}/ws/{self.agent_type}")
            asyncio.create_task(self._listen())
        else:
            print("Connected to main agent.")

    async def _listen(self):
        try:
            while True:
                message = await self.websocket.recv()
                print(f"{self.agent_type} message: {message}")
        except websockets.exceptions.ConnectionClosed:
            print(f"Connection to {self.agent_type} closed")

    async def send_message(self, message: str):
        if self.agent_type:
            if not self.websocket:
                await self.connect()
            await self.websocket.send(message)
        else:
            response = requests.post(f"{self.base_url}/ask", json={"question": message})
            print(f"Main agent response: {response.json()['response']}")
            return response.json()

    async def close(self):
        if self.websocket:
            await self.websocket.close()

async def run_client(client: Client):
    await client.connect()
    while True:
        message = input(f"Enter message for {client.agent_type or 'main agent'} (or 'quit' to exit): ")
        if message.lower() == 'quit':
            break
        response = await client.send_message(message)
        if not client.agent_type and response:
            new_agents = set(response.get('activated_agents', []))
            for agent_type in new_agents:
                print(f"New agent activated: {agent_type}")
    await client.close()


# Usage example:
# asyncio.run(run_client(Client("http://localhost:8000")))
# or
# asyncio.run(run_client(Client("ws://localhost:8000", "AgentType1")))