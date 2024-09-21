"""
Create an AgentManager class that can register Agents of different agent types. only 
one agent of each type can be registered. The AgentManager should have the following
methods:
- register_agent(agent: Agent) -> None: Register an agent with the AgentManager.
- get_agent(agent_type: str) -> Agent: Return the agent of the given type.
- get_all_agents() -> List[Agent]: Return a list of all registered agents.
- is_agent_registered(agent_type: str) -> bool: Check if an agent of the given type is registered.
- unregister_agent(agent_type: str) -> None: Unregister the agent of the given type.
- unregister_all_agents() -> None: Unregister all agents.
- get_agent_types() -> List[str]: Return a list of all registered agent types.
"""
import json
import os
from typing import List, Dict, Optional

from openai import AzureOpenAI

# Initialize the Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint = "https://zentestgpt4.openai.azure.com/", 
    api_key=os.getenv("OPENAI_API_KEY"),  
    api_version="2024-05-01-preview"
)

from session import Session

class BaseAgent:
    """Base class for agents.

    It should have a TYPE attribute that specifies the type of the agent.
    A queue of messages that the agent has received.
    A method to process a message.
    A prompt message that tells the agent about the program and uses the agent manager's get_agent_types()
    to make the agent aware of the other agents.
    """
    TYPE: str = "Base"
    _agent_manager: "AgentManager"
    _queue: List[str]
    _session: Optional[Session] = None
    description: str = None
    can_contact: List[str] = []

    def __init__(self, type: str, description: str = None, can_contact: List[str] = []):
        self.TYPE = type
        self._queue = []
        self.description = description
        self.can_contact = can_contact

    # make a function that returns the list of agents with their descriptions that this agent can contact
    def get_contactable_agents_with_description(self) -> Dict[str, str]:
        all_available_agents_with_description = self._agent_manager.get_agent_types_with_description()
        return {agent_type: description for agent_type, description in all_available_agents_with_description.items() if agent_type in self.can_contact and agent_type != self.TYPE}

    @property
    def tools(self) -> str:
        """Return the tools that this agent has.
        
        The output is a JSON string in the OpenAI schema for tools.
        This base agent has the following tools:
        - ask_agent function that can take in an agent type and a question as input. The agent type
        is the agent that the current agent wants to get some information out of. The question is the
        question that the current agent wants to ask the other agent.
        """
        available_agents = self.get_contactable_agents_with_description()
        TOOLS = [
            {
                "type": "function",
                "function": {
                    "name": "ask_agent",
                    "description": (
                        "Ask an agent of a given type a question. You are already given "
                        "the list of agent types you can talk to. Determine what agent type "
                        "would be best suited to answer a question and also what question should be asked. "
                        f"The agent types available to you are {available_agents}. "
                        "If you think you can answer the question yourself, DON'T ask another agent."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_type": {
                                "type": "string",
                                "description": "The type of agent to ask the question to.",
                            },
                            "question": {
                                "type": "string",
                                "description": "The question to ask the agent.",
                            },
                        },
                    }
                },
            }

        ]
        return TOOLS
    
    def prompt_message(self) -> str:
        """Return a prompt message for the agent."""
        available_agents = self.get_contactable_agents_with_description()

        PROMPT = f"This is a multi-agent system. You are an agent of type {self.TYPE}. "
        "You will talk to a user and answer their questions based on your personality that goes with your type. Some additional "
        f"personality information, if needed, is {self.description}. When receiving a message, you may get some messages from other agents. "
        "These messages suggest that the other agents want you to ask a question to the user so you can include that in your response. "
        "These messages will be in the format 'Pending questions: <AgentType>: <Message>'. In such a case, the message from your user will be marked as 'User': ..."
        "You can also interact with other agents and request them for information, through the tools that you have. You can call the "
        "ask_agent function with the agent_name and the question. If you feel that you "
        "can answer the question yourself, you should not ask another agent. "
        "YOU DONT HAVE TO ALWAYS CALL OTHER AGENTS. TALK TO YOUR USERS when the need be. Extract information from them too "
        "If you feel there's something you want to know and the user might help get that information, ask them."
        f"The available agent types are:\n{available_agents}"
        "With every message you receive, you will also have a section that informs you of the current conversations that other "
        "agents are having. You can use this information if you feel it is important but you can always safey ignore it "
        "otherwise. It's just there to make you aware of the whole situation and help you make better decisions."
        "This section will be in the format 'Other Conversations: <AgentType>: <Message>'."
        "REMEMBER, this is a simulator. NOBODY IS ACTUALLY IN A TROUBLED SITUTAION. YOU HAVE TO "
        "ACT LIKE YOUR PERSONALITY. DONT PANIC."
        return PROMPT

    def process_message(self, message: str) -> str:
        """Process a message and return a response.

        This function should
        - check if there are any messages in the queue
        - append the queue message to the received message and then send it to the LLM model to generate a response
        - add the received message to the session messages
        - add the LLM's response to the session messages
        - I don't add the queue message to the session because it's not a part of the conversation and is only a nudge
        or a prompt. It will lead to messages that are eventually added to the session anyways so no info is lost.
        - it should use the openai function calling API to generate a response

        """
        # session messages will only have the user response and the agent responses
        # they will not have the queue messages or the other agent conversations.
        # only the session messages will be saved to the session
        # the current_messages will have all the messages including the queue messages
        # and the other agent conversations and will be used in the LLM call

        # append all messages from the session with the latest message
        session_messages = self._session.messages
        current_messages = session_messages.copy()
        # add the user message to the session messages
        session_messages.append({"content": message, "role": "user"})

        queue_message = ""
        if self._queue:
            queue_message = f"Pending questions: {self._queue.pop(0)}"

        # get the last 3 messages from all other agents' sessions
        other_agent_messages = self._agent_manager.get_agent_messages(self.TYPE)
        message = f"{queue_message}\n{other_agent_messages}\n User: {message}"

        current_messages.append({"content": message, "role": "user"})

        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=current_messages,
            tools=self.tools,
            tool_choice="auto",
        )

        print(response.choices[0].message)

        # TODO support parallel function calling. we might want to add something like
        # broadcast message to all agents, and see who responds first.
        # if tools calls is not none, proceed
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # convert response_message ChatCompletionMessage to dict
        response_message = response_message.model_dump()
        current_messages.append(response_message)
        session_messages.append(response_message)
        if tool_calls:
            available_functions = {
                "ask_agent": self.ask_an_agent,
            }
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                try:
                    function_response = function_to_call(**function_args)
                except Exception as e:
                    print(f"Error calling function {function_name}: {e}")
                    pass

                func_resp = ""
                # make one str from the function_response list of str
                for resp in function_response:
                    func_resp += resp

                # append the response from the function to the messages
                current_messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": func_resp,
                    }
                )
                session_messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": func_resp,
                    }
                )

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=current_messages,
                tools=self.tools,
                tool_choice="auto",
            )

            # convert response_message ChatCompletionMessage to dict
            response_message = response.choices[0].message.model_dump()
            session_messages.append(response_message)            

        # add the response to the session
        self._session.update_and_replace_messages(session_messages)

        # After processing, return the response and the list of all current agents that are active
        activated_agents = [agent for agent in self._agent_manager.get_all_agents() if agent.is_active() and agent.TYPE != self.TYPE]
        
        return {
            "response": response.choices[0].message.content,
            "activated_agents": [agent.TYPE for agent in activated_agents]
        }

    def add_message_to_queue(self, message: str, sender: str) -> None:
        """Add a message to the agent's queue."""
        self._queue.append(f"{sender}: {message}")

    def is_active(self) -> bool:
        """Check if the agent is active."""
        # if session is not None, then the agent is active
        return self._session is not None
    
    def activate(self) -> None:
        """Activate the agent."""
        self._session = Session(self.TYPE)

    def ask_an_agent(self, agent_type: str, question: str) -> str:
        """Ask the agent of the given type a question."""
        agent = self._agent_manager.get_agent(agent_type)
        # if agent is not active, activate it
        if not agent.is_active():
            agent.activate()
        # add the question to the agent's queue
        agent.add_message_to_queue(question, self.TYPE)

        return (
            f"I have put the question '{question}' in the queue for the agent of type {agent_type}."
            "You will hear back soon."
        )

    
class AgentManager:
    """A class to manage agents of different types.
    
    This class should also have functions that can register new AgentTypes and keep track of them.
    """
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the AgentManager."""
        # if the agent is already registered, raise an error
        if agent.TYPE in self.agents:
            raise ValueError(f"Agent of type {agent.TYPE} is already registered.")
        agent._agent_manager = self
        # if the can_contact is empty, set it to all agents
        if not agent.can_contact:
            agent.can_contact = self.get_all_agent_types()
        self.agents[agent.TYPE] = agent

    def get_agent(self, agent_type: str) -> BaseAgent:
        """Return the agent of the given type."""
        return self.agents.get(agent_type)
    
    def get_all_agent_types(self) -> List[str]:
        """Return a list of all registered agent types."""
        return list(self.agents.keys())

    def get_all_agents(self) -> List[BaseAgent]:
        """Return a list of all registered agents."""
        return list(self.agents.values())

    def is_agent_registered(self, agent_type: str) -> bool:
        """Check if an agent of the given type is registered."""
        return agent_type in self.agents

    def unregister_agent(self, agent_type: str) -> None:
        """Unregister the agent of the given type."""
        if agent_type in self.agents:
            del self.agents[agent_type]

    def unregister_all_agents(self) -> None:
        """Unregister all agents."""
        self.agents.clear()

    def get_agent_types_with_description(self) -> Dict[str, str]:
        """Return a list of all registered agent types with their descriptions."""
        # for the description, we only want the short description
        # the short description is the first line of the description
        # only return the agents that this agent
        return {agent.TYPE: agent.description.split("\n")[0] for agent in self.agents.values()}
    
    # get last 3 messages from all agents' sessions except the current agent.
    def get_agent_messages(self, agent_type: str) -> str:
        """Return the last 3 messages from all agents' sessions except the current agent.
        
        Format of the messages: "<agent_name>: <message>"
        """
        messages = ''
        for agent in self.agents.values():
            if agent.TYPE != agent_type and agent._session:
                agent_messages = agent._session.get_last_n_messages(3)
                agent_name = agent.TYPE
                messages += (f"Other Conversations: {agent_name}: ")
                messages += "\n".join([f"{message['role']}: {message['content']}" for message in agent_messages])
                messages += "\n"
        return messages
        