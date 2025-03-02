import os
from typing import Dict, List, Any, Optional
import litellm
from rich.console import Console

console = Console()

class LLMConfig:
    """Configuration for LLM models using LiteLLM.
    
    This class handles the configuration of LLM models and providers,
    allowing for easy switching between different models and providers.
    """
    
    def __init__(self):
        """Initialize the LLM configuration.
        
        Reads environment variables to determine which model and provider to use.
        Falls back to defaults if not specified.
        """
        # Default model configuration
        self.default_model = "gpt-4o-mini"
        self.default_provider = "openai"
        
        # Read from environment variables
        self.model = os.getenv("MAHILO_LLM_MODEL", self.default_model)
        self.provider = os.getenv("MAHILO_LLM_PROVIDER", self.default_provider)
        
        # API keys and endpoints
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.azure_api_key = os.getenv("AZURE_API_KEY")
        self.azure_endpoint = os.getenv("AZURE_API_BASE")
        
        # Set up LiteLLM with the appropriate provider
        self._setup_litellm()
        
        # Log the configuration
        self._log_config()
    
    def _setup_litellm(self):
        """Configure LiteLLM with the appropriate provider and API keys."""
        # Set the default API keys for different providers
        if self.openai_api_key:
            litellm.openai_key = self.openai_api_key
        
        if self.anthropic_api_key:
            litellm.anthropic_key = self.anthropic_api_key
            
        if self.azure_api_key and self.azure_endpoint:
            litellm.azure_key = self.azure_api_key
            litellm.azure_endpoint = self.azure_endpoint
    
    def _log_config(self):
        """Log the current LLM configuration."""
        console.print(f"[bold blue]🤖 LLM Configuration:[/bold blue]")
        console.print(f"  [green]▪[/green] [cyan]Provider:[/cyan] [dim]{self.provider}[/dim]")
        console.print(f"  [green]▪[/green] [cyan]Model:[/cyan] [dim]{self.model}[/dim]")
    
    async def chat_completion(self, 
                       messages: List[Dict[str, Any]], 
                       model: Optional[str] = None,
                       tools: Optional[List[Dict[str, Any]]] = None,
                       tool_choice: Optional[str] = None,
                       temperature: float = 0.7,
                       **kwargs) -> Any:
        """Generate a chat completion using LiteLLM.
        
        Args:
            messages: List of message dictionaries with role and content
            model: Optional model override
            tools: Optional list of tools for function calling
            tool_choice: Optional tool choice setting
            temperature: Temperature for generation
            **kwargs: Additional arguments to pass to LiteLLM
            
        Returns:
            The response from the LLM
        """
        try:
            # Use the specified model or fall back to the configured one
            model_to_use = model or self.model
            
            # Prepare the request parameters
            params = {
                "model": model_to_use,
                "messages": messages,
                "temperature": temperature,
                **kwargs
            }
            
            # Add tools if provided
            if tools:
                params["tools"] = tools
                
            if tool_choice:
                params["tool_choice"] = tool_choice
            
            # Make the API call through LiteLLM
            response = await litellm.acompletion(**params)
            return response
            
        except Exception as e:
            console.print(f"[bold red]⛔ Error in LLM request:[/bold red] {str(e)}")
            # If there's an error with the specified model, try falling back to the default
            if model_to_use != self.default_model:
                console.print(f"[yellow]⚠️ Falling back to default model: {self.default_model}[/yellow]")
                return await self.chat_completion(
                    messages=messages,
                    model=self.default_model,
                    tools=tools,
                    tool_choice=tool_choice,
                    temperature=temperature,
                    **kwargs
                )
            raise e

# Create a singleton instance
llm_config = LLMConfig() 