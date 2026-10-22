"""End-to-end investment reasoning pipeline with ablation support."""

from typing import List, Optional
from pydantic import BaseModel, Field

from src.reasoning.claims import GroundedClaim, extract_claims
from src.reasoning.debate import (
    CandidateThesis,
    DebateArbitrationResult,
    ThesisStance,
    generate_candidate_theses,
    run_premortem_debate,
)
from src.reasoning.minto import (
    MintoDraft,
    synthesize_minto_draft,
    format_minto_to_markdown,
)
from src.voice.linter import lint_memo, LintResult
from src.voice.traceability import verify_numerical_traceability, TraceabilityReport
from src.voice.editor import edit_memo
from src.llm.base import LLMProvider


class PipelineConfig(BaseModel):
    """Configuration for pipeline execution including ablation modes."""
    company_name: str = "Apex Systems"
    enable_debate: bool = True   # If False: ablation mode skipping multi-thesis debate & pre-mortem
    enable_voice: bool = True    # If False: ablation mode skipping editorial de-slopping pass


class PipelineResult(BaseModel):
    """Complete bundle returned by a pipeline execution."""
    final_memo: str
    company_name: str
    ablation_mode: str
    verified_claims: List[GroundedClaim]
    candidate_theses: Optional[List[CandidateThesis]] = None
    debate_result: Optional[DebateArbitrationResult] = None
    minto_draft: MintoDraft
    lint_result: LintResult
    traceability_report: TraceabilityReport


def run_pipeline(
    dossier_text: str,
    provider: LLMProvider,
    config: Optional[PipelineConfig] = None,
) -> PipelineResult:
    """
    Execute the multi-stage investment memo generation pipeline.
    
    Stages:
    1. Grounded Claim Extraction with verbatim string match invariant
    2. 360° Candidate Theses & Pre-Mortem Debate (if enable_debate=True)
    3. Grounded Minto Pyramid Synthesis
    4. Voice Editorial Pass & Numerical Traceability Guard (if enable_voice=True)
    """
    cfg = config or PipelineConfig()
    ablation_mode = "full"
    if not cfg.enable_debate and not cfg.enable_voice:
        ablation_mode = "no-debate-no-voice"
    elif not cfg.enable_debate:
        ablation_mode = "no-debate"
    elif not cfg.enable_voice:
        ablation_mode = "no-voice"

    from rich.console import Console
    from src.llm.tracker import token_tracker
    console = Console()

    # Stage 1: Claim Extraction & Invariant Verification
    console.print("   [cyan]• Stage 1/4: Extracting atomic claims & checking verbatim quotes...[/cyan]")
    token_tracker.set_current_stage("Stage 1: Grounded Claims Extraction")
    verified_claims, rejected_claims = extract_claims(dossier_text, provider)
    if not verified_claims:
        raise RuntimeError("No claims survived verbatim verification against source dossier.")
    console.print(f"     [green]✓ Extracted {len(verified_claims)} grounded claims ({len(rejected_claims)} discarded for quote mismatch)[/green]")

    # Stage 2: Theses & Pre-Mortem Debate (or fallback if ablated)
    candidate_theses: Optional[List[CandidateThesis]] = None
    debate_result: Optional[DebateArbitrationResult] = None
    selected_thesis: Optional[CandidateThesis] = None
    stance = ThesisStance.BUY

    if cfg.enable_debate:
        console.print("   [cyan]• Stage 2/4: Formulating 3 candidate theses (BUY, CONDITIONAL, PASS)...[/cyan]")
        token_tracker.set_current_stage("Stage 2a: 360° Candidate Theses")
        candidate_theses = generate_candidate_theses(verified_claims, provider)
        for t in candidate_theses:
            console.print(f"     - [{t.stance.value}] {t.headline}")

        console.print("   [cyan]• Stage 2b: Running adversarial 3-year pre-mortem attack (Du et al., 2023)...[/cyan]")
        token_tracker.set_current_stage("Stage 2b: Pre-Mortem Adversarial Debate")
        debate_result = run_premortem_debate(candidate_theses, verified_claims, provider)
        stance = debate_result.final_stance
        console.print(f"     [green]✓ Pre-mortem complete: Selected [{stance.value}][/green]")

        if debate_result.selected_thesis_id:
            for t in candidate_theses:
                if t.id == debate_result.selected_thesis_id:
                    selected_thesis = t
                    break
    else:
        # Ablated mode: default to simple first-order conviction without adversarial pre-mortem
        stance = ThesisStance.RECOMMEND
        selected_thesis = CandidateThesis(
            id="T_ABLATED",
            stance=ThesisStance.RECOMMEND,
            headline=f"Proceed with {cfg.company_name} based on primary empirical findings and verified metrics",
            core_mechanism="Substantiated by verified claims and core metrics",
            supporting_claim_ids=[c.id for c in verified_claims[:3]],
            primary_vulnerability="Key structural bottlenecks or counter-evidence",
        )

    # Stage 3: Grounded Minto Synthesis
    console.print("   [cyan]• Stage 3/4: Synthesizing Answer-First Minto Pyramid draft...[/cyan]")
    token_tracker.set_current_stage("Stage 3: Answer-First Minto Synthesis")
    minto_draft = synthesize_minto_draft(
        company_name=cfg.company_name,
        stance=stance,
        selected_thesis=selected_thesis,
        debate_result=debate_result if debate_result else DebateArbitrationResult(
            attacks=[],
            selected_thesis_id="T_ABLATED",
            final_stance=ThesisStance.BUY,
            arbitration_summary="Ablation run: pre-mortem bypassed.",
        ),
        claims=verified_claims,
        provider=provider,
    )
    draft_markdown = format_minto_to_markdown(minto_draft)

    # Stage 4: Voice Editorial Pass & Traceability Guard
    if cfg.enable_voice:
        console.print("   [cyan]• Stage 4/4: Executing editorial de-slopping & strict numerical traceability...[/cyan]")
        token_tracker.set_current_stage("Stage 4: Voice Editorial De-slopping")
        final_memo, lint_result, traceability = edit_memo(
            draft_markdown=draft_markdown,
            claims=verified_claims,
            provider=provider,
        )
        status_str = "[green]PASSED[/green]" if traceability.is_valid else "[red]FAILED[/red]"
        console.print(f"     [green]✓ De-slopping complete (Slop Score: {lint_result.slop_score:.1f}/100 | Traceability: {status_str})[/green]")
    else:
        # Ablated mode: return raw Minto draft without stylistic rewriting
        final_memo = draft_markdown
        lint_result = lint_memo(draft_markdown)
        traceability = verify_numerical_traceability(draft_markdown, verified_claims)

    return PipelineResult(
        final_memo=final_memo,
        company_name=cfg.company_name,
        ablation_mode=ablation_mode,
        verified_claims=verified_claims,
        candidate_theses=candidate_theses,
        debate_result=debate_result,
        minto_draft=minto_draft,
        lint_result=lint_result,
        traceability_report=traceability,
    )
