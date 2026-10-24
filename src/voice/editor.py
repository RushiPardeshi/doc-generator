"""Editorial pass: rewrites draft memo to eliminate AI slop while strictly maintaining numerical traceability."""

from typing import List, Tuple
from src.reasoning.claims import GroundedClaim
from src.voice.linter import lint_memo, LintResult
from src.voice.traceability import verify_numerical_traceability, TraceabilityReport
from src.llm.base import LLMProvider

STYLE_DIRECTIVE = """You are an exacting senior editor and lead research director editing an executive research memo / synthesis.
Your mandate is to eliminate every trace of generic AI writing and replace it with crisp, understated, authoritative analytical prose.

STYLE INVARIANTS:
1. HARD NUMERICAL TRACEABILITY: You are STRICTLY FORBIDDEN from inventing any numbers, percentages, multiples, measurements, or dollar amounts. You must preserve the exact verified metrics from the input and cited claims.
2. ZERO THROAT-CLEARING: Delete all introductory warm-ups ("X represents an attractive...", "In today's digital landscape...", "It is worth noting that..."). Start immediately with the active assertion.
3. BANNED CLICHÉS: Never use "not only X, but also Y", "testament to", "delve", "tapestry", "landscape", "poised to", "holistic", or "pivotal".
4. PUNCTUATION DISCIPLINE: Minimize em-dashes (at most 1 in the entire memo). Use standard periods. Avoid symmetrical rule-of-three triplets.
5. PRESERVE CITATIONS: Maintain all bracketed Claim citations (e.g. [C1], [C4]) and the Minto section structure.
6. SCANNABLE MARKDOWN & AIRY FORMATTING (NEWLINE DISCIPLINE):
   - Always put a blank line (double newline) after each topic, heading, and sub-heading.
   - Use double newlines between paragraphs. Never output dense blocks longer than 3 sentences.
   - Convert dense inline lists (e.g. '(1)... (2)... (3)...') into clean, scannable markdown bullet lists with bold headers, with a newline after each item.
   - Preserve or use markdown comparison tables where multiple empirical metrics are compared across regimes.
7. TONE APPROPRIATENESS:
   - If the subject is a technology, model, paper, or research concept (e.g. LIIF, continuous representation), keep the tone analytical and research-driven; do NOT force artificial "buy", "sell", or "deploy" procurement decisions.
8. PLAIN LANGUAGE & DIRECT CAUSALITY:
   - Write in clear, plain-English prose. Do NOT hide simple economic or technical concepts behind dense Wall Street, management consulting, or academic jargon.
   - Express abstract concepts as concrete, real-world cause and effect (explain plainly what happens to cash, costs, customers, latency, or hardware).
   - Concrete examples:
     * INSTEAD OF: "The contribution margin per order is structurally fragile."
     * WRITE: "The business barely breaks even on each delivery; small cost increases or promotional discounts quickly create net losses."
     * INSTEAD OF: "Exhibits asymmetric downside multiple compression risk."
     * WRITE: "The valuation will drop sharply if revenue growth slows even slightly."
   - Favor active, concrete verbs over stacked abstract nouns (use "margins drop" or "costs rise" rather than "structural margin degradation" or "cost-profile escalation").
9. BAN META-PROMPT LEAKAGE & EPISTEMIC PONTIFICATING:
   - Never write about the memo, thesis, or reasoning process itself.
   - FORBIDDEN META-PHRASES: "The thesis survives only within...", "within these guardrails", "the argument holds", "opinion-based heuristic, not a rigorously derived cost model", "the pre-mortem critique indicates".
   - Speak directly about the real-world subject, its users, and its costs. For example, instead of writing "The 500/month breakeven is an opinion-based heuristic", write "The 500/month threshold is a conservative rule of thumb".
10. PRESERVE CONCRETE DATA & SUBJECT-FIRST SENTENCES:
   - When claims provide specific numbers, costs, or real-world examples (like credit burn, pricing tiers, row counts), keep those concrete numbers in the prose rather than abstracting them into high-level categories (e.g. say "using 5 data sources and AI cells", NOT "provider mix and cell density").
   - Start sentences with the active subject and verb. Never stack multiple introductory dependent clauses (e.g. avoid "Above this threshold, and specifically for teams running X, Y does Z"). Keep sentences under 25 words.
"""


def edit_memo(
    draft_markdown: str,
    claims: List[GroundedClaim],
    provider: LLMProvider,
    mode: str = "research",
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

    prompt = f"""Rewrite and edit the following executive research document to sharpen analytical tone, enforce plain-language clarity, eliminate meta-commentary (never write 'the thesis survives', 'within guardrails', or 'heuristic vs cost model'), retain concrete numbers and costs from cited claims rather than abstracting them, maintain scannable markdown formatting with blank lines after each heading/topic, and eliminate generic AI clichés.

DELIVERABLE TYPE: {mode.upper()} SYNTHESIS
{violations_text}

VERIFIED ALLOWED METRICS (DO NOT INVENT ANY OTHERS):
{allowed_metrics_summary}

ORIGINAL DRAFT MEMO:
\"\"\"
{draft_markdown}
\"\"\"

Output ONLY the revised markdown text. Ensure a blank line is included after each topic, heading, and list item. Do not include meta-commentary.
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
