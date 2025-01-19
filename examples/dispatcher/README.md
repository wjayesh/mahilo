# Multi-Agent Dispatcher

This is a simple multi-agent dispatcher that can be used to dispatch tasks to multiple agents as needed. This is an example of the hierarchical agent communication pattern where the dispatcher can talk to and activate all agents as needed but the agents like the plumber and the mold specialist are not aware of each other and only talk to the dispatcher and their respective users (a real plumber and a real mold specialist).

## Getting Started

### Installation and Running the Server

1. Install mahilo:
   ```bash
   pip install mahilo
   ```

2. Run the server:
   ```bash
   cd examples/dispatcher
   python run_server.py
   ```

### Code Explanation

1. The code for the agents is defined in the `templates/centralized` directory.

2. The `run_server.py` file is the entry point for the server. It initializes the agent manager and the WebSocket server and serves the app:
   ```python
   from mahilo import AgentManager, ServerManager
   from mahilo.templates.centralized.dispatcher import Dispatcher
   from mahilo.templates.centralized.plumber import Plumber
   from mahilo.templates.centralized.mold_specialist import MoldSpecialist

   # initialize and setup agents
   manager = AgentManager()
   # ... rest of the setup
   ```

3. When you run the server, it will start a WebSocket server on `localhost:8000`. You can connect to this server using the mahilo CLI.

4. Connect to your server using the CLI:
   ```bash
   # Connect to the dispatcher
   mahilo connect --agent-name dispatcher

   # In another terminal, connect to the plumber
   mahilo connect --agent-name plumber

   # In another terminal, connect to the mold specialist
   mahilo connect --agent-name mold_specialist
   ```

> [!TIP]
> You don't have to specify the URL if you want to connect to the default server at localhost:8000.
