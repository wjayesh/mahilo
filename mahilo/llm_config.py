"""
LLM Configuration module for Mahilo.

This module provides configuration for different LLM providers, including OpenAI and
other providers through litellm.
"""

import os
from typing import Dict, Any, Optional, Union, List
from enum import Enum
import json
from rich.console import Console

console = Console()

# Try to import litellm, but don't fail if it's not installed
try:
    import litellm
    from litellm import AsyncLiteLLM
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# Try to import OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class LLMProvider(str, Enum):
    """Enum for supported LLM providers."""
    OPENAI = "openai"
    LITELLM = "litellm"

class LLMConfig:
    """Configuration for LLM providers."""
    
    def __init__(
        self,
        provider: Union[LLMProvider, str] = None,
        model: str = None,
        api_key: str = None,
        api_base: str = None,
        additional_options: Dict[str, Any] = None
    ):
        """Initialize LLM configuration.
        
        Args:
            provider: LLM provider (openai or litellm)
            model: Model name to use
            api_key: API key for the provider
            api_base: Base URL for API calls
            additional_options: Additional provider-specific options
        """
        # Set provider, defaulting to environment variable or OpenAI
        self.provider = provider or os.getenv("MAHILO_LLM_PROVIDER", LLMProvider.OPENAI)
        if isinstance(self.provider, str):
            try:
                self.provider = LLMProvider(self.provider.lower())
            except ValueError:
                console.print(f"[bold yellow]Warning: Unknown provider '{provider}'. Defaulting to OpenAI.[/bold yellow]")
                self.provider = LLMProvider.OPENAI
        
        # Set model, defaulting to environment variable or gpt-4o-mini
        self.model = model or os.getenv("MAHILO_LLM_MODEL", "gpt-4o-mini")
        
        # Set API key based on provider
        if self.provider == LLMProvider.OPENAI:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        else:
            # For litellm, try provider-specific env var first, then fall back to OPENAI_API_KEY
            self.api_key = api_key or os.getenv(f"{self.model.upper().split('-')[0]}_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        # Set API base URL
        self.api_base = api_base
        if not self.api_base:
            if self.provider == LLMProvider.OPENAI:
                self.api_base = os.getenv("OPENAI_API_BASE")
            else:
                self.api_base = os.getenv(f"{self.model.upper().split('-')[0]}_API_BASE")
        
        # Additional options
        self.additional_options = additional_options or {}
        
        # Load additional options from environment if available
        env_options = os.getenv("MAHILO_LLM_OPTIONS")
        if env_options:
            try:
                self.additional_options.update(json.loads(env_options))
            except json.JSONDecodeError:
                console.print("[bold yellow]Warning: Could not parse MAHILO_LLM_OPTIONS as JSON.[/bold yellow]")
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate the configuration."""
        if self.provider == LLMProvider.LITELLM and not LITELLM_AVAILABLE:
            console.print("[bold yellow]Warning: litellm is not installed but provider is set to 'litellm'.[/bold yellow]")
            console.print("[bold yellow]Install litellm with: pip install litellm[/bold yellow]")
            console.print("[bold yellow]Falling back to OpenAI provider.[/bold yellow]")
            self.provider = LLMProvider.OPENAI
        
        if self.provider == LLMProvider.OPENAI and not OPENAI_AVAILABLE:
            console.print("[bold red]Error: OpenAI package is not installed.[/bold red]")
            console.print("[bold red]Install OpenAI with: pip install openai[/bold red]")
            raise ImportError("OpenAI package is required but not installed")
        
        if not self.api_key:
            if self.provider == LLMProvider.OPENAI:
                console.print("[bold red]Error: OPENAI_API_KEY environment variable is not set.[/bold red]")
                raise ValueError("OPENAI_API_KEY environment variable is required")
            else:
                console.print(f"[bold yellow]Warning: No API key found for provider '{self.provider}'.[/bold yellow]")
    
    def get_client(self):
        """Get the appropriate client based on the provider."""
        if self.provider == LLMProvider.OPENAI:
            client_options = {
                "api_key": self.api_key,
            }
            if self.api_base:
                client_options["base_url"] = self.api_base
            
            # Add any additional options
            client_options.update(self.additional_options)
            
            return AsyncOpenAI(**client_options)
        
        elif self.provider == LLMProvider.LITELLM:
            # For litellm, we return the AsyncLiteLLM client
            client_options = {
                "api_key": self.api_key,
            }
            if self.api_base:
                client_options["base_url"] = self.api_base
            
            # Add any additional options
            client_options.update(self.additional_options)
            
            return AsyncLiteLLM(**client_options)
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, Any]], 
        model: str = None, 
        tools: List[Dict[str, Any]] = None,
        tool_choice: str = None,
        **kwargs
    ):
        """Create a chat completion using the configured provider.
        
        Args:
            messages: List of messages for the conversation
            model: Override the default model
            tools: List of tools to use
            tool_choice: Tool choice strategy
            **kwargs: Additional arguments to pass to the provider
            
        Returns:
            The response from the provider
        """
        model_to_use = model or self.model
        
        if self.provider == LLMProvider.OPENAI:
            client = self.get_client()
            return await client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs
            )
        
        elif self.provider == LLMProvider.LITELLM:
            # For litellm, we use the AsyncLiteLLM client
            client = self.get_client()
            return await client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs
            )
        
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

# Create a default configuration
default_config = LLMConfig()