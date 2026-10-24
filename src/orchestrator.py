"""Unified thinking process orchestrator routing queries to tailored analytical pipelines."""

from typing import Optional, List, Dict, Any, Callable
from pydantic import BaseModel, Field

from src.routing.models import QueryCategory, RoutingDecision
from src.routing.classifier import classify_query
from src.tools.financial_metrics import (
    CompanyFinancialMetrics,
    fetch_financial_metrics,
)
from src.tools.serp_research import (
    ResearchReference,
    fetch_authoritative_research,
    compile_references_to_dossier_section,
)
from src.templates.registry import get_template_for_category
from src.templates.guardrail import (
    verify_recommendation_guardrail,
    scrub_recommendations_if_present,
)
from src.llm.base import LLMProvider


class OrchestratorResult(BaseModel):
    """The structured result emitted by the thinking orchestrator."""
    query: str
    decision: RoutingDecision
    output_text: str
    financial_metrics: Optional[CompanyFinancialMetrics] = None
    references: List[ResearchReference] = Field(default_factory=list)
    guardrail_passed: bool = True
    guardrail_violations: List[str] = Field(default_factory=list)


class AssembledContentBundle(BaseModel):
    """The complete combination of routing decision, retrieved data, and assembled prompt ready for local validation."""
    query: str
    decision: RoutingDecision
    system_instruction: str
    assembled_prompt: str
    financial_metrics: Optional[CompanyFinancialMetrics] = None
    references: List[ResearchReference] = Field(default_factory=list)
    output_text: Optional[str] = None
    guardrail_passed: bool = True
    guardrail_violations: List[str] = Field(default_factory=list)


def assemble_content_bundle(
    query: str,
    provider: Optional[LLMProvider] = None,
    serpapi_key: Optional[str] = None,
    fmp_key: Optional[str] = None,
    generate_output: bool = False,
    progress_callback: Optional[Callable[[str, str, int, int], None]] = None,
) -> AssembledContentBundle:
    """
    Assemble the complete combination payload:
    1. Routing Decision
    2. Live 3rd Party Data (Financial Metrics or Scholar Citations)
    3. Fully Assembled Prompt + Category System Instruction
    4. Optional LLM Output generation and guardrail check
    """
    if progress_callback:
        progress_callback("router", f"Analyzing query intent for: '{query}'...", 1, 4)

    # Step 1: Classify query
    decision = classify_query(query, provider)

    # Step 2: Handle Ambiguous queries immediately
    if decision.category == QueryCategory.AMBIGUOUS:
        opts = "\n".join(f"- {opt}" for opt in (decision.disambiguation_options or []))
        disambig_text = (
            f"### Clarification Required for: '{query}'\n\n"
            f"The input term is ambiguous. Please clarify your specific objective:\n\n"
            f"{opts}\n\n"
            f"*Please reply with your target company ticker or full research topic to proceed.*"
        )
        return AssembledContentBundle(
            query=query,
            decision=decision,
            system_instruction="Clarification and disambiguation protocol.",
            assembled_prompt=f"Clarification requested for '{query}'",
            output_text=disambig_text,
            guardrail_passed=True,
        )

    # Step 3: Fetch Data based on category
    financial_metrics: Optional[CompanyFinancialMetrics] = None
    references: List[ResearchReference] = []

    template = get_template_for_category(decision.category)
    entity_name = decision.primary_entities[0] if decision.primary_entities else query

    if decision.category == QueryCategory.COMPANY:
        if progress_callback:
            progress_callback("fetch_metrics", f"Fetching real-time financial metrics for {entity_name}...", 2, 4)

        ticker = decision.tickers[0] if decision.tickers else entity_name
        financial_metrics = fetch_financial_metrics(ticker, api_key=fmp_key)
        metrics_table = financial_metrics.format_as_markdown()

        user_prompt = f"""Conduct a disciplined investment analysis on {entity_name} using the following real-time data:

{metrics_table}

Follow this exact structure:
{template.output_guidelines.format(entity=entity_name, financial_metrics_table=metrics_table)}
"""

    elif decision.category == QueryCategory.TOPIC:
        if progress_callback:
            progress_callback("fetch_scholar", f"Retrieving verified scholarly research on '{entity_name}'...", 2, 4)

        references = fetch_authoritative_research(entity_name, serpapi_key=serpapi_key)
        ref_section = compile_references_to_dossier_section(references)

        user_prompt = f"""Synthesize the empirical literature on the research topic: "{entity_name}".

GROUNDING REFERENCES:
{ref_section}

CRITICAL REQUIREMENT:
DO NOT recommend any suggestions, actions, investment thesis, or advice.
Maintain strict scientific objectivity.

Follow this exact structure:
{template.output_guidelines.format(entity=entity_name, references_section=ref_section)}
"""

    elif decision.category == QueryCategory.INDUSTRY:
        if progress_callback:
            progress_callback("fetch_industry", f"Gathering market landscape data for '{entity_name}'...", 2, 4)
        references = fetch_authoritative_research(entity_name, serpapi_key=serpapi_key)
        ref_section = compile_references_to_dossier_section(references)
        user_prompt = f"""Provide an objective industry landscape analysis for: "{entity_name}".

CONTEXT & REFERENCES:
{ref_section}

Follow this exact structure:
{template.output_guidelines.format(entity=entity_name)}
"""

    elif decision.category == QueryCategory.COMPARISON:
        if progress_callback:
            progress_callback("fetch_comparison", f"Gathering comparative benchmarks for '{entity_name}'...", 2, 4)
        user_prompt = f"""Conduct a head-to-head comparative analysis of: "{entity_name}".

Follow this exact structure:
{template.output_guidelines.format(entity=entity_name)}
"""

    else:  # MACRO
        if progress_callback:
            progress_callback("fetch_macro", f"Analyzing transmission channels for '{entity_name}'...", 2, 4)
        user_prompt = f"""Analyze the macroeconomic policy and market transmission for: "{entity_name}".

Follow this exact structure:
{template.output_guidelines.format(entity=entity_name)}
"""

    output_text = None
    is_valid = True
    violations = []

    if generate_output and provider:
        if progress_callback:
            progress_callback("synthesizing", f"Synthesizing structured {template.title}...", 3, 4)

        raw_output = provider.complete(
            prompt=user_prompt,
            system_instruction=template.system_instruction,
            temperature=0.15,
        )

        if progress_callback:
            progress_callback("guardrail", "Running recommendation guardrail validation...", 4, 4)

        is_valid, violations = verify_recommendation_guardrail(raw_output, decision.category)
        final_text = raw_output
        if not is_valid and not decision.allow_recommendations:
            final_text = scrub_recommendations_if_present(raw_output)
        output_text = final_text

    return AssembledContentBundle(
        query=query,
        decision=decision,
        system_instruction=template.system_instruction,
        assembled_prompt=user_prompt,
        financial_metrics=financial_metrics,
        references=references,
        output_text=output_text,
        guardrail_passed=is_valid,
        guardrail_violations=violations,
    )


def run_thinking_process(
    query: str,
    provider: LLMProvider,
    serpapi_key: Optional[str] = None,
    fmp_key: Optional[str] = None,
    progress_callback: Optional[Callable[[str, str, int, int], None]] = None,
) -> OrchestratorResult:
    """
    Execute the full thinking process:
    1. Check what is asked of the system (Company vs Topic vs Other) via Intent Routing.
    2. If Ambiguous, emit disambiguation guidance immediately.
    3. If Company, fetch live financial metrics & execute an investment thesis pipeline.
    4. If Topic, fetch scholarly references & execute a pure objective synthesis with ZERO suggestions.
    5. If Other (Industry, Comparison, Macro), execute tailored frameworks.
    6. Run post-generation guardrails to ensure no recommendation leakage.
    """
    bundle = assemble_content_bundle(
        query=query,
        provider=provider,
        serpapi_key=serpapi_key,
        fmp_key=fmp_key,
        generate_output=True,
        progress_callback=progress_callback,
    )
    return OrchestratorResult(
        query=bundle.query,
        decision=bundle.decision,
        output_text=bundle.output_text or "",
        financial_metrics=bundle.financial_metrics,
        references=bundle.references,
        guardrail_passed=bundle.guardrail_passed,
        guardrail_violations=bundle.guardrail_violations,
    )


if __name__ == "__main__":
    import sys
    from rich.console import Console
    from rich.panel import Panel
    from src.llm.gemini import GeminiProvider

    cli_console = Console()
    query_arg = sys.argv[1] if len(sys.argv) > 1 else "NVDA"

    cli_console.print(f"\n[bold blue]Thinking Process Running for:[/bold blue] '{query_arg}'\n")
    provider_inst = GeminiProvider()

    def _cli_progress(key: str, msg: str, step: int, total: int):
        cli_console.print(f"[dim]• [{step}/{total}] {msg}[/dim]")

    res = run_thinking_process(query_arg, provider_inst, progress_callback=_cli_progress)

    cli_console.print(Panel(
        f"[bold]Category:[/bold] {res.decision.category.value.upper()}\n"
        f"[bold]Allow Recommendations:[/bold] {res.decision.allow_recommendations}\n"
        f"[bold]Reasoning:[/bold] {res.decision.reasoning}\n"
        f"[bold]Guardrail Passed:[/bold] {res.guardrail_passed}",
        title="Routing & Decision Metadata",
        border_style="cyan",
    ))

    cli_console.print(Panel(res.output_text, title=f"Synthesized Output: {res.decision.category.value}", border_style="green"))

