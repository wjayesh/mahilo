from mahilo import AgentManager, ServerManager
from mahilo.templates.scenario_911.dispatcher import EmergencyDispatcher
from mahilo.templates.scenario_911.police import PoliceProxyAgent
from mahilo.templates.scenario_911.medic import MedicalProxyAgent

# initialize the agent manager
manager = AgentManager()

# create the agents
emergency_dispatcher = EmergencyDispatcher()
police_proxy = PoliceProxyAgent()
medical_proxy = MedicalProxyAgent()

# register the agents to the manager
manager.register_agent(emergency_dispatcher)
manager.register_agent(police_proxy)
manager.register_agent(medical_proxy)

# activate the emergency dispatcher as the starting point of the conversation
emergency_dispatcher.activate()

# initialize the server manager
server = ServerManager(manager)

# run the server
def main():
    server.run()

if __name__ == "__main__":
    main()
