from mahilo.agent_manager import AgentManager
from mahilo.server import ServerManager
from mahilo.templates.historical_event_simulator.historical_figure_agent import HistoricalFigureAgent
from mahilo.templates.historical_event_simulator.context_agent import ContextAgent
from mahilo.templates.historical_event_simulator.what_if_agent import WhatIfAgent
import argparse


SCENARIOS = {
    "cuban_missile_crisis": {
        "event_name": "Cuban Missile Crisis",
        "figure_name": "John F. Kennedy",
        "agent_type": "john_f._kennedy_agent"
    },
    "partition_of_india": {
        "event_name": "Partition of India",
        "figure_name": "Mahatma Gandhi",  # Or "Muhammad Ali Jinnah", "Jawaharlal Nehru", "Lord Mountbatten"
        "agent_type": "mahatma_gandhi_agent"
    },
    "fall_of_the_mughal_empire": {
        "event_name": "Fall of the Mughal Empire",
        "figure_name": "Aurangzeb", # Or "Bahadur Shah Zafar"
        "agent_type": "aurangzeb_agent"
    },
    "roman_empire": {
        "event_name": "Reign of Caesar",
        "figure_name": "Julius Caesar",
        "agent_type": "julius_caesar_agent"
    }
}


def main(scenario_key):
    if scenario_key not in SCENARIOS:
        raise ValueError(f"Invalid scenario key. Available scenarios: {', '.join(SCENARIOS.keys())}")

    scenario = SCENARIOS[scenario_key]
    EVENT_NAME = scenario["event_name"]
    FIGURE_NAME = scenario["figure_name"]
    AGENT_TYPE = scenario["agent_type"]

    manager = AgentManager()

    figure_agent = HistoricalFigureAgent(FIGURE_NAME, EVENT_NAME)
    context = ContextAgent(EVENT_NAME)
    what_if = WhatIfAgent(EVENT_NAME)

    manager.register_agent(figure_agent)
    manager.register_agent(context)
    manager.register_agent(what_if)

    figure_agent.activate()

    server = ServerManager(manager)
    server.run()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run historical event simulator.')
    parser.add_argument('scenario', choices=SCENARIOS.keys(), help='Choose a historical scenario.')
    args = parser.parse_args()
    main(args.scenario)
