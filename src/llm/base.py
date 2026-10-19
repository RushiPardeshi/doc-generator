"""Abstract protocol and base types for LLM providers."""

from typing import Protocol, TypeVar, Type, Optional
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    """Protocol defining the unified interface for LLM completions."""

    def complete(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.2,
    ) -> str:
        """Generate a raw text completion."""
        ...

    def complete_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: str = "",
        temperature: float = 0.2,
    ) -> T:
        """Generate a structured completion validated against a Pydantic schema."""
        ...
