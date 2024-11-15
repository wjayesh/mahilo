"""
A Session class that manages the conversation between the user and the agent.

It keeps track of the messages and saves them to a file. It should support functions like
add_message and get_last_n_messages.

This session class will be an attribute in the BaseAgent class from the agent_manager.py snippet.
Every agent will have its own session to keep track of the conversation with the user.
"""
import json
import os
from typing import Dict, List
from pathlib import Path

class Session:
    """A class to manage the conversation between the user and the agent.
    
    The session messages have two types:
    - User messages
    - Agent messages
    """
    def __init__(self, agent_name: str, server_id: str = None):
        self.agent_name = agent_name
        self.messages: List[Dict[str, str]] = []
        
        # Create a unique directory for each server instance
        self.server_dir = f"sessions/{server_id}" if server_id else "sessions"
        Path(self.server_dir).mkdir(parents=True, exist_ok=True)
        
        self.file_path = os.path.join(self.server_dir, f"{agent_name}.json")
        self.load_messages()

    def load_messages(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as file:
                    self.messages = [json.loads(line) for line in file.read().splitlines()]
            except Exception as e:
                print(f"Error loading messages: {e}")
                self.messages = []

    def save_messages(self):
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        
        try:
            with open(self.file_path, "w") as file:
                for message in self.messages:
                    file.write(f"{json.dumps(message)}\n")
        except Exception as e:
            print(f"Error saving messages: {e}")

    def add_message(self, message: str, sender: str):
        """Add a message to the session."""
        self.messages.append({"content": message, "role": sender})
        self.save_messages()

    def update_and_replace_messages(self, messages: List[Dict[str, str]]):
        """Update the messages in the session.
        
        The format should be
        [{"content": message, "role": sender}],
        """
        self.messages = messages
        self.save_messages()

    def get_last_n_messages(self, n: int) -> List[Dict[str, str]]:
        """Get the last n messages, ensuring they're in pairs."""
        messages = self.messages[-n:]
        # If we have an odd number of messages and more than one message,
        # include one more to ensure we have complete pairs
        if len(messages) > 1 and len(messages) % 2 != 0:
            messages = self.messages[-(n+1):]
        return messages

    