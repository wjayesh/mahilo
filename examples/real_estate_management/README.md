# Multi-Agent Real Estate Management System

This is a multi-agent system designed to facilitate real estate transactions by automating interactions between buyers and sellers through intelligent agents. The system features buyer agents and seller agents that can coordinate property viewings and handle property-related inquiries autonomously.

## System Overview

The system consists of three main components:

1. **Buyer Agent**: Represents property buyers and helps find suitable properties
2. **Seller Agent**: Represents property owners and handles property inquiries
3. **Tools**: Shared utilities for property search and scheduling

### Buyer Agent
- Searches properties based on buyer preferences
- Coordinates with seller agents for property viewings
- Manages buyer availability and scheduling
- Autonomously handles routine communications

### Seller Agent
- Responds to property inquiries
- Manages property viewing schedules
- Enforces property rules and restrictions
- Handles availability coordination

### Interaction Between Agents:
- Buyer's agent contacts relevant seller's agent(s)
- Agents exchange property details and discuss preferences
- Agents coordinate to schedule property visits, talking to the human only when there are conflicts

### Tools
- Property search functionality
- Calendar management and availability checking
- Date coordination utilities

## Getting Started

### Installation

1. Clone the repository:
```bash
git clone https://github.com/wjayesh/mahilo.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage

1. Inside, the run_server.py file, initialize a Buyer Agent:
```python
buyer_preferences = """
Looking for:
- Location: Koramangala
- Budget: 30000
- Type: 1BHK
"""
buyer_agent = BuyerAgent(buyer_preferences=buyer_preferences)
```

2. Inside, the run_server.py file, initialize a Seller Agent:
```python
seller_preferences = """
- Prefer to sell to a young family with children
- Tenants should be inside the property by 9pm
- Rules: No pets allowed
"""
seller_agent = SellerAgent(type="seller_agent_1", seller_preferences=seller_preferences)
```

3. Run the server:
   ```
   cd examples/real_estate_management
   python run_server.py
   ```

## Features

- **Automated Property Search**: Agents can search properties based on specific criteria
- **Smart Scheduling**: Automatic coordination of property viewings
- **Autonomous Communication**: Agents handle routine interactions without human intervention
- **Availability Management**: Built-in calendar management for scheduling
- **Professional Communication**: Agents maintain professional etiquette in all interactions

## Best Practices

- Agents prioritize autonomous operation to minimize human intervention
- Clear communication protocols between buyer and seller agents
- Efficient scheduling and availability management
- Professional representation of client interests

