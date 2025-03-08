# Multi-provider LLM Support with LiteLLM

Mahilo now supports multiple LLM providers through [LiteLLM](https://github.com/BerriAI/litellm), allowing you to easily switch between different models and providers.

## Configuration

The LLM configuration is managed through the `LLMConfig` class in `mahilo/llm_config.py`. This class handles the setup of LiteLLM with the appropriate API keys.

### Environment Variables

You can configure the LLM model using the following environment variable:

- `MAHILO_LLM_MODEL`: The model to use in the format `provider/model` (default: "openai/gpt-4o-mini")

The provider is specified as part of the model name, following LiteLLM's convention. For example:
- `openai/gpt-4o` for OpenAI's GPT-4o
- `anthropic/claude-3-opus-20240229` for Anthropic's Claude
- `azure/your-deployment-name` for Azure OpenAI

### API Keys

API keys for different providers can be set via environment variables:

- `OPENAI_API_KEY`: For OpenAI models
- `ANTHROPIC_API_KEY`: For Anthropic models
- `AZURE_API_KEY` and `AZURE_API_BASE`: For Azure OpenAI models

## Supported Providers

LiteLLM supports a wide range of providers, including:

- OpenAI
- Anthropic
- Azure OpenAI
- Google AI (Gemini)
- Cohere
- Mistral AI
- And many more

For a complete list of supported providers, see the [LiteLLM documentation](https://docs.litellm.ai/docs/providers).

## Usage

The LLM configuration is automatically loaded when Mahilo starts. You don't need to make any changes to your code to use different models or providers - just set the appropriate environment variables.

### Example

```bash
# Use OpenAI's GPT-4o
export MAHILO_LLM_MODEL="openai/gpt-4o"
export OPENAI_API_KEY="your-openai-api-key"

# Use Anthropic's Claude
export MAHILO_LLM_MODEL="anthropic/claude-3-opus-20240229"
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Use Azure OpenAI
export MAHILO_LLM_MODEL="azure/your-deployment-name"
export AZURE_API_KEY="your-azure-api-key"
export AZURE_API_BASE="https://your-resource-name.openai.azure.com"
```

## Fallback Mechanism

If there's an error with the specified model, Mahilo will automatically try to fall back to the default model (openai/gpt-4o-mini). This ensures that your application continues to work even if there are issues with the configured model.

## Advanced Configuration

For advanced configuration options, you can modify the `LLMConfig` class in `mahilo/llm_config.py`. This allows you to customize the behavior of LiteLLM, such as adding custom headers, setting timeouts, or configuring caching. 