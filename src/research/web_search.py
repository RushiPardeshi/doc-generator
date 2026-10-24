"""Automated grounded web research using Google Gemini with Search Grounding."""

import os
import time
from datetime import datetime
from typing import Optional, List
from google import genai
from google.genai import types
from google.genai import errors

from src.config import GEMINI_API_KEY, GEMINI_MODEL

RESEARCH_FALLBACK_MODELS = [
    GEMINI_MODEL,
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


class _PromptTemplate(str):
    """String template that automatically injects current_date if omitted."""
    def format(self, *args, **kwargs):
        if "current_date" not in kwargs:
            kwargs["current_date"] = datetime.now().strftime("%B %Y")
        return super().format(*args, **kwargs)


RESEARCH_PROMPT_TEMPLATE = _PromptTemplate("""You are a senior forensic equity research analyst and investigative technology researcher.
Your task is to conduct in-depth, verified web research on the following topic and assemble a comprehensive, fact-rich Research Dossier.

TEMPORAL ANCHOR & SEARCH RECENCY INSTRUCTIONS:
1. TODAY'S DATE: {current_date}.
2. LIVE RECENCY REQUIREMENT:
   - When searching the web, specifically search for the latest real-time data, announcements, and metrics as of {current_date}.
   - Append the current year or recency qualifiers to your search queries to avoid pulling stale cached snippets from old search results or archived websites.
3. FAST-MOVING OPERATIONAL METRICS (TEAM SIZE / HEADCOUNT / PRICING / FUNDING):
   - Fast-growing startups and tech companies change team size, pricing tiers, and product features rapidly.
   - Do NOT rely on stale cached snippets from months or years ago (e.g. outdated LinkedIn search preview snippets or secondary directory profiles like Crunchbase/Tracxn from past quarters).
   - Search specifically for recent updates, company press releases, the company's live `/careers` or `/about` pages, or verified recent news disclosures.
   - If a metric (such as employee headcount or round valuation) is based on older disclosures or third-party estimates, explicitly state its exact date and caveat (e.g. "Reported ~X employees as of [Specific Date], though recent scaling indicates higher current headcount"). Never present an old cached estimate as current reality.
4. PRIMARY SOURCE PREFERENCE:
   - Prioritize verified primary sources: official documentation, product changelogs, live pricing pages, GitHub releases/commits, and recent regulatory disclosures.

TOPIC TO RESEARCH:
{topic}

INSTRUCTIONS:
1. Search the live web for the most up-to-date and reliable empirical data, technical benchmarks, performance metrics, and factual statements as of {current_date}.
2. Structure the dossier cleanly in Markdown with the following sections:
   # Research Dossier: {topic}

   ## 1. Executive Summary & Overview
   - Concise factual overview of the subject, model, technology, or company as of {current_date}.

   ## 2. Empirical Metrics & Key Benchmark Data
   - Explicitly list numbers, benchmark scores, throughput/latency, parameters, accuracy, or financial metrics.
   - Every metric should cite its source and reporting date/period (e.g., "Source: Official Pricing Page, {current_date}").

   ## 3. Structural Mechanisms & Core Advantages
   - Concrete architectural innovations, mathematical/algorithmic mechanisms, efficiency gains, or competitive advantages.

   ## 4. Technical Constraints, Bottlenecks & Failure Modes
   - Specific failure points, computational/memory overhead, trade-offs, scalability limits, or execution hazards.

   ## 5. Key Factual Statements & Excerpts
   - 5 to 10 unambiguous factual sentences or quotes directly reported in research papers, technical benchmarks, or disclosures.

3. NEWLINE DISCIPLINE: Always use a blank line (double newline) after each topic, heading, and list item. Never run text directly beneath a heading without an empty line.

CRITICAL INVARIANT:
Do NOT output vague marketing fluff or generic platitudes. Include specific numbers, percentages, dates, parameter sizes, benchmark datasets, and entity names so downstream analysts can verify every claim.
""")


def compile_research_dossier(
    topic: str,
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
    as_of_date: Optional[str] = None,
) -> str:
    """
    Query Gemini with Google Search Grounding to build a structured research dossier.
    Iterates through fallback models if rate limits (429) or high-demand (503) errors occur.
    """
    key = api_key or GEMINI_API_KEY
    if not key:
        raise ValueError("No Gemini API key available. Provide a key or configure GEMINI_API_KEY.")

    client = genai.Client(api_key=key)

    models_to_try: List[str] = []
    if preferred_model:
        models_to_try.append(preferred_model)
    for m in RESEARCH_FALLBACK_MODELS:
        if m not in models_to_try:
            models_to_try.append(m)

    current_date = as_of_date or datetime.now().strftime("%B %Y")
    prompt = RESEARCH_PROMPT_TEMPLATE.format(topic=topic, current_date=current_date)
    last_error: Optional[Exception] = None

    for model_name in models_to_try:
        for attempt in range(3):
            try:
                config = types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.2,
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                text = response.text
                if not text and getattr(response, "candidates", None) and response.candidates:
                    cand = response.candidates[0]
                    if getattr(cand, "content", None) and getattr(cand.content, "parts", None):
                        text_parts = [p.text for p in cand.content.parts if getattr(p, "text", None)]
                        if text_parts:
                            text = "".join(text_parts)
                if text and len(text.strip()) > 100:
                    return text.strip()
            except errors.APIError as e:
                last_error = e
                status = getattr(e, "code", None) or getattr(e, "status_code", None)
                if status == 503 or "503" in str(e) or "high demand" in str(e).lower():
                    # High demand on this model: backoff and retry
                    time.sleep(2 ** (attempt + 1))
                    continue
                elif status in (404, 429) or "404" in str(e) or "429" in str(e):
                    # Model deprecated / not found or quota exhausted: try next model
                    break
                else:
                    time.sleep(1)
                    continue
            except Exception as e:
                last_error = e
                break

    raise RuntimeError(
        f"Unable to compile research dossier for '{topic}'. "
        f"All attempted models encountered quota or network limits: {last_error}"
    )
