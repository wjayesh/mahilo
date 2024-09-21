from agent_manager import AgentManager
from server import ServerManager
from templates.centralized.dispatcher import Dispatcher
from templates.centralized.plumber import Plumber
from templates.centralized.mold_specialist import MoldSpecialist

# initialize the agent manager
manager = AgentManager()

# create the agents
dispatcher = Dispatcher()
mold_specialist = MoldSpecialist()
plumber = Plumber()

# register the agents to the manager
manager.register_agent(dispatcher)
manager.register_agent(mold_specialist)
manager.register_agent(plumber)

# activate the dispatcher as the starting point of the conversation
dispatcher.activate()

# initialize the server manager
server = ServerManager(manager)

# run the server
def main():
    server.run()

if __name__ == "__main__":
    main()
