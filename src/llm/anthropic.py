"""Anthropic Claude provider implementation with automatic model fallback."""

from typing import Type, TypeVar, Optional, List, Callable, Any
from pydantic import BaseModel
import anthropic
from rich.console import Console

from src.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from src.llm.base import LLMProvider
from src.llm.tracker import token_tracker

console = Console()
T = TypeVar("T", bound=BaseModel)

ANTHROPIC_FALLBACK_MODELS = [
    "claude-sonnet-4-6",
    "claude-sonnet-5",
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5-20250929",
]


class AnthropicProvider:
    """Anthropic LLM Provider supporting raw text and structured Pydantic schemas via tool use."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.model = model or ANTHROPIC_MODEL
        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY in .env or pass it to AnthropicProvider."
            )
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def _execute_with_resilience(self, call_fn: Callable[[str], Any]) -> Any:
        models_to_try = [self.model]
        for m in ANTHROPIC_FALLBACK_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = None
        for model in models_to_try:
            try:
                return call_fn(model)
            except anthropic.NotFoundError as e:
                last_error = e
                console.print(f"[dim]• Anthropic model '{model}' not found (404). Falling back to next model...[/dim]")
                continue
            except anthropic.RateLimitError as e:
                last_error = e
                console.print(f"[yellow]⚠ Anthropic rate limit on {model}. Retrying with next model...[/yellow]")
                continue
            except Exception as e:
                last_error = e
                raise e

        raise RuntimeError(f"All Anthropic models exhausted. Last error: {last_error}")

    def complete(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> str:
        """Generate plain text from Claude."""
        def _call(model_name: str) -> str:
            kwargs = {
                "model": model_name,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                "extra_body": {"temperature": temperature},
            }
            if system_instruction:
                kwargs["system"] = system_instruction

            message = self.client.messages.create(**kwargs)
            if getattr(message, "usage", None):
                usage = message.usage
                token_tracker.record_usage(
                    model=model_name,
                    prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
                    output_tokens=getattr(usage, "output_tokens", 0) or 0,
                )
            text_parts = [
                block.text for block in message.content if getattr(block, "type", None) == "text"
            ]
            return "".join(text_parts)

        return self._execute_with_resilience(_call)

    def complete_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: str = "",
        temperature: float = 0.2,
        max_tokens: int = 8192,
    ) -> T:
        """Generate structured output validated against a Pydantic model via forced tool calling."""
        tool_name = "extract_structured_data"
        tools = [
            {
                "name": tool_name,
                "description": f"Output schema matching {schema.__name__}",
                "input_schema": schema.model_json_schema(),
            }
        ]

        def _call(model_name: str) -> T:
            kwargs = {
                "model": model_name,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                "tools": tools,
                "tool_choice": {"type": "tool", "name": tool_name},
                "extra_body": {"temperature": temperature},
            }
            if system_instruction:
                kwargs["system"] = system_instruction

            message = self.client.messages.create(**kwargs)
            if getattr(message, "usage", None):
                usage = message.usage
                token_tracker.record_usage(
                    model=model_name,
                    prompt_tokens=getattr(usage, "input_tokens", 0) or 0,
                    output_tokens=getattr(usage, "output_tokens", 0) or 0,
                )
            for block in message.content:
                if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
                    return schema.model_validate(block.input)

            raise RuntimeError(f"Claude failed to return a tool call for {tool_name}")

        return self._execute_with_resilience(_call)
