from mahilo import AgentManager, ServerManager
from buyer_agent import BuyerAgent
from seller_agent import SellerAgent

# initialize the agent manager
manager = AgentManager()

# create the agents
buyer_preferences = "Buyer preferences: I am looking for a 2BHK in Koramangala or Indiranagar with good schools and hospitals nearby."
buyer_agent = BuyerAgent(buyer_preferences=buyer_preferences, name="buyer_agent", can_contact=["seller_agent_1", "seller_agent_2"])

seller_preferences_1 = "Seller preferences: I prefer to sell my property to a young family with children. I want that when they are living in the property, they should be inside the property by 9pm."
seller_agent_1 = SellerAgent(seller_preferences=seller_preferences_1, name="seller_agent_1", can_contact=["buyer_agent"])

seller_preferences_2 = "Seller preferences: I prefer to sell my property to bachelors. I don't care when they get home in the night."
seller_agent_2 = SellerAgent(seller_preferences=seller_preferences_2, name="seller_agent_2", can_contact=["buyer_agent"])

# register the agents to the manager
manager.register_agent(buyer_agent)
manager.register_agent(seller_agent_1)
manager.register_agent(seller_agent_2)

# activate the buyer agent as the starting point
buyer_agent.activate()

# initialize the server manager
server = ServerManager(manager)

# run the server
def main():
    server.run()

if __name__ == "__main__":
    main() 