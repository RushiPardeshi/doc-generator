"""Google Gemini provider implementation using google-genai SDK with exponential backoff and fallback models."""

import time
from typing import Type, TypeVar, Optional, List, Callable, Any
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai import errors
from rich.console import Console

from src.config import GEMINI_API_KEY, GEMINI_MODEL
from src.llm.base import LLMProvider
from src.llm.tracker import token_tracker

console = Console()
T = TypeVar("T", bound=BaseModel)

FALLBACK_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite",
]


class GeminiProvider:
    """Gemini LLM Provider with automatic 503 high-demand retry and fallback model routing."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model or GEMINI_MODEL
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = genai.Client()

    def _execute_with_resilience(
        self,
        call_fn: Callable[[str], Any],
        max_retries_per_model: int = 3,
    ) -> Any:
        """
        Execute API call with exponential backoff for 503/429 errors.
        If a model is persistently unavailable (503 High Demand or 404 Deprecated), fall back to alternative models.
        """
        models_to_try = [self.model]
        for m in FALLBACK_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

        last_error = None
        for model in models_to_try:
            for attempt in range(max_retries_per_model):
                try:
                    return call_fn(model)
                except errors.ClientError as e:
                    last_error = e
                    if (
                        getattr(e, "code", None) in (404, 429)
                        or "404" in str(e)
                        or "429" in str(e)
                        or "resource_exhausted" in str(e).lower()
                        or "not found" in str(e).lower()
                        or "quota" in str(e).lower()
                    ):
                        console.print(f"[dim]• Model '{model}' quota/resource exhausted ({getattr(e, 'code', '4xx')}). Routing to next fallback model...[/dim]")
                        break
                    raise e
                except errors.ServerError as e:
                    last_error = e
                    if "503" in str(e) or "high demand" in str(e).lower() or getattr(e, "code", None) == 503:
                        delay = 2 ** (attempt + 1)
                        console.print(
                            f"[yellow]⚠ {model} experienced high demand (503). Retrying in {delay}s (attempt {attempt+1}/{max_retries_per_model})...[/yellow]"
                        )
                        time.sleep(delay)
                    else:
                        raise e
                except errors.APIError as e:
                    last_error = e
                    # Rate limit or quota spike
                    if getattr(e, "code", None) in (429, 503) or "429" in str(e) or "503" in str(e):
                        delay = 2 ** (attempt + 1)
                        console.print(
                            f"[yellow]⚠ Transient API error ({e}). Retrying in {delay}s...[/yellow]"
                        )
                        time.sleep(delay)
                    else:
                        raise e
                except Exception as e:
                    last_error = e
                    raise e

            console.print(f"[dim]• Switching from {model} to next model...[/dim]")

        raise RuntimeError(f"All Gemini models exhausted. Last error: {last_error}")

    def complete(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.2,
    ) -> str:
        """Generate plain text from Gemini with automatic retry and model fallback."""
        config_kwargs = {"temperature": temperature}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        config = types.GenerateContentConfig(**config_kwargs)

        def _call(model_name: str):
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if getattr(response, "usage_metadata", None):
                meta = response.usage_metadata
                token_tracker.record_usage(
                    model=model_name,
                    prompt_tokens=getattr(meta, "prompt_token_count", 0) or 0,
                    output_tokens=getattr(meta, "candidates_token_count", 0) or 0,
                    total_tokens=getattr(meta, "total_token_count", 0) or 0,
                )
            return response.text or ""

        return self._execute_with_resilience(_call)

    def complete_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: str = "",
        temperature: float = 0.2,
    ) -> T:
        """Generate structured output validated against a Pydantic model with automatic retry and fallback."""
        config_kwargs = {
            "temperature": temperature,
            "response_mime_type": "application/json",
            "response_json_schema": schema.model_json_schema(),
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        config = types.GenerateContentConfig(**config_kwargs)

        def _call(model_name: str):
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if getattr(response, "usage_metadata", None):
                meta = response.usage_metadata
                token_tracker.record_usage(
                    model=model_name,
                    prompt_tokens=getattr(meta, "prompt_token_count", 0) or 0,
                    output_tokens=getattr(meta, "candidates_token_count", 0) or 0,
                    total_tokens=getattr(meta, "total_token_count", 0) or 0,
                )
            raw_text = response.text or "{}"
            return schema.model_validate_json(raw_text)

        return self._execute_with_resilience(_call)
