"""Editorial pass: rewrites draft memo to eliminate AI slop while strictly maintaining numerical traceability."""

from typing import List, Tuple
from src.reasoning.claims import GroundedClaim
from src.voice.linter import lint_memo, LintResult
from src.voice.traceability import verify_numerical_traceability, TraceabilityReport
from src.llm.base import LLMProvider

STYLE_DIRECTIVE = """You are an exacting senior editor and lead research director editing an executive research & decision memo.
Your mandate is to eliminate every trace of generic AI writing and replace it with crisp, understated, authoritative analytical prose.

STYLE INVARIANTS:
1. HARD NUMERICAL TRACEABILITY: You are STRICTLY FORBIDDEN from inventing any numbers, percentages, multiples, measurements, or dollar amounts. You must preserve the exact verified metrics from the input and cited claims.
2. ZERO THROAT-CLEARING: Delete all introductory warm-ups ("X represents an attractive...", "In today's digital landscape...", "It is worth noting that..."). Start immediately with the active assertion.
3. BANNED CLICHÉS: Never use "not only X, but also Y", "testament to", "delve", "tapestry", "landscape", "poised to", "holistic", or "pivotal".
4. PUNCTUATION DISCIPLINE: Minimize em-dashes (at most 1 in the entire memo). Use standard periods. Avoid symmetrical rule-of-three triplets.
5. PRESERVE CITATIONS: Maintain all bracketed Claim citations (e.g. [C1], [C4]) and the Minto section structure.
"""


def edit_memo(
    draft_markdown: str,
    claims: List[GroundedClaim],
    provider: LLMProvider,
) -> Tuple[str, LintResult, TraceabilityReport]:
    """
    Execute the editorial pass on draft_markdown.
    Enforces linter cleanliness and strict numerical traceability.
    """
    initial_lint = lint_memo(draft_markdown)
    violations_text = "\n".join(
        f"- Line {v.line_number}: '{v.matched_text}' -> {v.rule_description}"
        for v in initial_lint.violations
    ) or "None (clean initial draft)"

    allowed_metrics_summary = ", ".join(
        f"[{c.id}: {c.metric_or_data}]" for c in claims if c.metric_or_data
    )

    prompt = f"""Rewrite and edit the following investment memo to remove AI clichés and sharpen analyst tone.

CURRENT LINTER VIOLATIONS TO REMOVE:
{violations_text}

VERIFIED ALLOWED METRICS (DO NOT INVENT ANY OTHERS):
{allowed_metrics_summary}

ORIGINAL DRAFT MEMO:
\"\"\"
{draft_markdown}
\"\"\"

Output ONLY the revised markdown text of the investment memo. Do not include meta-commentary.
"""

    edited_text = provider.complete(
        prompt=prompt,
        system_instruction=STYLE_DIRECTIVE,
        temperature=0.2,
    )

    # Hard Invariant Check: Verify numerical traceability
    traceability = verify_numerical_traceability(edited_text, claims)
    if not traceability.is_valid:
        # Emergency self-refine loop: fix untraced numbers
        repair_prompt = f"""The edited memo failed strict numerical verification because it introduced untraced numbers:
UNTRACED NUMBERS DETECTED: {', '.join(traceability.untraced_metrics)}

ALLOWED METRICS ONLY: {allowed_metrics_summary}

Fix the text below by strictly replacing or removing any ungrounded figures with exact verified numbers:
\"\"\"
{edited_text}
\"\"\"
"""
        edited_text = provider.complete(
            prompt=repair_prompt,
            system_instruction=STYLE_DIRECTIVE,
            temperature=0.1,
        )
        traceability = verify_numerical_traceability(edited_text, claims)

    final_lint = lint_memo(edited_text)
    return edited_text, final_lint, traceability
