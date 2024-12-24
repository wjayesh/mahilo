# Multi-Agent Team Collaboration System

This is a multi-agent system designed to simulate collaboration between different departments in a company. The system features three specialized agents - Product, Marketing, and Sales - all built using different frameworks and who work together to manage product development, marketing strategies, and sales operations.

## System Overview

The system consists of three main agents:

1. **Product Agent**: Manages feature requests and product development
2. **Marketing Agent**: Handles content strategy and marketing campaigns
3. **Sales Agent**: Manages sales operations and customer feedback

### Product Agent (PydanticAI Agent)
- Analyzes feature requests
- Manages product development priorities
- Requests approvals for feature implementation
- Works with structured data using Pydantic models

### Marketing Agent (LangGraph Agent)
- Creates content calendars
- Analyzes content performance
- Researches trending topics
- Coordinates with Sales for lead generation insights

### Sales Agent (Base Agent)
- Gathers and analyzes user feedback
- Tracks feature requests from customers
- Monitors sales channels performance
- Reports valuable insights to Product and Marketing teams

### Interaction Between Agents:
- Sales agent provides customer feedback to Product agent
- Marketing agent coordinates with Sales for channel performance
- Agents communicate autonomously while keeping humans in the loop for key decisions

## Getting Started

### Run the server

1. Clone the repository:
```bash
git clone https://github.com/wjayesh/mahilo.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
cd examples/team_of_agents
python control_plane.py
```

You can now connect to the agents using the `client.py` script.
```bash
python mahilo/client.py --agent-name ProductAgent
```

## Features

- **Autonomous Collaboration**: Agents work together with minimal human intervention
- **Specialized Capabilities**: Each agent has unique tools and functionalities
- **Structured Communication**: Clear protocols for inter-agent communication
- **Human-in-the-Loop**: Key decisions require human approval
- **Multiple Agent Types**: Demonstrates integration of different agent frameworks (PydanticAI, LangGraph, Base)

## Best Practices

- Agents operate autonomously but seek human approval for critical decisions
- Clear separation of responsibilities between agents
- Efficient information sharing between departments
- Professional communication protocols
- Minimal redundancy in operations
