from mahilo.agent_manager import AgentManager
from mahilo.server import ServerManager
from mahilo.templates.historical_event_simulator.historical_figure_agent import HistoricalFigureAgent
from mahilo.templates.historical_event_simulator.context_agent import ContextAgent
from mahilo.templates.historical_event_simulator.what_if_agent import WhatIfAgent

# Example: Cuban Missile Crisis scenario
EVENT_NAME = "Cuban Missile Crisis"
FIGURE_NAME = "JFK"  # Or "Nikita Khrushchev" for a different perspective

manager = AgentManager()

kennedy = HistoricalFigureAgent(FIGURE_NAME, EVENT_NAME)  # Create Kennedy agent
context = ContextAgent(EVENT_NAME)
what_if = WhatIfAgent(EVENT_NAME)

manager.register_agent(kennedy)
manager.register_agent(context)
manager.register_agent(what_if)

kennedy.activate()  # Activate the historical figure agent

server = ServerManager(manager)

def main():
    server.run()

if __name__ == "__main__":
    main()
