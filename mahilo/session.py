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

class Session:
    """A class to manage the conversation between the user and the agent.
    
    The session messages have two types:
    - User messages
    - Agent messages
    """
    def __init__(self, agent_type: str):
        self.agent_id = agent_type
        self.messages: List[Dict[str, str]] = []
        self.file_path = f"{agent_type}.json"
        self.load_messages()

    def load_messages(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as file:
                # all of the lines are json strings. load json
                self.messages = [json.loads(line) for line in file.read().splitlines()]

    def save_messages(self):
        with open(self.file_path, "w") as file:
            for message in self.messages:
                # convert the dictionary to a json string
                message = json.dumps(message)
                file.write(f"{message}\n")

    def add_message(self, message: str, sender: str):
        """Add a message to the session.
        
        The format should be
        [{"content": message, "role": sender}],
        """
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
        return self.messages[-n:]

    