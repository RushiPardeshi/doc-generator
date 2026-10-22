"""Symmetrical Mega-Prompt Baseline for fair benchmarking against multi-stage pipeline."""

from typing import Tuple
from src.llm.base import LLMProvider
from src.voice.linter import lint_memo, LintResult

BASELINE_MEGA_PROMPT = """You are a senior decision-maker and lead analyst writing an Executive Research & Decision Memo based on the research dossier below.

REQUIRED STRUCTURE (Minto's Pyramid Principle):
1. Executive Thesis (Answer-First): State the core decision or conclusion (RECOMMEND/BUY, CONDITIONAL, or REJECT/PASS) and the central thesis immediately.
2. 3 Supporting Pillars: Provide exactly 3 distinct structural arguments backing the thesis, citing specific figures and verified evidence from the research.
3. Key Risks & Pre-Mortem: Unvarnished failure modes explaining how this thesis or project could fail catastrophically in practice.
4. What Would Change My Mind: Quantitative or empirical falsification triggers that would immediately invalidate your thesis.

WRITING STYLE DIRECTIVE:
- Write with high conviction and active verbs.
- Ground every claim in specific metrics and empirical facts from the text.
- Avoid throat-clearing openings and conversational filler.
- Do NOT use AI clichés such as "not only X, but also Y", "testament to", "delve", "landscape", "poised to", or "tapestry".
- Minimize em-dashes and avoid symmetrical rule-of-three triplets.

RESEARCH DOSSIER:
\"\"\"
{dossier_text}
\"\"\"

Output the complete, final research and decision memo in clean markdown.
"""


def run_baseline(
    dossier_text: str,
    provider: LLMProvider,
) -> Tuple[str, LintResult]:
    """
    Generate an executive decision memo using a single competitive mega-prompt.
    Provides the exact same instructions and constraints as the multi-stage pipeline.
    """
    from src.llm.tracker import token_tracker
    token_tracker.set_current_stage("1/3 Mega-Prompt Baseline")

    prompt = BASELINE_MEGA_PROMPT.format(dossier_text=dossier_text)
    raw_memo = provider.complete(
        prompt=prompt,
        system_instruction="You are an elite analytical decision-maker drafting a high-conviction memo.",
        temperature=0.2,
    )
    lint_result = lint_memo(raw_memo)
    return raw_memo, lint_result
