# Thesis Engine: Research-to-Conviction Analytical Memo Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.7+-e92063.svg)](https://docs.pydantic.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Deconstruct unstructured research packets into atomic, verified claims; stress-test orthogonal hypotheses with an adversarial pre-mortem critic; structure arguments via Minto's Pyramid Principle; and enforce hard numerical traceability to mathematically eliminate hallucinations.**

---

## 1. Executive Summary & Problem Statement

Large Language Models (LLMs) typically fail at high-stakes analytical decision-making (investment memos, technical evaluations, research syntheses) because **nothing forces them to commit**. Given raw data, naive one-shot prompts default to:

1. **Cowardly Hedging & Bland Summaries**: Defaulting to non-committal summaries littered with synthetic transitions (*"delve"*, *"testament to"*, *"in an increasingly... world"*, *"not only X but also Y"*).
2. **Hallucinated Metrics**: Rounding numbers, inventing valuation multiples, or fabricating benchmark stats with zero evidentiary lineage.
3. **Absence of Falsifiability**: Failing to specify the exact empirical conditions or operational thresholds that would prove the thesis wrong.
4. **Self-Grading Bias**: Evaluating generated outputs using the same model family that drafted them, producing falsely inflated conviction scores.

**Thesis Engine** solves this with an architectural, multi-stage reasoning pipeline with deterministic local invariants, multi-source grounding tools, and an independent cross-model evaluation harness.

---

## 2. System Architecture

```
                                [ Raw Anonymized Dossier / User Query ]
                                                   │
                                                   ▼
                                   [ Stage 0: Intent Classifier & Router ]
                                   - Categorizes: COMPANY, TOPIC, INDUSTRY, MACRO, COMPARISON, AMBIGUOUS
                                   - Live Retrieval: FMP Financials, SerpApi Scholar, Semantic Scholar, Tavily
                                                   │
                                                   ▼
                                  [ Stage 1: Grounded Claim Extractor ]
                                   - Categorized: FACT, ESTIMATE, OPINION
                                   - Invariant: Verbatim source_quote substring match against primary source
                                   - Multi-tier recovery: Exact match ➔ Token regex ➔ Lexical alignment (≥85%)
                                   - Output: List[GroundedClaim] (Pydantic schema)
                                                   │
                                                   ▼
                             [ Stage 2: 360° Candidate Theses & Adversarial Debate ]
                                   - Proposes 3 orthogonal theses: BUY/VALIDATED, CONDITIONAL, PASS/REJECT
                                   - Adversarial Critic Agent: 3-year fatal failure pre-mortem (Du et al., 2023)
                                   - Survival scoring (1.0–10.0) & quantitative falsification triggers
                                   - Arbitration: Dominant thesis selected or defaults to PASS
                                                   │
                                                   ▼
                                  [ Stage 3: Grounded Minto Synthesizer ]
                                   - Barbara Minto's Pyramid Principle: Answer-First top-line conviction
                                   - 3 Supporting Strategic Pillars strictly anchored to Claim IDs [C1, C4, ...]
                                   - Downside failure modes derived from pre-mortem attacks
                                   - "What Would Change My Mind" falsification criteria
                                                   │
                                                   ▼
                               [ Stage 4: De-Slopped Voice & Traceability Guard ]
                                   - Style Directives: Active voice, plain English, zero throat-clearing
                                   - Deterministic Regex Linter: 0 AI clichés, em-dash caps, no triplets
                                   - Hard Numerical Traceability: Regex extracts ALL metrics/currencies/percentages
                                   - Zero ungrounded figures permitted; triggers automated self-refine loop
                                                   │
                                                   ▼
                                   [ Final Verified Analytical Memo ]
                                                   │
                                                   ▼
                              [ Stage 5: Evaluation & Cross-Model Benchmark ]
                                   - Symmetrical Mega-Prompt Baseline comparison
                                   - Cross-Model Blind Judge (e.g. Claude 3.5 Sonnet judging Gemini 3.8 Flash)
                                   - Ablation testing (--no-debate, --no-voice)
                                   - Terminal Rich comparison table & anonymized blind_eval.md
```

---

## 3. Core Engine Modules & Implementation

### 3.1 Grounded Claim Extraction (`src/reasoning/claims.py`)
* Deconstructs unstructured research packets, corporate SEC filings (e.g., S-1 / 10-K), or academic literature into discrete, atomic claims.
* Each claim is tagged as `FACT` (audited numbers, historical events), `ESTIMATE` (forward projections, TAM, confidence intervals), or `OPINION` (management commentary, qualitative moats).
* **Hard Verbatim Invariant**: `verify_and_filter_claims()` validates that every single claim's `source_quote` exists verbatim in the source dossier. Any claim with fabricated quotes or ungrounded assertions is immediately discarded.

### 3.2 360° Candidate Theses & Adversarial Pre-Mortem (`src/reasoning/debate.py`)
* Formulates three orthogonal candidate theses:
  * **BUY / VALIDATED**: Core mechanism holds, robust unit economics, dominant market/benchmark efficacy.
  * **CONDITIONAL / CONSTRAINED**: Viable only within specific operational boundaries, requiring valuation margin of safety.
  * **PASS / REJECT / DISCONFIRMED**: Structural failure, multiple compression hazard, fatal scaling bottleneck.
* **Pre-Mortem Critic Agent (Du et al., 2023)**: Simulates a catastrophic downside scenario (*"Assume 3 years have passed and this investment/technology lost 60–80% of value. Exactly how did it fail?"*).
* Derives quantitative falsification triggers tied directly to extracted claim IDs.

### 3.3 Answer-First Minto Synthesis (`src/reasoning/minto.py`)
* Formats the surviving thesis according to Barbara Minto’s Pyramid Principle:
  1. **Executive Thesis (Answer-First)**: Unambiguous recommendation and core asymmetric insight.
  2. **Three Supporting Strategic Pillars**: Exhaustive, evidence-backed arguments citing bracketed Claim IDs (`[C1]`, `[C5]`).
  3. **Structural Risks & Pre-Mortem Failure Modes**: Concrete failure mechanics without sanitized corporate hedging.
  4. **What Would Change My Mind**: 3 measurable, falsifiable operational triggers that mandate an immediate thesis exit.

### 3.4 Numerical Traceability Guard & Anti-Slop Linter (`src/voice/`)
* **Strict Traceability Guard (`traceability.py`)**: Uses comprehensive regular expressions (`METRIC_PATTERN`) to extract every currency amount, percentage, multiple, latency figure, and metric token from the drafted memo. Checks each token against the `allowed_metrics_corpus` generated strictly from verified claims. Any invented number halts the pipeline with a `Hard Traceability Failure`.
* **Automated Self-Refine Loop (`editor.py`)**: Feeds untraced metrics back into the model in a targeted repair prompt to scrub or ground them before emission.
* **Deterministic Linter (`linter.py` & `banned_patterns.py`)**: Deterministically flags and eliminates synthetic transitions (*"delve"*, *"tapestry"*, *"testament to"*, *"not only X but also Y"*), em-dash clusters ($\le 1$ per 750 words), and rule-of-three adjective triplets.

### 3.5 Intent Classifier & Real-Time Tool Integration (`src/orchestrator.py`, `src/tools/`)
* Classifies incoming requests into 6 structured archetypes: `COMPANY`, `TOPIC`, `INDUSTRY`, `COMPARISON`, `MACRO`, and `AMBIGUOUS`.
* Connects directly to real-time third-party data APIs:
  * **Financial Modeling Prep (FMP)**: Pulls live market cap, P/E (TTM & forward), EV/EBITDA, P/S, gross/operating margins, free cash flow, and Net Debt/EBITDA leverage.
  * **SerpApi & Semantic Scholar**: Fetches peer-reviewed paper abstracts, citation counts, and publication metadata.
  * **Tavily Search & Gemini Grounding**: Ingests live web findings, regulatory releases, and primary company disclosures.
* **Recommendation Guardrail (`src/templates/guardrail.py`)**: Programmatically scrubs unsolicited investment advice or speculative buy/sell calls from academic and macro queries.

---

## 4. Empirical Benchmark & Evaluation Harness

Thesis Engine includes an uncompromising evaluation suite (`src/eval/`) contrasting a symmetrical **Mega-Prompt Baseline** (which receives identical Minto and anti-slop guidelines in a single prompt) against the **Full Thesis Pipeline**.

### 4.1 Cross-Model Blind Judge
To eliminate self-grading bias, the evaluation harness decouples the generator model from the judge model (e.g., **Claude 3.5 Sonnet** independently judging **Gemini 3.8 Flash**). Documents are stripped of identity headers and evaluated across four 1–5 dimensions:
1. **Thesis Falsifiability & Conviction**: Are actionable, falsifiable criteria established?
2. **Evidence Grounding & Linkage**: Are all claims auditable and cited to source data?
3. **Pre-Mortem Realism**: Are downside failure modes genuinely fatal and stress-tested?
4. **Prose Conviction & Slop Absence**: Is the prose dense, active, and free of AI clichés?

### 4.2 Benchmark Results (LLM Speculative Decoding Architecture)

| Evaluation Dimension | Mega-Prompt Baseline | Full Thesis Engine Pipeline | Differentiator |
| :--- | :---: | :---: | :--- |
| **Thesis Falsifiability (1–5)** | 4.3 / 5.0 | **4.8 / 5.0** | Explicit 3-tier verdict ladder with operational thresholds |
| **Evidence Grounding (1–5)** | 4.4 / 5.0 | **4.7 / 5.0** | Auditable `[C1]`–`[C45]` claim citation system |
| **Pre-Mortem Realism (1–5)** | 4.5 / 5.0 | **4.9 / 5.0** | Unvarnished fatal failure mechanisms (VRAM sunk cost, batch traps) |
| **Overall Judge Score (1–5)** | 4.5 / 5.0 | **4.7 / 5.0** | **Preferred by Independent Judge** |
| **Deterministic Slop Score (0–100, lower=better)**| 95.0 | **0.0** | **0 banned AI clichés detected** |
| **Strict Numerical Traceability** | Untracked | **PASSED (100% Grounded)**| Zero untraced numbers or invented statistics |

*Complete benchmark logs, token consumption tables, and side-by-side transcripts are available in [`eval_report.md`](eval_report.md) and [`citations.md`](citations.md).*

---

## 5. Full-Stack Web Application

Thesis Engine features a modern, production-ready web interface powered by FastAPI:

* **Real-Time Streaming**: Server-Sent Events (SSE) stream pipeline stages, extracted claims, candidate theses, and the synthesized memo in real time.
* **Dual Operating Modes**:
  * **Investment Mode**: Generates high-conviction investment memos with explicit BUY/CONDITIONAL/PASS recommendations.
  * **Research Mode**: Synthesizes complex technical and scientific literature with strict scientific objectivity (VALIDATED/CONSTRAINED/DISCONFIRMED).
* **Interactive Pipeline Visualizer**: Step-by-step progress indicators tracking token usage, slop score, and traceability status.
* **Dossier Flexibility**: Supports live web research via Tavily/Gemini, automated financial data retrieval, or manual paste/upload of primary documents (e.g., SEC Form S-1 filings).
* **Quota & BYOK Management**: Built-in free trial allocation with seamless Bring-Your-Own-Key (BYOK) fallback for Anthropic Claude and Google Gemini.

---

## 6. Project Directory Structure

```
doc-generator/
├── SPECIFICATION.md             # Complete architectural specification & invariants
├── README.md                    # Project documentation & quickstart guide
├── pyproject.toml               # Project metadata & dependency definitions
├── requirements.txt             # Pinned production dependencies
├── render.yaml                  # Cloud deployment configuration
├── Procfile                     # Web process entrypoint (Uvicorn)
├── eval_report.md               # Empirical evaluation & benchmark report
├── blind_eval.md                # Anonymized side-by-side evaluation sheet
├── citations.md                 # Complete verified thesis memo example (Speculative Decoding)
├── data/
│   ├── dossiers/                # Primary source research dossiers (e.g. Apex 2019 S-1)
│   └── quota.db                 # SQLite database for trial usage tracking
├── tests/                       # Comprehensive Pytest test suite
│   ├── test_claims.py           # Claim extraction & verbatim matching tests
│   ├── test_traceability.py     # Numerical traceability guard tests
│   ├── test_linter.py           # Anti-slop regex & heuristic tests
│   ├── test_router.py           # Query classification & routing tests
│   ├── test_financial_metrics.py# Real-time financial metrics fetcher tests
│   ├── test_guardrail.py        # Recommendation prohibition guardrail tests
│   └── test_web.py              # Web API endpoints & streaming tests
└── src/
    ├── config.py                # Environment configuration & model settings
    ├── orchestrator.py          # Unified analytical thinking orchestrator
    ├── pipeline.py              # 4-stage investment reasoning pipeline
    ├── llm/                     # Multi-provider LLM abstraction layer
    │   ├── base.py              # Abstract LLM provider interface
    │   ├── gemini.py            # Google Gemini provider (google-genai SDK)
    │   ├── anthropic.py         # Anthropic Claude provider (anthropic SDK)
    │   └── tracker.py           # Token usage and invocation latency tracker
    ├── reasoning/               # Core analytical reasoning engine
    │   ├── claims.py            # Grounded claim extractor & verbatim verification
    │   ├── debate.py            # 360° candidate theses & pre-mortem critic
    │   └── minto.py             # Barbara Minto Pyramid Principle synthesizer
    ├── voice/                   # Anti-slop & verification guards
    │   ├── banned_patterns.py   # Regex catalog of banned AI clichés & structures
    │   ├── linter.py            # Deterministic prose quality linter
    │   ├── traceability.py      # Hard numerical traceability verification guard
    │   └── editor.py            # Executive editorial de-slopping & repair loop
    ├── tools/                   # Live 3rd-party integration tools
    │   ├── financial_metrics.py # Financial Modeling Prep (FMP) real-time fetcher
    │   ├── serp_research.py     # SerpApi Google Scholar & Semantic Scholar fetcher
    │   └── tavily_search.py     # Tavily live web search & CLI fallback
    ├── research/                # Research dossier compilation
    │   └── web_search.py        # Temporal-anchored search synthesis
    ├── routing/                 # Query classification & intent models
    │   ├── classifier.py        # Few-shot query classifier
    │   └── models.py            # Pydantic models for routing decisions
    ├── templates/               # Output templates & guardrail rules
    │   ├── registry.py          # Category-specific template registry
    │   └── guardrail.py         # Recommendation scrubbing guardrails
    ├── eval/                    # Evaluation & ablation harness
    │   ├── baseline.py          # Symmetrical Mega-Prompt baseline
    │   ├── judge.py             # Cross-model independent judge
    │   └── runner.py            # Benchmark execution CLI & report exporter
    └── web/                     # Full-stack web application
        ├── app.py               # FastAPI application & REST endpoints
        ├── runner.py            # Asynchronous SSE execution manager
        ├── quota.py             # Quota check & prompt consumption logic
        └── templates/           # Frontend dashboard
            └── index.html       # Single-page application UI
```

---

## 7. Getting Started

### 7.1 Prerequisites
* Python 3.11 or higher
* [uv](https://github.com/astral-sh/uv) (recommended) or `pip`
* API Keys (at least one LLM provider required):
  * `GEMINI_API_KEY` (Google AI Studio)
  * `ANTHROPIC_API_KEY` (Anthropic Console)
  * *(Optional)* `FMP_API_KEY` (Financial Modeling Prep), `TAVILY_API_KEY`, `SERPAPI_API_KEY`

### 7.2 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/thesis-engine.git
   cd thesis-engine
   ```

2. **Create and activate a virtual environment**:
   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create a `.env` file in the project root:
   ```env
   GEMINI_API_KEY="your-google-gemini-api-key"
   ANTHROPIC_API_KEY="your-anthropic-api-key"
   GEMINI_MODEL="gemini-3.8-flash"
   ANTHROPIC_MODEL="claude-sonnet-4-6"

   # Optional 3rd-party tools
   FMP_API_KEY="your-fmp-api-key"
   TAVILY_API_KEY="your-tavily-api-key"
   SERPAPI_API_KEY="your-serpapi-api-key"
   SEMANTIC_SCHOLAR_API_KEY="your-semantic-scholar-api-key"
   ```

---

## 8. Usage & Execution

### 8.1 Launch the Web Dashboard
Start the FastAPI server:
```bash
uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://localhost:8000](http://localhost:8000) in your browser to interact with the dashboard.

### 8.2 Run the Thinking Orchestrator CLI
Run the intent-routed analytical pipeline on any company, topic, or ticker directly from the terminal:
```bash
# Company equity analysis (fetches live FMP financial metrics)
python -m src.orchestrator "NVDA"

# Objective scientific synthesis (fetches peer-reviewed literature)
python -m src.orchestrator "LLM Speculative Decoding"
```

### 8.3 Run the Evaluation Benchmark
Execute the un-rigged evaluation harness comparing the Mega-Prompt Baseline against the Full Pipeline:
```bash
# Full benchmark on primary S-1 dossier using Gemini to generate and Claude to judge
python -m src.eval.runner --dossier data/dossiers/apex_observability_2019.md --subject "Apex Systems" --generator gemini --judge anthropic

# Run ablation studies (bypass debate or voice pass)
python -m src.eval.runner --ablate debate
python -m src.eval.runner --ablate voice
```

### 8.4 Run the Test Suite
Execute the full unit test suite:
```bash
pytest -v
```

---

## 9. Key Invariants & Design Principles

* **Deterministic over Generative**: Never ask an LLM to evaluate whether a metric is hallucinated if regex and set operations can mathematically prove it.
* **Auditability via Exact Quotation**: Every claim must quote the primary text verbatim. If a quote cannot be recovered from the source text, it is discarded.
* **Answer-First Hierarchy**: Every memo starts with a top-line falsifiable conviction statement before expanding into supporting pillars.
* **Adversarial Sincerity**: Every investment thesis is subjected to an explicit 3-year fatal failure attack before being approved.
* **Separation of Powers**: Never allow an LLM family to grade its own outputs during evaluation benchmarks.

---

## 10. License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
