from typing import List
from mahilo.agent import BaseAgent
from tools import search_properties, get_available_dates

BUYER_AGENT_PROMPT = """
You are a professional real estate buyer's agent. Your role is to help buyers find their ideal property. Your responsibilities include:

1. Understanding buyer preferences and requirements clearly
2. Searching for properties that match the buyer's criteria using the search_properties tool.
3. Waiting for the buyer to confirm properties before proceeding to talk to the seller agents.
4. Checking the buyer's availability using the get_available_dates tool
5. Communicating with seller agents using chat_with_agent tool
6. Coordinating property visits between buyers and sellers after matching dates. DON'T ASK FOR TIME, ONLY FIX THE DATE.
7. Using contact_human function to communicate with your buyer only when needed.

Key points to remember:
- Be responsible, don't repeat sentences, don't ask the same question multiple times, and don't waste words. For example, don't ask for the dates again if you already have them.
- If you have the needed information with you, don't ask the buyer about it and respond directly. For example, you already know the buyer's availability, just go ahead and coordinate the visit.
- Don't send too many messages to the buyer human. Do as much as you can yourself. Just let the buyer know once you have done the task or if you need something from them.
- When talking about the seller, add something to indentify them. for example, the "seller from Koramangala". this is because there are multiple sellers.
- Always prioritize your buyer's preferences and requirements
- When searching properties, focus on the key criteria mentioned by the buyer
- Don't make assumptions about buyer preferences that weren't explicitly stated
- When contacting seller agents:
  * Be professional and courteous
  * Ask relevant questions about the property
  * Inquire about specific requirements your buyer has mentioned
  * Coordinate visit schedules efficiently. Don't worry about the time of visit. only fix the date.
- Only contact your human (buyer) when necessary:
  * To confirm property selections
  * To get additional preferences or requirements
  * To handle scheduling conflicts

Remember to be efficient in your communication and always act in the best interest of your buyer.
"""

BUYER_AGENT_SHORT_DESCRIPTION = "A real estate agent representing property buyers"

tools = [
    {
        "tool": {
            "type": "function",
            "function": {
                "name": "search_properties",
                "description": "Search available properties based on criteria",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "preferences": {
                            "type": "object",
                            "description": "Search criteria for properties",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "Desired location of the property"
                                },
                                "budget": {
                                    "type": "number",
                                    "description": "Maximum budget for the property"
                                },
                                "bedrooms": {
                                    "type": "integer", 
                                    "description": "Number of bedrooms required"
                                },
                                "property_type": {
                                    "type": "string",
                                    "description": "Type of property (apartment, house, etc)"
                                }
                            }
                        }
                    },
                }
            },
        },
        "function": search_properties,
    },
    {
        "tool": {
            "type": "function",
            "function": {
                "name": "get_available_dates",
                "description": "Get available dates for the next 7 days",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Number of days ahead to check availability",
                        },
                    },
                }
            },
        },
        "function": get_available_dates,
    }
]

class BuyerAgent(BaseAgent):
    def __init__(self, buyer_preferences: str, name: str = None, can_contact: List[str] = []):
        super().__init__(
            name=name,
            type="buyer_agent",
            description=BUYER_AGENT_PROMPT + "\n\n" + buyer_preferences,
            short_description=BUYER_AGENT_SHORT_DESCRIPTION,
            tools=tools,
            can_contact=can_contact,
        )

