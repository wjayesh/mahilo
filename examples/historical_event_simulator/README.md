# Multi-Agent Historical Event Simulator

![Historical Event Simulator](../../assets/historical_event_simulator.png)

This multi-agent system simulates various historical events, allowing users to
interact with key figures and explore "what-if" scenarios.  The system uses
three specialized agents to create an engaging and historically informed
experience.

## System Overview

The simulator uses three agents:

1. **Historical Figure Agent:**  Represents a specific historical figure within the chosen event.  This agent interacts directly with the user, responding in character and maintaining historical accuracy.

2. **Context Agent:** Provides background information and historical context to the other agents.  It tracks user actions and deviations from the actual historical timeline.

3. **What-If Agent:**  Explores potential alternative outcomes based on the user's decisions within the simulation.

## Available Scenarios

The simulator currently offers the following historical scenarios:

*   **partition_of_india:** Interact with Mahatma Gandhi (or optionally Muhammad Ali Jinnah, Jawaharlal Nehru, or Lord Mountbatten – change `figure_name` in `run_server.py` to switch characters) during the Partition of India.

*   **fall_of_the_mughal_empire:** Interact with Aurangzeb (or Bahadur Shah Zafar) during the decline of the Mughal Empire.

*   **cuban_missile_crisis:** Interact with John F. Kennedy (or Nikita Khrushchev) during the tense moments of the Cuban Missile Crisis.

*   **roman_empire:** Interact with Julius Caesar during his reign.


## Getting Started

### Installation and Running the Server

1.  Clone the repository:

    ```bash
    git clone https://github.com/wjayesh/mahilo.git  # Or your repo URL
    ```

2.  Install the required packages:

    ```bash
    pip install -r requirements.txt
    ```

3.  Run the server, specifying the desired scenario:

    ```bash
    cd examples/historical_event_simulator
    python run_server.py <scenario_key>
    ```

    Replace `<scenario_key>` with one of the available scenario keys listed above (e.g., `partition_of_india`, `fall_of_the_mughal_empire`, `cuban_missile_crisis`, `roman_empire`).


4. Connect to the server using the client, specifying the correct agent type.  You can find the `agent_type` string in the `SCENARIOS` dictionary in the `run_server.py` file.  For example, for the `partition_of_india` scenario interacting with Mahatma Gandhi, you would use:

    ```bash
    python mahilo/client.py --url http://localhost:8000 --agent-type mahatma_gandhi_agent
    ```


## How to Play

1.  Connect to the server as described above, choosing your desired scenario and historical figure.

2.  Engage in conversation with the historical figure.  Ask questions, propose actions, and experience their reactions within the historical context.

3.  The simulator will strive for historical accuracy and will explore the potential ramifications of your choices, often consulting the "what if" agent for counterfactual possibilities.

## Example Interactions

*   **Partition of India (Mahatma Gandhi):**

    *   **User:** "Bapu, what is your message to the people during these turbulent times?"
    *   **Gandhi Agent:** "My dear child, we must remain committed to non-violence, even in the face of such adversity.  We must appeal to the better nature of all involved."

*   **Fall of the Mughal Empire (Aurangzeb):**

    *   **User:** "Your Majesty, the Marathas are gaining strength. What shall we do?"
    *   **Aurangzeb Agent:** "We shall crush this rebellion with the full might of the Mughal army! They dare challenge our authority?"



## Customization

You can extend the simulator by adding more scenarios to the `SCENARIOS`
dictionary in the `run_server.py` file.  Ensure that you provide appropriate
prompts for the new historical figures and events. Make sure to also update this
README with the added scenarios and their corresponding agent types.
