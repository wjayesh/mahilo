# Multi-Agent Dispatcher

This is a simple multi-agent dispatcher that can be used to dispatch tasks to multiple agents as needed. This is an example of the hierarchical agent communication pattern where the dispatcher can talk to and activate all agents as needed but the agents like the plumber and the mold specialist are not aware of each other and only talk to the dispatcher and their respective users (a real plumber and a real mold specialist).

## Getting Started

### Installation and Running the Server

1. Clone the repository:
   ```
   git clone https://github.com/wjayesh/multi-agent.git
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Run the server:
   ```
   cd examples/dispatcher
   python run_server.py
   ```

### Code Explanation

1. The code for the agents is defined in the `templates/centralized` directory.

2. The `run_server.py` file is the entry point for the server. It initializes the agent manager and the WebSocket server and serves the app.

3. The `client.py` in the root repo directory is the entry point for the client. It connects to the server and sends messages to the server.

4. When you run the server, it will start a WebSocket server on `ws://localhost:8000`. You can connect to this server using the CLI client.

5. Connect to your server using the CLI client:
   ```
   python client.py --url http://localhost:8000 --agent-type dispatcher
   ```
   You can connect to the same server using multiple clients to test the system in a real-world scenario where multiple agents need to coordinate their actions.

> [!TIP]
> You don't have to specify the URL if you want to connect to the default server.
