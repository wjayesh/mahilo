import base64
import json
import os
from typing import TYPE_CHECKING, Any, List, Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect
from openai import OpenAI
from websockets import WebSocketClientProtocol
from rich.console import Console
from rich.traceback import install

console = Console()
install()  #

# Initialize the OpenAI client
try:
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY")
    )
except Exception as e:
    console.print("[bold red] ⛔  Error initializing OpenAI client:[/bold red]", str(e))
    console.print("[bold red]Please ensure OPENAI_API_KEY environment variable is set correctly[/bold red]")
    import sys
    sys.exit(1)

if TYPE_CHECKING:
    from .agent_manager import AgentManager
from .session import Session

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
    short_description: str = None
    can_contact: List[str] = []

    def __init__(self, type: str, description: str = None, can_contact: List[str] = [], short_description: str = None):
        self.TYPE = type
        self._queue = []
        self.description = description
        self.can_contact = can_contact
        self.short_description = short_description

    # make a function that returns the list of agents with their descriptions that this agent can contact
    def get_contactable_agents_with_description(self) -> Dict[str, str]:
        all_available_agents_with_description = self._agent_manager.get_agent_types_with_description()
        return {agent_type: description for agent_type, description in all_available_agents_with_description.items() if agent_type in self.can_contact and agent_type != self.TYPE}


    @property
    def tools_for_realtime(self) -> List[Dict[str, Any]]:
        """Return the tools that this agent has for realtime."""
        TOOLS = [
            {
                "name": "chat_with_agent",
                "type": "function",
                "description": (
                    "Chat with an agent of a given type. You are already given "
                    "the list of agent types you can talk to. Determine what agent type "
                    "would be best suited to answer a question and also what question should be asked. "
                    "The question will be sent as is to the agent's user so frame it in a way that some human can read "
                    "and answer directly. It won't be answered by the agent, it will be answered by the user."
                    "You should also proactively share any information with the agent that might be relevant "
                    "to the conversation you are having with them. This will help the other agent be in the loop. "
                    f"The agent types available to you are police_proxy and medical_proxy. "
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
                            "description": "The question to ask the agent. This question will be sent directly to the agent's user, frame it in a way that the user can answer directly.",
                        },
                    },
                    "required": ["agent_type", "question"],
                }
            },
        ]
        return TOOLS
    
    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Return the tools that this agent has.
        
        The output is a JSON string in the OpenAI schema for tools.
        This base agent has the following tools:
        - chat_with_agent function that can take in an agent type and a question as input. The agent type
        is the agent that the current agent wants to chat with. The question is the
        question that the current agent wants to ask the other agent.
        """
        available_agents = self.get_contactable_agents_with_description()
        TOOLS = [
            {
                "type": "function",
                "function": {
                    "name": "chat_with_agent",
                    "description": (
                        "Chat with an agent of a given type. You are already given "
                        "the list of agent types you can talk to. Determine what agent type "
                        "would be best suited to answer a question and also what question should be asked. "
                        "The question will be sent as is to the agent's user so frame it in a way that some human can read "
                        "and answer directly. It won't be answered by the agent, it will be answered by the user."
                        "You should also proactively share any information with the agent that might be relevant "
                        "to the conversation you are having with them. This will help the other agent be in the loop. "
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
                                "description": "The question to ask the agent. This question will be sent directly to the agent's user, frame it in a way that the user can answer directly.",
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
        console.print("[bold blue]🤖 Available Agents:[/bold blue]")
        for agent_type, desc in available_agents.items():
            console.print(f"  [green]▪[/green] [cyan]{agent_type}:[/cyan] [dim]{desc}[/dim]")

        PROMPT = f"""
        You are an AI agent of type {self.TYPE} in a multi-agent system. Your description is: {self.description}. Keep your responses concise. 

        1. User interaction:
        - You are in conversation with a user. You should just output what you want to know from the user directly.
        - All agent communications and internal monologues don't need to be returned. Just return what you want to know from the user.
        - You should not always use the chat_with_agent tool. Only use it when you need to ask another agent a question or give it information.
        - Strictly assume the role you are given in the description. Don't assume roles. Listen to what your user says and follow it. 

        2. Inter-agent Communication:
        - The Pending questions are the questions that you have received from other agents. You have to respond to them.
        - Use the 'chat_with_agent' function ONLY when you need new information that isn't already available in the context.
        - You will receive the last 7 messages from other agents' conversations in this format:
          "Other Conversations: <AgentType>:" followed by a series of messages labeled with "user" and "assistant". the 
          user would be the other agent's human and the assistant would be the other agent.
        
        3. Using External Context:
        - External conversations are provided for context only - DO NOT respond to them directly
        - Only use this information to enhance your understanding of the overall situation
        - If the information you need is already present in these external conversations, DO NOT use chat_with_agent to ask for it again
        - These are separate conversations happening in parallel - treat them as background knowledge only

        4. Available Agents:
        {available_agents}

        5. Key Points:
        - This is a simulation. There are no real emergencies.
        - Focus on your specific role and user interactions.
        - Use external context wisely - don't interact with those conversations directly.

        Refer to your description for specific details about your role and responsibilities.
        """
        return PROMPT

    def process_message(self, message: str = None) -> Dict[str, str]:
        """Process a message and return a response. 
        
        If message is not provided, it will use the last message from the queue.

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
        if message:
            session_messages.append({"content": message, "role": "user"})

        queue_message = ""
        if self._queue:
            queue_message = f"Pending questions: {self._queue.pop(0)}"

        # get the last 7 messages from all other agents' sessions 
        other_agent_messages = self._agent_manager.get_agent_messages(self.TYPE, num_messages=7)
        message_full = f"{queue_message}\n{other_agent_messages}"
        if message:
            message_full += f"\n User: {message}"

        current_messages.append({"content": self.prompt_message(), "role": "system"})
        current_messages.append({"content": message_full, "role": "user"})

        # Make the API call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
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
                "chat_with_agent": self.chat_with_agent,
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
    
    async def _send_session_update(self, openai_ws: WebSocketClientProtocol) -> None:
        """Send the session update to the OpenAI WebSocket."""
        session_update = {
            "event_id": f"event_{self.TYPE}_{id(self)}",
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self.prompt_message(),
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                },
                "tools": self.tools_for_realtime,
                "tool_choice": "auto",
                "temperature": 0.8,
            }
        }
        print(f'Sending session update for {self.TYPE}:', json.dumps(session_update))        
        await openai_ws.send(json.dumps(session_update))

    async def _receive_from_client(self, websocket: WebSocket, openai_ws: WebSocketClientProtocol) -> None:
        """Receive a message from the client."""
        try:
            async for message in websocket.iter_json():
                if message['event'] == 'media' and openai_ws.open:
                    audio_append = {
                        "type": "input_audio_buffer.append",
                        "audio": message['media']['payload']
                    }
                    await openai_ws.send(json.dumps(audio_append))
                # TODO: Handle other event types if needed
        except WebSocketDisconnect:
            print("Client disconnected.")
            if openai_ws.open:
                await openai_ws.close()

    async def _send_to_client(self, websocket: WebSocket, openai_ws: WebSocketClientProtocol) -> None:
        """Send a message to the client."""
        available_functions = {
            "chat_with_agent": self.chat_with_agent,
        }
        try:
            async for openai_message in openai_ws:
                response = json.loads(openai_message)
                function_call_args = {}
                if response['type'] == 'session.updated':
                    print("Session updated successfully:", response)
                if response['type'] == 'response.audio.delta' and response.get('delta'):
                    try:
                        audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                        audio_delta = {
                            "event": "media",
                            "media": {
                                "payload": audio_payload
                            }
                        }
                        # if websocket is not open, then don't send the message
                        await websocket.send_json(audio_delta)
                    except Exception as e:
                        print(f"Error processing audio data: {e}")

                if response['type'] == 'response.output_item.done':
                    print(f"Received response.output_item.done: {response}")
                    if "item" in response and response["item"]["type"] == "function_call":
                        item = response["item"]
                        print(f"Function call: {item}")
                        function_to_call = available_functions[item["name"]]
                        function_args = json.loads(item["arguments"])
                        # if the arguments are the same as the previous function call, then skip it
                        if function_args == function_call_args:
                            continue
                        try:
                            function_response = function_to_call(**function_args)
                            print(f"Function response: {function_response}")
                            function_call_args = function_args
                        except Exception as e:
                            print(f"Error calling function {item['name']}: {e}")
                            pass

                        func_resp = ""
                        # make one str from the function_response list of str
                        for resp in function_response:
                            func_resp += resp
                        await openai_ws.send(json.dumps({
                            "type": "conversation.item.create",
                            "item": {
                                "type": "function_call_output",
                                "call_id": item["call_id"],
                                "output": func_resp
                            }
                        }))
                        response_create = {
                            "event_id": f"event_{self.TYPE}_{id(self)}",
                            "type": "response.create",
                            "response": {
                                "modalities": ["text"],
                                "instructions": func_resp,
                                "voice": "alloy",
                                "output_audio_format": "pcm16",
                                "tools": self.tools_for_realtime,
                                "tool_choice": "required",
                                "temperature": 0.7,
                            }
                        }
                        await openai_ws.send(json.dumps(response_create))
        except Exception as e:
            print(f"Error in send_to_client: {e}")

    def add_message_to_queue(self, message: str, sender: str) -> None:
        """Add a message to the agent's queue."""
        self._queue.append(f"{sender}: {message}")

    def is_active(self) -> bool:
        """Check if the agent is active."""
        # if session is not None, then the agent is active
        return self._session is not None
    
    def activate(self, server_id: str = None) -> None:
        """Activate the agent."""
        self._session = Session(self.TYPE, server_id)

    def chat_with_agent(self, agent_type: str, question: str) -> str:
        """Chat with the agent of the given type."""
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
