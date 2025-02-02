import base64
import json
import os
from typing import TYPE_CHECKING, Any, List, Dict, Optional, Callable, get_type_hints

from fastapi import WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI
from websockets import WebSocketClientProtocol
from rich.console import Console
from rich.traceback import install
import asyncio

from mahilo.tools import get_chat_with_agent_tool

console = Console()
install()  #

# Initialize the OpenAI client
try:
    client = AsyncOpenAI(
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

class ToolFunctionError(Exception):
    """Custom exception for tool function validation errors."""
    pass

class BaseAgent:
    """Base class for agents.

    It should have a TYPE attribute that specifies the type of the agent.
    A queue of messages that the agent has received.
    A method to process a message.
    A prompt message that tells the agent about the program and uses the agent manager's get_agent_types()
    to make the agent aware of the other agents.
    """
    TYPE: str = "Base"
    name: str = None
    _agent_manager: "AgentManager"
    _queue: List[str]
    _session: Optional[Session] = None
    description: str = None
    short_description: str = None
    can_contact: List[str] = []

    def __init__(self, type: str, name: str = None, description: str = None, can_contact: List[str] = [], short_description: str = None, tools: List[Dict[str, Any]] = None):
        """Initialize a BaseAgent.
        
        Args:
            type (str): The type of agent (e.g. "story_weaver")
            name (str, optional): Unique name for this agent instance
            description (str, optional): Long description of the agent
            can_contact (List[str], optional): List of agent types this agent can contact
            short_description (str, optional): Brief description of the agent
            tools (List[Dict], optional): List of tool configurations. Each tool must contain:
                - "tool": The OpenAI tool configuration
                - "function": A callable that returns str or List[str]
                
        Raises:
            ToolFunctionError: If any tool configuration or function is invalid
        """
        self.TYPE = type
        self.name = name or f"{type}_{id(self)}"  # Default to type_uniqueid if no name given
        self._queue = []
        self.description = description
        self.can_contact = can_contact
        self.short_description = short_description
        self._custom_tools = []
        self._custom_functions = {}

        if tools:
            for tool_config in tools:
                try:
                    self._validate_tool_config(tool_config)
                    tool = tool_config["tool"]
                    func = tool_config["function"]
                    tool_name = tool["function"]["name"]
                    
                    self._custom_tools.append(tool)
                    self._custom_functions[tool_name] = func
                except ToolFunctionError as e:
                    raise ToolFunctionError(f"Invalid tool configuration: {str(e)}")

    # make a function that returns the list of agents with their descriptions that this agent can contact
    def get_contactable_agents_with_description(self) -> Dict[str, str]:
        """Return a dict of contactable agent names with their descriptions."""
        all_available_agents_with_description = {
            agent.name: agent.short_description 
            for agent in self._agent_manager.get_all_agents()
        }
        return {
            name: desc 
            for name, desc in all_available_agents_with_description.items() 
            if name in self.can_contact and name != self.name
        }


    @property
    def tools_for_realtime(self) -> List[Dict[str, Any]]:
        """Return the tools that this agent has for realtime."""
        try:
            available_agents = self.get_contactable_agents_with_description()
        except AttributeError as e:
            console.print("[bold red] ⚠️  Agent not registered with AgentManager:[/bold red]")
            available_agents = {}
        TOOLS = [
            {
                "name": "chat_with_agent",
                "type": "function",
                "description": (
                    "Chat with an agent by their name. You are already given "
                    "the list of agent names you can talk to. Determine what agent "
                    "would be best suited to answer a question and also what question should be asked. "
                    f"The agent names available to you are {available_agents}. "
                    "Don't use any other agent names. You also shouldn't send a chat message to yourself."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "The name of the agent to ask the question to.",
                        },
                        "your_name": {
                            "type": "string",
                            "description": "The name of the agent asking the question, that is you.",
                        },
                        "question": {
                            "type": "string",
                            "description": "The question to ask the agent.",
                        },
                    },
                    "required": ["agent_name", "your_name", "question"],
                }
            },
            {
                "name": "contact_human",
                "type": "function",
                "description": (
                    "Contact your human. Use this function whenever you want to send some information to your human or get new information from your human."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "The message to send to the human.",
                        },
                    },
                },
            },
        ]
        return TOOLS
    
    
    def _get_base_tools(self) -> List[Dict[str, Any]]:
        """Return the base tools that all agents must have."""
        try:
            available_agents = self.get_contactable_agents_with_description()
        except AttributeError as e:
            console.print("[bold red] ⚠️  Agent not registered with AgentManager:[/bold red]")
            available_agents = {}
        return [
            {
                "type": "function",
                "function": {
                    "name": "chat_with_agent",
                    "description": (
                        "Chat with an agent by their name. You are already given "
                        "the list of agent names you can talk to. Determine what agent "
                        "would be best suited to answer a question and also what question should be asked. "
                        f"The agent names available to you are {available_agents}. "
                        "Don't use any other agent names. You also shouldn't send a chat message to yourself."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_name": {
                                "type": "string",
                                "description": "The name of the agent to ask the question to.",
                            },
                            "your_name": {
                                "type": "string",
                                "description": "The name of the agent asking the question, that is you.",
                            },
                            "question": {
                                "type": "string",
                                "description": "The question to ask the agent.",
                            },
                        },
                    }
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "contact_human",
                    "description": "Contact your human. Use this function whenever you want to send some information to your human or get new information from your human.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "The message to send to the human.",
                            },
                        },
                    },
                },
            },
        ]

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Return all tools available to this agent, combining base and custom tools."""
        return self._get_base_tools() + self._custom_tools

    def add_tool(self, tool_config: Dict[str, Any]) -> None:
        """Add a new tool to the agent's toolkit.
        
        Args:
            tool_config (Dict[str, Any]): Tool configuration containing:
                - "tool": The OpenAI tool configuration
                - "function": A callable that returns str or List[str]
                
        Raises:
            ToolFunctionError: If the tool configuration or function is invalid
            
        Example:
            agent.add_tool({
                "tool": {
                    "type": "function",
                    "function": {
                        "name": "search_database",
                        "description": "Search the database",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"}
                            }
                        }
                    }
                },
                "function": search_database  # Must return str or List[str]
            })
        """
        self._validate_tool_config(tool_config)
        
        tool = tool_config["tool"]
        func = tool_config["function"]
        tool_name = tool["function"]["name"]
        
        if any(t.get("function", {}).get("name") == tool_name for t in self.tools):
            raise ToolFunctionError(f"Tool with name '{tool_name}' already exists")
        
        self._custom_tools.append(tool)
        self._custom_functions[tool_name] = func
        print(f"Tool '{tool_name}' added to toolkit")

    def remove_tool(self, tool_name: str) -> Dict[str, Any]:
        """Remove a tool and its function from the agent's toolkit by name.
        
        Args:
            tool_name (str): Name of the tool to remove
            
        Returns:
            Dict[str, Any]: The removed tool configuration containing both the tool and its function
            
        Raises:
            ValueError: If tool doesn't exist or is a base tool
        """
        if tool_name in ["chat_with_agent", "contact_human"]:
            raise ValueError(f"Cannot remove base tool '{tool_name}'")
                
        # Find tool index
        tool_index = None
        for i, tool in enumerate(self._custom_tools):
            if tool.get("function", {}).get("name") == tool_name:
                tool_index = i
                break
                
        if tool_index is None:
            raise ValueError(f"Tool '{tool_name}' not found in toolkit")
                
        # Remove and return both tool and function
        removed_tool = self._custom_tools.pop(tool_index)
        removed_function = self._custom_functions.pop(tool_name)
                
        print(f"Tool '{tool_name}' removed from toolkit")
                
        return {
            "tool": removed_tool,
            "function": removed_function
        }

    def prompt_message(self) -> str:
        """Return a prompt message for the agent."""
        available_agents = self.get_contactable_agents_with_description()
        console.print("[bold blue]🤖 Available Agents:[/bold blue]")
        for agent_type, desc in available_agents.items():
            console.print(f"  [green]▪[/green] [cyan]{agent_type}:[/cyan] [dim]{desc}[/dim]")

        PROMPT = f"""
        You are an AI agent of type {self.TYPE} and name {self.name} in a multi-agent system. Your description is: {self.description}. Keep your responses concise.

        1. Direct User Messages:
        - When a user messages you directly, first try to respond using available context
        - If you need more information, use chat_with_agent to ask other agents
        - Once you have the information or need to respond, use contact_human to reply to the user
        - Don't explain your internal process, just respond naturally in your role

        2. Agent Messages (Pending Messages):
        - These appear in the format "Pending messages: <AgentType>: <message>"
        - If you can answer using available context, respond using chat_with_agent to that agent
        - If you need to ask your user, use contact_human and then inform the agent you're getting the information
        - When your user later provides the answer, send it to the requesting agent using chat_with_agent

        3. Using External Context:
        - Other Conversations: Last 7 messages from other agents' conversations
        - Format: "Other Conversations: <AgentType>:" followed by user/assistant messages
        - External conversations are provided for context only - DO NOT respond to them directly
        - Only use this information to enhance your understanding of the overall situation
        - If the information you need is already present in these external conversations, DO NOT use chat_with_agent to ask for it again
        - These are separate conversations happening in parallel - treat them as background knowledge only
        
        4. Available Agents for Communication:
        {available_agents}

        5. Key Points:
        - This is a simulation. There are no real emergencies.
        - Focus on your specific role and responsibilities
        - Only use chat_with_agent when you need information not in context
        - Use contact_human to respond to users or get information from your user

        Remember: Stay in character and refer to your description for your specific role and responsibilities.
        """
        return PROMPT

    async def process_chat_message(self, message: str = None, websockets: List[WebSocket] = []) -> Dict[str, Any]:
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

        # get the last 7 messages from all other agents' sessions 
        other_agent_messages = self._agent_manager.get_agent_messages(self.name, num_messages=7)
        message_full = f"{other_agent_messages}"
        if message:
            message_full += f"\n User: {message}"

        current_messages.append({"content": self.prompt_message(), "role": "system"})
        current_messages.append({"content": message_full, "role": "user"})

        # Make the API call
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=current_messages,
            tools=[tool for tool in self.tools if tool["function"]["name"] != "contact_human"],
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
        while tool_calls:
            available_functions = {
                "chat_with_agent": get_chat_with_agent_tool(),
                "contact_human": self.contact_human, # just in case the model chooses this
                **self._custom_functions  # Add custom functions to available functions
            }
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                try:
                    if function_name == "contact_human":
                        function_response = await function_to_call(**function_args, websockets=websockets)
                    else:
                        function_response = function_to_call(**function_args)
                        # Convert responses to appropriate string format
                        if isinstance(function_response, dict):
                            function_response = json.dumps(function_response)
                        elif isinstance(function_response, list):
                            function_response = [
                                json.dumps(item) if isinstance(item, dict) else str(item)
                                for item in function_response
                            ]
                except Exception as e:
                    print(f"Error calling function {function_name}: {e}")
                    continue

                func_resp = ""
                # make one str from the function_response list of str
                for resp in function_response:
                    func_resp += resp

                # console log the function called and its response in suitable formatting
                console.print(f"[bold green] 🛠️  Function called:[/bold green] {function_name}")
                console.print(f"[bold blue]Function response:[/bold blue] {func_resp}")

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

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=current_messages,
                tools=[tool for tool in self.tools if tool["function"]["name"] != "contact_human"],
                tool_choice="auto",
            )
            print(response.choices[0].message)
            tool_calls = response.choices[0].message.tool_calls

            # convert response_message ChatCompletionMessage to dict
            response_message = response.choices[0].message.model_dump()
            session_messages.append(response_message)
            current_messages.append(response_message)         

        # add the response to the session
        self._session.update_and_replace_messages(session_messages)

        # After processing, return the response and the list of all current agents that are active
        activated_agents = [agent for agent in self._agent_manager.get_all_agents() if agent.is_active() and agent.name != self.name]

        return {
            "response": response.choices[0].message.content,
            "activated_agents": [agent.name for agent in activated_agents]
        }


    async def process_queue_message(self, message: str = None, websockets: List[WebSocket] = []) -> None:
        """Process a message from the queue. 
        
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
        session_messages = self._session.messages
        current_messages = session_messages.copy()

        if message:
            queue_message = f"Pending messages: {message}"

        print(f"Queue message for {self.TYPE}: {queue_message}")

        session_messages.append({"content": queue_message, "role": "user"})
        current_messages.append({"content": self.prompt_message(), "role": "system"})
        current_messages.append({"content": queue_message, "role": "user"})

        # Make the API call
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=current_messages,
            tools=self.tools,
            tool_choice="auto",
        )

        print("In queue fn:", response.choices[0].message)

        # TODO support parallel function calling. we might want to add something like
        # broadcast message to all agents, and see who responds first.
        # if tools calls is not none, proceed
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # convert response_message ChatCompletionMessage to dict
        response_message = response_message.model_dump()
        current_messages.append(response_message)
        session_messages.append(response_message)
        while tool_calls:
            available_functions = {
                "chat_with_agent": get_chat_with_agent_tool(),
                "contact_human": self.contact_human,
                **self._custom_functions  # Add custom functions to available functions
            }
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                try:
                    if function_name == "contact_human":
                        function_response = await function_to_call(**function_args, websockets=websockets)
                    else:
                        function_response = function_to_call(**function_args)
                        # Convert responses to appropriate string format
                        if isinstance(function_response, dict):
                            function_response = json.dumps(function_response)
                        elif isinstance(function_response, list):
                            function_response = [
                                json.dumps(item) if isinstance(item, dict) else str(item)
                                for item in function_response
                            ]
                except Exception as e:
                    print(f"Error calling function {function_name}: {e}")
                    continue

                func_resp = ""
                # make one str from the function_response list of str
                for resp in function_response:
                    func_resp += resp

                # console log the function called and its response in suitable formatting
                console.print(f"[bold green] 🛠️  Function called:[/bold green] {function_name}")
                console.print(f"[bold blue] Function response:[/bold blue] {func_resp}")

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

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=current_messages,
                tools=self.tools,
                tool_choice="auto",
            )
            print("In queue fn:", response.choices[0].message)
            tool_calls = response.choices[0].message.tool_calls

            # convert response_message ChatCompletionMessage to dict
            response_message = response.choices[0].message.model_dump()
            session_messages.append(response_message)
            current_messages.append(response_message)         

        # add the response to the session
        self._session.update_and_replace_messages(session_messages)

        # After processing, return the response and the list of all current agents that are active
        activated_agents = [agent for agent in self._agent_manager.get_all_agents() if agent.is_active() and agent.name != self.name]
        print(f"Activated agents: {[agent.name for agent in activated_agents]}")

    async def _send_session_update(self, openai_ws: WebSocketClientProtocol) -> None:
        """Send the session update to the OpenAI WebSocket."""
        session_update = {
            "event_id": f"event_{self.TYPE}_{id(self)}",
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": self.prompt_message(),
                "voice": "ash",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                },
                "tools": [tool for tool in self.tools_for_realtime if tool["name"] != "contact_human"],
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
        except WebSocketDisconnect:
            print("Client disconnected.")
            if openai_ws.open:
                await openai_ws.close()

    async def _send_to_client(self, websocket: WebSocket, openai_ws: WebSocketClientProtocol) -> None:
        """Send a message to the client."""
        available_functions = {
            "chat_with_agent": get_chat_with_agent_tool(),
        }
        try:
            async for openai_message in openai_ws:
                # Add keepalive heartbeat
                await asyncio.sleep(0.1)  # Prevent event loop starvation
                response = json.loads(openai_message)
                print("Received message from OpenAI:", response)
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
                                "voice": "ash",
                                "output_audio_format": "pcm16",
                                "tools": self.tools_for_realtime,
                                "tool_choice": "required",
                                "temperature": 0.7,
                            }
                        }
                        await openai_ws.send(json.dumps(response_create))

                if response['type'] == 'conversation.item.input_audio_transcription.completed':
                    # get the transcription from the response
                    transcription = response['transcript']
                    console.print(f"[bold blue] User input transcription:[/bold blue] {transcription}")
                    # add the transcription to the session
                    self._session.add_message(transcription, "user")

                if response['type'] == 'response.audio_transcript.done':
                    # get the transcript from the response
                    transcript = response['transcript']
                    console.print(f"[bold green] Assistant audio transcript:[/bold green] {transcript}")
                    # add the transcript to the session
                    self._session.add_message(transcript, "assistant")
                    
        except Exception as e:
            print(f"Error in send_to_client: {e}")

    def add_message_to_queue(self, message: str, sender: str) -> None:
        """Add a message to the agent's queue."""
        self._queue.append(f"{sender}: {message}")

    def is_active(self) -> bool:
        """Check if the agent is active."""
        # if session is not None, then the agent is active
        return self._session is not None
    
    def activate(self, server_id: str = None, dependencies: Any = None) -> None:
        """Activate the agent."""
        self._session = Session(self.TYPE, server_id)

    def chat_with_agent(self, agent_name: str, question: str) -> str:
        """Chat with the agent of the given name."""
        agent = self._agent_manager.get_agent(agent_name)
        if not agent:
            return f"Error: Agent with name '{agent_name}' not found"
        
        # if agent is not active, activate it
        if not agent.is_active():
            agent.activate()
        # add the question to the agent's queue
        agent.add_message_to_queue(question, self.name)

        return (
            f"I have put the question '{question}' in the queue for the agent named {agent_name}. "
            "You will hear back soon."
        )
    
    async def contact_human(self, message: str, websockets: List[WebSocket] = []) -> None:
        """Respond to the human."""
        for ws in websockets:
            await ws.send_text(message)
        return f"I have sent your message to the human as I don't have the information in context."

    def _validate_tool_function(self, func: Callable, tool_name: str) -> None:
        """Validate that a tool function meets the required signature.
        
        Args:
            func: The function to validate
            tool_name: Name of the tool (for error messages)
            
        Raises:
            ToolFunctionError: If the function doesn't meet requirements
        """
        # Check if it's callable
        if not callable(func):
            raise ToolFunctionError(f"Tool function for '{tool_name}' must be callable")

        # Get return type hint
        return_type = get_type_hints(func).get('return')
        if return_type is None:
            raise ToolFunctionError(
                f"Tool function '{tool_name}' must have a return type hint of str, List[str], Dict, or List[Dict]"
            )

        # Validate return type
        valid_return_types = (str, List[str], Dict, dict, List[Dict], List[dict])
        if return_type not in valid_return_types and not (
            hasattr(return_type, "__origin__") and 
            (
                (return_type.__origin__ is list and return_type.__args__[0] in (str, Dict, dict)) or
                (return_type.__origin__ is dict)
            )
        ):
            raise ToolFunctionError(
                f"Tool function '{tool_name}' must return str, List[str], Dict, or List[Dict], "
                f"got {return_type}"
            )

    def _validate_tool_config(self, tool_config: Dict[str, Any]) -> None:
        """Validate the complete tool configuration.
        
        Args:
            tool_config: The tool configuration dictionary
            
        Raises:
            ToolFunctionError: If the configuration is invalid
        """
        if not isinstance(tool_config, dict):
            raise ToolFunctionError("Tool config must be a dictionary")
            
        if "tool" not in tool_config or "function" not in tool_config:
            raise ToolFunctionError(
                "Tool config must contain both 'tool' and 'function' keys"
            )
            
        tool = tool_config["tool"]
        func = tool_config["function"]
        
        if "function" not in tool or "name" not in tool["function"]:
            raise ToolFunctionError(
                "Tool configuration must have a 'function' property with a 'name' field"
            )
            
        tool_name = tool["function"]["name"]
        if tool_name in ["chat_with_agent", "contact_human"]:
            raise ToolFunctionError(
                f"Tool name '{tool_name}' is reserved for base tools"
            )
            
        # Validate the function
        self._validate_tool_function(func, tool_name)
