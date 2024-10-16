# Multi-Agent 911 Emergency Response System

This is a multi-agent system designed to handle 911 emergency calls. It demonstrates a coordinated emergency response pattern where specialized agents collaborate to address various types of emergencies. The system includes an Emergency Dispatcher, a Police Proxy Agent, and a Medical Proxy Agent, all working together to manage different aspects of emergency response.

## System Overview

![911 Emergency Response System](../../assets/scenario_911.png)

The system consists of three main agents:

1. Emergency Dispatcher: The first point of contact for emergency calls, responsible for assessing the situation and coordinating with other agents.
2. Police Proxy Agent: Communicates with real police officers and relays law enforcement advice and information.
3. Medical Proxy Agent: Communicates with real medical professionals and relays medical advice and assistance.

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
   cd examples/scenario_911
   python run_server.py
   ```

### Code Explanation

1. The code for the agents is defined in the `mahilo/templates/scenario_911` directory.

2. The `run_server.py` file is the entry point for the server. It initializes the agent manager, creates and registers the agents, and starts the server.

