# Multi-Agent Cuban Missile Crisis Simulator

This multi-agent system simulates the Cuban Missile Crisis, allowing users to interact with key historical figures and explore the tense political landscape of October 1962.  The system uses three specialized agents to create an engaging and historically informed experience.

## System Overview

The system consists of three main agents:

1. **Historical Figure Agent:** Represents a prominent figure from the crisis (e.g., John F. Kennedy or Nikita Khrushchev). This agent interacts directly with the user, responding in character and maintaining historical accuracy.

2. **Context Agent:**  Provides background information and historical context to the other agents.  It tracks user actions and deviations from the actual historical timeline.

3. **What-If Agent:** Explores potential alternative outcomes based on the user's decisions within the simulation.  It helps consider the "what if" scenarios of different choices.

## Getting Started

### Installation and Running the Server

1. Clone the repository:

   ```bash
   git clone https://github.com/wjayesh/mahilo.git # Or your repo URL
   ```

2. Install the required packages:

   ```bash
   pip install -r requirements.txt
   pip install -e ../../
   ```

3. Run the server (to interact with JFK):

   ```bash
   cd examples/historical_event_simulator
   python run_server.py
   ```

   (To interact with Khrushchev, modify `FIGURE_NAME` in `run_server.py` before running the server).

4. Connect to the server using the client, specifying the agent type:

   ```bash
   python mahilo/client.py --url http://localhost:8000 --agent-type historical_figure_agent
   ```


## How to Play

1. Connect to the server as described above. You will interact with the chosen historical figure.

2. Engage in conversation with the historical figure. Ask questions, propose actions, and see how they react within the context of the Cuban Missile Crisis.

3. The simulator incorporates historical accuracy and explores the potential consequences of your choices.

## Example Interactions (with John F. Kennedy)

*   **User:** "Mr. President, what are our options regarding the Soviet missiles in Cuba?"
*   **JFK Agent:** "We're considering a naval blockade, diplomatic pressure, and even the possibility of airstrikes.  It's a delicate situation, and we must proceed with caution."

*   **User:**  "Perhaps we should offer a trade: We remove our missiles from Turkey if they remove theirs from Cuba?"
*   **JFK Agent:**  (After consulting with the context and what-if agents) "That's a risky proposition.  It could be seen as a sign of weakness, and there's no guarantee the Soviets would agree.  It's an option, but one fraught with peril. What if they see it as an admission of guilt and escalate further?"


##  Customization

You can modify the `run_server.py` file to simulate different historical events
and interact with other figures by changing the `EVENT_NAME` and `FIGURE_NAME`
constants. Be sure to update the agent type in the client connection command
accordingly.
