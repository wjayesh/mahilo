# Mahilo: Multi-Agent with Human-in-the-Loop System Framework

[![Mahilo first demo](https://github.com/wjayesh/mahilo/blob/main/assets/yt_thumbnail1.png?raw=true)](https://youtu.be/6RjKJwzsdWY?si=v13lNN3-9RGuhWjh "Mahilo: Multi-Agent with Human-in-the-Loop System Framework")

This project provides a flexible framework for defining and creating multi-agent systems that can each interact with humans while sharing relevant context internally. It allows developers to easily set up complex agent networks for various applications, from customer service to emergency response simulations.

Agents are aware of other agents in the system and can decide to talk to one or more agents based on the current conversation context, simultaneously. The system is designed to make humans more efficient by giving them an assitant that can handle context from multiple agents and help the human stay focused on their specific problem, while surfacing all relevant information on demand.

## Features
![An architecture diagram that shows the different components of the system](https://github.com/wjayesh/mahilo/blob/main/assets/mahilo.png?raw=true)
Above is an architecture diagram that shows the different components of the system in the context of a health emergency scenario. You have three humans talking to their respective agents, which all share information internally.

### TL;DR:
- Easy-to-extend BaseAgent class to create your own agents
- WebSocket-based real-time communication with multiple users simultaneously
- Flexible communication patterns: peer-to-peer and hierarchical (or centralized)
- Control hierarchy in communication via `can_contact` lists: limit what agents can talk to what other agents. 
- Session management for persistent conversations
- CLI client for easy testing and interaction
- Multiple users can connect to the same agent. In emergency situation scenarios, this means multiple police officers can connect to the same dispatcher and receive updates from the dispatcher.
- Agents are only activated when they are needed.


![A three-agent system where a medical advisor is talking about a public health emergency and the agent decides to call the logistics coordinator and the public communication director agents to coordinate the response to the emergency](https://github.com/wjayesh/mahilo/blob/main/assets/health_emergency1.png?raw=true)
Above is an image that shows a three-agent system where a medical advisor is talking about a public health emergency and the agent decides to call the logistics coordinator and the public communication director agents simultaneously to coordinate the response to the emergency.

More information on the features can be found in the [Detailed Features](#detailed-features) section below.


## Getting Started

### 🤘 Quickstart

1. Install the package:
   ```
   pip install mahilo
   ```

2. Export your OpenAI API key:
   ```
   export OPENAI_API_KEY=<your_api_key>
   ```

3. Go to one of the example directories and run the server:
   ```
   cd examples/your_example  # one of dispatcher or health_emergency
   python run_server.py
   ```
   This starts the agent server locally at `http://localhost:8000`.

4. Connect to the server using the CLI client:
   For each of the agents in the system, you can spin up a client to connect to the server.
   ```
   cd mahilo
   python client.py --url http://localhost:8000 --agent-type your_agent_type
   ```
   Run this command in separate terminals for each of the agents and you can then start talking with them.


> [!TIP]
> You dont have to specify the URL if you want to connect to the default server.

### 🧑‍🍳 Building your own agents

1. Define your agents looking at examples in the `templates` directory.

2. Create a run script for your specific use case. See the examples in the `examples` directory.

3. Run your server:
   ```
   python examples/your_example/run_server.py
   ```

4. Connect to your server using the CLI client:
   ```
   python mahilo/client.py --url http://localhost:8000 --agent-type your_agent_type
   ```
   You can connect to the same server using multiple clients to test the system with multiple users. This is useful for testing the system in a real-world scenario where multiple agents need to coordinate their actions.

> [!TIP]
> You dont have to specify the URL if you want to connect to the default server.

## Project Structure

- `agent_manager.py`: Defines the `AgentManager` and `BaseAgent` classes
- `server.py`: Implements the `ServerManager` for handling WebSocket connections
- `session.py`: Manages conversation sessions for each agent
- `client.py`: Provides a CLI client for interacting with the agents
- `templates/`: Contains agent templates for different use cases
- `examples/`: Includes example implementations of multi-agent systems


## Detailed Features

### Index
- [Human-in-the-Loop](#human-in-the-loop)
- [Easy-to-use agent definition system](#easy-to-use-agent-definition-system)
- [WebSocket-based real-time communication](#websocket-based-real-time-communication)
- [Flexible communication patterns: peer-to-peer and hierarchical (or centralized)](#flexible-communication-patterns-peer-to-peer-and-hierarchical-or-centralized)
- [Flexible agent manager for handling multiple agent types](#flexible-agent-manager-for-handling-multiple-agent-types)
- [Session management for persistent conversations](#session-management-for-persistent-conversations)

### Human-in-the-Loop
- The human-in-the-loop is implemented by having the human client connect to each agent in the system.
- The system is designed to make humans more efficient by giving an assitant that can handle context from multiple agents and help the human stay focused on the conversation.
- The agents are aware of what's going on in all the conversations and can help the human get information on demand.
- The human can override the agent's decision to choose an agent for any situation.

### Easy-to-use agent definition system
The BaseAgent class is designed to be subclassed for defining new agents. It comes with:
- tools that allow it to talk to other agents.
- a message queue that stores the history of messages that the agent has received.
- a prompt that tells the agent about the system
- a method to process a message which takes care of the context and the conversation history.
- a session object that stores the conversation history in a file for persistence.

### WebSocket-based real-time communication
- The server uses FastAPI's WebSocket support to handle real-time communication between the agents and the client. This allows for natural, two-way conversations that can be used for a variety of applications, from customer service to emergency response simulations.
- The server keeps track of all connected agents and the messages they receive from other agents and coordinates the conversation between them.

### Flexible communication patterns: peer-to-peer and hierarchical (or centralized)
- In a peer-to-peer communication pattern, agents are connected directly to each other and can call each other directly.
- This is useful when a complex problem needs to be tackled by a combination of one or more agents. The example directory contains a health emergency scenario where a medical advisor, a logistics coordinator and a public communication director each independently decide on a course of action.
- In a hierarchical (or centralized) communication pattern, agents are connected to a single dispatcher agent. This is useful for a group of agents who need to coordinate their actions with a single leader. The example directory contains a dispatch scenario where the dispatcher coordinates the actions of a plumber and mold removal specialist agent.

### Flexible agent manager for handling multiple agent types
- The `AgentManager` class is designed to manage multiple agent types, allowing for easy addition and removal of agents. 
- Agent manager makes sure that an agent can only talk to agents that are on its `can_contact` list.

### Session management for persistent conversations
- The `Session` class is designed to manage conversation sessions for each agent. It stores the conversation history in a file for persistence.
- The messages from the queue or the shared context are not stored to avoid duplication and redundancy.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

