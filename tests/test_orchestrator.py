"""Integration tests for the complete thinking orchestrator."""

from typing import Type, TypeVar
from pydantic import BaseModel
from src.routing.models import QueryCategory
from src.orchestrator import run_thinking_process
from src.llm.base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider:
    """Mock LLM Provider for unit testing."""
    def complete(self, prompt: str, system_instruction: str = "", temperature: float = 0.2) -> str:
        if "principal investment analyst" in system_instruction.lower():
            return "Recommendation: BUY. Apex Systems displays strong moat durability and expanding margins."
        return "Objective research synthesis. The empirical findings indicate 3.2x speedup without degradation."

    def complete_structured(self, prompt: str, schema: Type[T], system_instruction: str = "", temperature: float = 0.2) -> T:
        pass


def test_orchestrator_company_flow():
    mock_provider = MockLLMProvider()
    result = run_thinking_process(
        query="NVDA",
        provider=mock_provider,
        fmp_key="mock_synthetic_fmp_token_12345",
    )
    assert result.decision.category == QueryCategory.COMPANY
    assert result.decision.allow_recommendations is True
    assert result.financial_metrics is not None
    assert result.financial_metrics.ticker == "NVDA"
    assert "Recommendation: BUY" in result.output_text


def test_orchestrator_topic_flow():
    mock_provider = MockLLMProvider()
    result = run_thinking_process(
        query="Quantum error correction in topological qubits",
        provider=mock_provider,
        serpapi_key="mock_synthetic_serpapi_token_12345",
    )
    assert result.decision.category == QueryCategory.TOPIC
    assert result.decision.allow_recommendations is False
    assert len(result.references) > 0
    assert result.guardrail_passed is True
    assert "Objective research synthesis" in result.output_text


def test_orchestrator_ambiguous_flow():
    mock_provider = MockLLMProvider()
    result = run_thinking_process(
        query="Mercury",
        provider=mock_provider,
    )
    assert result.decision.category == QueryCategory.AMBIGUOUS
    assert "Clarification Required" in result.output_text
    assert result.decision.disambiguation_options is not None
