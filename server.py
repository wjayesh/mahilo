from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
import asyncio
import uuid

app = FastAPI()

class Message(BaseModel):
    content: str

class Agent:
    def __init__(self, name):
        self.name = name
        self.conversation = []

    async def process_message(self, message):
        # Simulate AI processing
        await asyncio.sleep(1)
        return f"{self.name} received: {message}"

class Dispatcher(Agent):
    def __init__(self):
        super().__init__("Dispatcher")
        self.active_agents = {}

    async def process_message(self, message):
        response = await super().process_message(message)
        if "activate" in message.lower():
            new_agent = self.activate_new_agent(message)
            return f"{response}\nActivated new agent: {new_agent.name}"
        return response

    def activate_new_agent(self, message):
        if "police" in message.lower():
            new_agent = Agent("Police")
        elif "ambulance" in message.lower():
            new_agent = Agent("Ambulance")
        else:
            new_agent = Agent("Generic")
        
        agent_id = str(uuid.uuid4())
        self.active_agents[agent_id] = new_agent
        return new_agent

dispatcher = Dispatcher()

@app.post("/dispatch/")
async def dispatch_message(message: Message):
    # this is where mt agent comes in 
    response = await dispatcher.process_message(message.content)
    return {"response": response}

@app.websocket("/agent/{agent_id}")
async def agent_websocket(websocket: WebSocket, agent_id: str):
    # you check if the agent is active and only then respond
    # otherwise, say the agent is not available.
    
    await websocket.accept()
    if agent_id not in dispatcher.active_agents:
        await websocket.send_text("Invalid agent ID")
        await websocket.close()
        return

    agent = dispatcher.active_agents[agent_id]
    await websocket.send_text(f"Connected to {agent.name}")

    try:
        while True:
            message = await websocket.receive_text()
            response = await agent.process_message(message)
            await websocket.send_text(response)
    except:
        dispatcher.active_agents.pop(agent_id, None)