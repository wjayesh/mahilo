import asyncio
import websockets
import requests

active_agents = set()
websocket_connections = {}

async def connect_to_agent(agent_type):
    websocket = await websockets.connect(f"ws://localhost:8000/ws/{agent_type}")
    websocket_connections[agent_type] = websocket
    asyncio.create_task(listen_to_agent(agent_type, websocket))

async def listen_to_agent(agent_type, websocket):
    try:
        while True:
            message = await websocket.recv()
            print(f"{agent_type} message: {message}")
    except websockets.exceptions.ConnectionClosed:
        print(f"Connection to {agent_type} closed")
        del websocket_connections[agent_type]

async def main():
    global active_agents

    while True:
        question = input("Enter your question (or 'quit' to exit): ")
        if question.lower() == 'quit':
            break

        # Interact with the main agent
        response = requests.post("http://localhost:8000/ask", json={"question": question})
        print(f"Main agent response: {response.json()['response']}")

        # Check for new active agents
        new_active_agents = set(response.json().get('activated_agents', []))
        new_agents = new_active_agents - active_agents
        active_agents = new_active_agents

        # Connect to new agents
        for agent_type in new_agents:
            if agent_type not in websocket_connections:
                await connect_to_agent(agent_type)

    # Close all WebSocket connections
    for websocket in websocket_connections.values():
        await websocket.close()

if __name__ == "__main__":
    asyncio.run(main())