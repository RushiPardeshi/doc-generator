"""LLM Provider factory and exports."""

from typing import Optional
from src.llm.base import LLMProvider
from src.llm.gemini import GeminiProvider
from src.llm.anthropic import AnthropicProvider
from src.config import DEFAULT_GENERATOR_PROVIDER


def get_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMProvider:
    """Instantiate and return the requested LLM provider."""
    name = (provider_name or DEFAULT_GENERATOR_PROVIDER).lower()
    if name in ("gemini", "google"):
        return GeminiProvider(api_key=api_key, model=model)
    elif name in ("anthropic", "claude"):
        return AnthropicProvider(api_key=api_key, model=model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_name}. Expected 'gemini' or 'anthropic'.")


__all__ = ["LLMProvider", "GeminiProvider", "AnthropicProvider", "get_provider"]
