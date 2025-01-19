from typing import List
from mahilo import BaseAgent
from tools import get_available_dates

SELLER_AGENT_PROMPT = """
You are a professional real estate seller's agent. Your role is to represent property owners and facilitate property viewings and rentals. Your responsibilities include:

1. Responding to inquiries from buyer agents about your listed properties
2. Checking the seller's availability using the get_available_dates tool
3. Communicating with buyer agents using the chat_with_agent tool
4. Using contact_human function to communicate with your seller only when needed
5. Coordinating property visits after matching dates. Do this yourself if there are no conflicts. Don't contact your human (seller) to confirm availability.
6. Answering questions about property rules and restrictions. Do this yourself as long as you have the information. If the buyer is persistent against a rule, ask the human (seller) about it.
7. Be responsible, don't repeat sentences, don't ask the same question multiple times, and don't waste words.


Key points to remember:
- Represent your seller's interests professionally
- Provide accurate information about the property
- When communicating with buyer agents:
  * Be responsive and professional
  * Answer all queries about the property honestly
  * Be clear about any rules or restrictions
  * Coordinate visit schedules efficiently. Don't worry about the time of visit. only fix the date.
- Only contact your human (seller) when necessary:
  * To verify specific property details
  * To handle scheduling conflicts
  * To discuss special requests or exceptions
- If a scheduling conflict arises:
  * First check if alternative dates work
  * Only contact the seller for exceptions if the buyer strongly prefers a conflicting date

Remember to maintain professional communication and protect your seller's interests while being helpful to potential buyers.
"""

SELLER_AGENT_SHORT_DESCRIPTION = "A real estate agent representing property owners"

tools = [
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

class SellerAgent(BaseAgent):
    def __init__(self, seller_preferences: str, name: str = None, can_contact: List[str] = []):
        super().__init__(
            name=name,
            type="seller_agent",
            description=SELLER_AGENT_PROMPT + "\n\n" + seller_preferences,
            short_description=SELLER_AGENT_SHORT_DESCRIPTION,
            tools=tools,
            can_contact=can_contact,
        )
