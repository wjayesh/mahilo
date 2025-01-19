from mahilo import AgentManager, ServerManager
from mahilo.templates.peer2peer.logistics_coordinator import LogisticsCoordinator
from mahilo.templates.peer2peer.medical_advisor import MedicalAdvisor
from mahilo.templates.peer2peer.public_communications_director import PublicCommunicationsDirector

# initialize the agent manager
manager = AgentManager()

# create the agents
medical_advisor = MedicalAdvisor()
logistics_coordinator = LogisticsCoordinator()
public_communications_director = PublicCommunicationsDirector()

# register the agents to the manager
manager.register_agent(logistics_coordinator)
manager.register_agent(public_communications_director)
manager.register_agent(medical_advisor)

# activate the medical advisor as the starting point of the conversation
medical_advisor.activate()

# initialize the server manager
server = ServerManager(manager)

# run the server
def main():
    server.run()

if __name__ == "__main__":
    main()
