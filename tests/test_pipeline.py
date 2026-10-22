"""End-to-end integration test with mock provider verifying all pipeline stages."""

import pytest
from src.llm.base import LLMProvider
from src.pipeline import run_pipeline, PipelineConfig
from src.reasoning.claims import GroundedClaim, ClaimType, ClaimsExtractionResult
from src.reasoning.debate import (
    ThesesGenerationResult,
    CandidateThesis,
    ThesisStance,
    DebateArbitrationResult,
    PreMortemAttack,
)
from src.reasoning.minto import MintoDraft, MintoPillar


class MockLLMProvider:
    """Deterministic Mock LLM provider for zero-cost integration testing."""

    def complete(self, prompt: str, system_instruction: str = "", temperature: float = 0.2) -> str:
        # Mocking the editorial pass or baseline completion
        return """
# Investment Memo: Apex Systems
**Recommendation**: `BUY`

## 1. Executive Thesis (Answer-First)
Apex is a compelling infrastructure buy. The company generates $153.3 million in revenue with 146% net retention.

## 2. Supporting Investment Pillars
### Pillar 1: High Net Retention
Apex maintains a 146% dollar-based net retention rate driven by 590 enterprise customers paying over $100,000 [C4].

### Pillar 2: Cash Flow Generation
Apex generated $10.9 million in operating cash flow in H1 2019 [C2].

### Pillar 3: Multi-Product Expansion
40% of customers utilize two or more modules [C3].

## 3. Structural Risks & Pre-Mortem Failure Modes
- AWS CloudWatch native bundled competition.

## 4. What Would Change My Mind (Falsification Criteria)
- If dollar-based net retention falls from 146% below 130%.
"""

    def complete_structured(self, prompt: str, schema, system_instruction: str = "", temperature: float = 0.2):
        if schema == ClaimsExtractionResult:
            return ClaimsExtractionResult(
                claims=[
                    GroundedClaim(
                        id="C1",
                        claim_type=ClaimType.FACT,
                        statement="Revenue was $153.3 million, up 79% YoY",
                        source_quote="Revenue for the six months ended June 30, 2019 was $153.3 million, up 79% from $85.4 million for the six months ended June 30, 2018.",
                        metric_or_data="$153.3 million",
                        entity_names=["Apex"],
                    ),
                    GroundedClaim(
                        id="C2",
                        claim_type=ClaimType.FACT,
                        statement="Apex generated positive operating cash flow of $10.9 million",
                        source_quote="Apex generated positive operating cash flow of $10.9 million for the six months ended June 30, 2019, up from $3.2 million in the prior year period.",
                        metric_or_data="$10.9 million",
                        entity_names=["Apex"],
                    ),
                    GroundedClaim(
                        id="C3",
                        claim_type=ClaimType.FACT,
                        statement="40% of customers used two or more products",
                        source_quote="As of June 30, 2019, approximately 40% of Apex customers used two or more products, compared to approximately 15% as of June 30, 2018.",
                        metric_or_data="40%",
                        entity_names=["Apex"],
                    ),
                    GroundedClaim(
                        id="C4",
                        claim_type=ClaimType.FACT,
                        statement="Customers with ARR of $100,000 or more reached 590",
                        source_quote="Customers with Annual Recurring Revenue (ARR) of $100,000 or more reached 590 as of June 30, 2019, up from 308 as of June 30, 2018.",
                        metric_or_data="590",
                        entity_names=["Apex"],
                    ),
                    GroundedClaim(
                        id="C5",
                        claim_type=ClaimType.FACT,
                        statement="Dollar-based net retention rate was 146% and historically exceeded 130%",
                        source_quote="Dollar-based net retention rate was 146% as of June 30, 2019, and has consistently exceeded 130% across historical quarters.",
                        metric_or_data="146%",
                        entity_names=["Apex"],
                    ),
                ]
            )
        elif schema == ThesesGenerationResult:
            return ThesesGenerationResult(
                theses=[
                    CandidateThesis(
                        id="T1",
                        stance=ThesisStance.BUY,
                        headline="Apex multi-product expansion creates an insurmountable observability moat",
                        core_mechanism="Multi-product NRR expansion",
                        supporting_claim_ids=["C1", "C3"],
                        primary_vulnerability="AWS CloudWatch native bundling",
                    ),
                    CandidateThesis(
                        id="T2",
                        stance=ThesisStance.CONDITIONAL,
                        headline="Apex is investable only if cloud hosting gross margins remain above 75%",
                        core_mechanism="Gross margin defensibility",
                        supporting_claim_ids=["C1", "C2"],
                        primary_vulnerability="AWS egress pricing spikes",
                    ),
                    CandidateThesis(
                        id="T3",
                        stance=ThesisStance.PASS,
                        headline="Avoid Apex due to long-term commoditization by hyperscaler cloud consoles",
                        core_mechanism="Public cloud vendor consolidation",
                        supporting_claim_ids=["C1"],
                        primary_vulnerability="Decelerating enterprise cloud migrations",
                    ),
                ]
            )
        elif schema == DebateArbitrationResult:
            return DebateArbitrationResult(
                attacks=[
                    PreMortemAttack(
                        thesis_id="T1",
                        fatal_failure_narrative="AWS bundles APM for free; customer growth decelerates.",
                        survived=True,
                        survival_score=8.5,
                        fatal_flaws=["Hosting reliance on AWS"],
                        falsification_triggers=["If NRR drops below 120%"],
                    )
                ],
                selected_thesis_id="T1",
                final_stance=ThesisStance.BUY,
                arbitration_summary="Thesis T1 survived due to proven 40% multi-product cross-selling.",
            )
        elif schema == MintoDraft:
            return MintoDraft(
                company_name="Apex Systems",
                recommendation=ThesisStance.BUY,
                executive_thesis="Apex represents an exceptional buy driven by $153.3 million in revenue and 146% NRR.",
                pillar_1=MintoPillar(
                    headline="Multi-Product Flywheel",
                    argument="Apex expands within customer accounts [C1].",
                    cited_claim_ids=["C1"],
                    metrics_cited=["$153.3 million"],
                ),
                pillar_2=MintoPillar(
                    headline="Operating Cash Flow",
                    argument="Apex generated $10.9 million in operating cash flow [C2].",
                    cited_claim_ids=["C2"],
                    metrics_cited=["$10.9 million"],
                ),
                pillar_3=MintoPillar(
                    headline="Product Cross-Selling",
                    argument="40% of customers adopt multiple modules [C3].",
                    cited_claim_ids=["C3"],
                    metrics_cited=["40%"],
                ),
                key_risks=["AWS native bundling", "Gross margin vulnerability"],
                what_would_change_my_mind=["If net retention rate drops below 120%"],
            )

        raise ValueError(f"Unrecognized schema in MockLLMProvider: {schema}")


def test_end_to_end_pipeline_execution():
    from pathlib import Path
    dossier_text = Path("data/dossiers/apex_observability_2019.md").read_text()
    provider = MockLLMProvider()

    result = run_pipeline(
        dossier_text=dossier_text,
        provider=provider,
        config=PipelineConfig(company_name="Apex Systems", enable_debate=True, enable_voice=True),
    )

    assert result.company_name == "Apex Systems"
    assert result.ablation_mode == "full"
    assert len(result.verified_claims) >= 3
    assert result.candidate_theses is not None
    assert result.debate_result is not None
    assert result.traceability_report.is_valid is True
    assert result.lint_result.is_acceptable is True
    assert "Investment Memo: Apex Systems" in result.final_memo


def test_pipeline_execution_with_progress_callback():
    from pathlib import Path
    dossier_text = Path("data/dossiers/apex_observability_2019.md").read_text()
    provider = MockLLMProvider()

    events = []

    def callback(stage_key, message, step, total_steps, data):
        events.append((stage_key, message, step, total_steps, data))

    result = run_pipeline(
        dossier_text=dossier_text,
        provider=provider,
        config=PipelineConfig(company_name="Apex Systems", enable_debate=True, enable_voice=True),
        progress_callback=callback,
    )

    assert result.company_name == "Apex Systems"
    voice_done_events = [e for e in events if e[0] == "voice_done"]
    assert len(voice_done_events) == 1
    assert "untraced_count" in voice_done_events[0][4]
    assert voice_done_events[0][4]["untraced_count"] == 0
