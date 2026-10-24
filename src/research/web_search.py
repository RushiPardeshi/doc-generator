"""Automated grounded web research using Google Gemini with Search Grounding."""

import os
import time
from typing import Optional, List
from google import genai
from google.genai import types
from google.genai import errors

from src.config import GEMINI_API_KEY, GEMINI_MODEL

RESEARCH_FALLBACK_MODELS = [
    GEMINI_MODEL,
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
]

RESEARCH_PROMPT_TEMPLATE = """You are a senior forensic equity research analyst and investigative technology researcher.
Your task is to conduct in-depth, verified web research on the following topic and assemble a comprehensive, fact-rich Research Dossier.

TOPIC TO RESEARCH:
{topic}

INSTRUCTIONS:
1. Search the live web for the most up-to-date and reliable empirical data, technical benchmarks, performance metrics, and factual statements.
2. Structure the dossier cleanly in Markdown with the following sections:
   # Research Dossier: {topic}

   ## 1. Executive Summary & Overview
   - Concise factual overview of the subject, model, technology, or company.

   ## 2. Empirical Metrics & Key Benchmark Data
   - Explicitly list numbers, benchmark scores, throughput/latency, parameters, accuracy, or financial metrics.
   - Every metric should cite its source or context.

   ## 3. Structural Mechanisms & Core Advantages
   - Concrete architectural innovations, mathematical/algorithmic mechanisms, efficiency gains, or competitive advantages.

   ## 4. Technical Constraints, Bottlenecks & Failure Modes
   - Specific failure points, computational/memory overhead, trade-offs, scalability limits, or execution hazards.

   ## 5. Key Factual Statements & Excerpts
   - 5 to 10 unambiguous factual sentences or quotes directly reported in research papers, technical benchmarks, or disclosures.

3. NEWLINE DISCIPLINE: Always use a blank line (double newline) after each topic, heading, and list item. Never run text directly beneath a heading without an empty line.

CRITICAL INVARIANT:
Do NOT output vague marketing fluff or generic platitudes. Include specific numbers, percentages, dates, parameter sizes, benchmark datasets, and entity names so downstream analysts can verify every claim.
"""


def compile_research_dossier(
    topic: str,
    api_key: Optional[str] = None,
    preferred_model: Optional[str] = None,
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

    prompt = RESEARCH_PROMPT_TEMPLATE.format(topic=topic)
    last_error: Optional[Exception] = None

    for model_name in models_to_try:
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
            if response.text and len(response.text.strip()) > 100:
                return response.text.strip()
        except errors.APIError as e:
            last_error = e
            status = getattr(e, "code", None) or getattr(e, "status_code", None)
            if status == 429:
                # Rate limit encountered: try next fallback model
                continue
            elif status == 503:
                time.sleep(2)
                continue
            else:
                # Other API error, continue to fallback model
                continue
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(
        f"Unable to compile research dossier for '{topic}'. "
        f"All attempted models encountered quota or network limits: {last_error}"
    )
