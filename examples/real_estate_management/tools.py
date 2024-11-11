import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

def search_properties(preferences: Dict[str, Any]) -> List[Dict]:
    """
    Dummy function to search for properties based on preferences
    Returns a list of properties with their details and seller agent IDs
    """
    # Dummy property database
    properties = [
        {
            "id": "prop1",
            "type": "1BHK",
            "location": "Koramangala",
            "price": 25000,
            "seller_agent": "seller_agent_1",
            "description": "Spacious 1BHK with modern amenities"
        },
        {
            "id": "prop2",
            "type": "1BHK",
            "location": "Indiranagar",
            "price": 28000,
            "seller_agent": "seller_agent_2",
            "description": "Cozy 1BHK near metro station"
        },
        {
            "id": "prop3",
            "type": "2BHK",
            "location": "Koramangala",
            "price": 35000,
            "seller_agent": "seller_agent_1",
            "description": "Premium 2BHK with parking"
        }
    ]
    
    # Basic filtering based on location
    if "location" in preferences:
        properties = [p for p in properties if preferences["location"].lower() in p["location"].lower()]
    
    return properties

def check_calendar(date: str) -> bool:
    """
    Dummy function to check if an agent's human is available on a given date
    Returns True if available, False if not
    """
    # Randomly return True or False for demo purposes
    return random.choice([True, False])

def get_available_dates(days_ahead: int = 7) -> List[str]:
    """
    Dummy function to get available dates for next 7 days
    Returns a list of available dates
    """
    available_dates = []
    today = datetime.now()
    
    for i in range(days_ahead):
        date = today + timedelta(days=i)
        if check_calendar(date):
            available_dates.append(date.strftime("%Y-%m-%d"))
    
    return available_dates
