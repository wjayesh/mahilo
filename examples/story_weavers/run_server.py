from mahilo.agent_manager import AgentManager
from mahilo.server import ServerManager
from mahilo.templates.story_weavers.story_weaver_agent import StoryWeaverAgent
import argparse

# Example usage:
# python run_server.py jayesh arunjoy ritvi
# This will create jayesh_weaver, arunjoy_weaver, and ritvi_weaver agents

# initialize the agent manager
manager = AgentManager()

def main(agent_names):
    # create and register agents
    agents = []
    for name in agent_names:
        agent = StoryWeaverAgent(type=f'{name}_weaver')
        manager.register_agent(agent)
        agents.append(agent)
    
    # activate all agents
    for agent in agents:
        agent.activate()

    # initialize and run server
    server = ServerManager(manager)
    server.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run story weaver server with specified agents')
    parser.add_argument('agent_names', nargs='*', default=['jayesh', 'arunjoy', 'ritvi'], 
                       help='Names of users that will play the game (defaults to jayesh, arunjoy, ritvi)')
    args = parser.parse_args()
    
    main(args.agent_names)
