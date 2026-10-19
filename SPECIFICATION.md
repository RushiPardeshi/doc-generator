# Thesis Engine: Research-to-Conviction Investment Memo Generator

## 1. Executive Summary & Core Thesis

Large Language Models typically fail at investment analysis because **nothing forces them to commit**. Given a raw research packet, naive one-shot prompts default to bland summaries littered with synthetic transitions ("delve", "testament to", "not only X but also Y"), cowardly hedging, and zero falsifiable criteria.

**Thesis Engine** solves this with an architectural pipeline:
1. **Structural Reasoning**: Extract claims as tagged, cited atomic units (`fact`, `estimate`, `opinion`) verified via verbatim string matching. Generate 3 distinct candidate theses (Bull, Conditional, and Bear/Pass), subject each to an adversarial pre-mortem critic agent (Du et al., 2023), and synthesize the survivor using Minto's Pyramid Principle (Answer-First, 3 Supporting Pillars, Structural Risks, and "What Would Change My Mind").
2. **De-Slopped Voice & Hard Traceability Guard**: Decouple drafting from editing. Apply a deterministic local linter targeting Wikipedia AI-writing patterns and investor clichés. Enforce a **hard numerical traceability invariant**: every metric and number in the final memo must trace directly back to verified claims; hallucinated figures cause an immediate reject.
3. **Uncompromising Evaluation**: An un-rigged benchmark contrasting a symmetrical "Mega-Prompt" baseline against the pipeline. Uses a **cross-model judge** (e.g., Claude 3.5 Sonnet judging Gemini 3.8 Flash) to eliminate self-grading bias, supports ablation testing, and exports an anonymized blind-review sheet for human inspection.

---

## 2. System Architecture

```
                       [ Raw Anonymized Dossier ]
                                  │
                                  ▼
                     [ Stage 1: Grounded Claim Extractor ]
                     - Tagged: FACT, ESTIMATE, OPINION
                     - Invariant: source_quote verified via exact string match
                     - Output: List[GroundedClaim] (Pydantic)
                                  │
                                  ▼
                   [ Stage 2: 360° Candidate Theses & Pre-Mortem ]
                     - Proposes: Bull, Conditional, and PASS/AVOID theses
                     - Critic Agent: 3-year fatal failure attack
                     - All-Fail Handling: Emits unvarnished "PASS" memo
                                  │
                                  ▼
                    [ Stage 3: Grounded Minto Synthesizer ]
                     - Answer-First conviction statement
                     - 3 Pillars strictly cited to Claim IDs [C1, C4, ...]
                     - Key Risks derived from Pre-Mortem
                     - "What Would Change My Mind" (Falsification triggers derived from claims)
                                  │
                                  ▼
                    [ Stage 4: Voice Pass & Traceability Guard ]
                     - Concise style rules (active voice, zero throat-clearing)
                     - Deterministic Linter (banned clichés, em-dash, rule-of-three)
                     - Hard Numerical Traceability: Zero untraced numbers allowed
                     - Self-refine loop if violations persist
                                  │
                                  ▼
                     [ Final Investment Memo ]
                                  │
                                  ▼
                    [ Stage 5: Evaluation & Ablation Harness ]
                     - Symmetrical Mega-Prompt Baseline (identical instructions)
                     - Cross-Model Judge (Claude evaluating Gemini)
                     - Ablation testing (--no-debate, --no-voice)
                     - Side-by-side terminal report & blind-review document
```

---

## 3. Module Specifications

### 3.1 LLM Abstraction Layer (`src/llm/`)
* **Agnostic Interface**: Supports Google Gemini (default via `google-genai`) and Anthropic Claude (via `anthropic`).
* **Cross-Model Separation**: Generator model and Judge model can be assigned independently (e.g. Gemini 3.8 Flash generates, Claude 3.5 Sonnet judges).
* **Typed Structured Outputs**: All reasoning stages use Pydantic models for schema enforcement.

### 3.2 Reasoning Engine (`src/reasoning/`)
* **`claims.py`**:
  * Extracts atomic assertions from unstructured research.
  * Fields: `id`, `claim_type` (`fact`, `estimate`, `opinion`), `statement`, `source_quote`, `metric_or_data`, `entity_names`.
  * **Invariant**: `verify_claim_quotes()` checks that `source_quote` exists verbatim in the source dossier text.
* **`debate.py`**:
  * Proposes 3 distinct theses: Bull Case, Conditional/Margin-of-Safety Case, and Bear/Pass Case.
  * Critic Agent conducts an adversarial pre-mortem: *"Assume it is 3 years later and this investment lost 80% of value. Exactly how did it fail?"*
  * If all theses fail the pre-mortem or Bear case dominates, pipeline outputs a **PASS** recommendation.
* **`minto.py`**:
  * Structures the draft using Barbara Minto’s Pyramid Principle:
    1. **Recommendation / Answer-First**: Top-line thesis and investment action.
    2. **3 Supporting Pillars**: Exhaustive, cited arguments tied directly to extracted Claim IDs.
    3. **Key Risks & Bear Case**: Unvarnished failure modes.
    4. **What Would Change My Mind**: Falsification triggers strictly derived from cited metrics (no invented thresholds).

### 3.3 Voice & Anti-Slop Engine (`src/voice/`)
* **`traceability.py`**:
  * Extracts all numbers, percentages, and currencies from the memo.
  * Ensures every single metric traces back to a cited `GroundedClaim`. Untraced numbers trigger a validation failure.
* **`banned_patterns.py` & `linter.py`**:
  * Deterministic regex and heuristic checks:
    * Banned Cliches: *"not only... but also"*, *"testament to"*, *"in an increasingly... world"*, *"delve"*, *"tapestry"*, *"landscape"*, *"holistic"*, *"pivotal"*, *"beacon"*, *"poised to"*.
    * Structural Tells: Em-dash clusters ($\le 1$ per 750 words), Rule-of-Three adjective triplets, passive hedging.
* **`editor.py`**:
  * Style instructions forcing active verbs, concrete claims, and zero warm-up.
  * Self-refine loop feeds linter feedback directly back into the rewrite pass.

### 3.4 Evaluation & Ablation Harness (`src/eval/`)
* **`baseline.py`**:
  * Symmetrical "Mega-Prompt" baseline with identical instructions (Minto answer-first, commit to a thesis, cite claims, avoid AI clichés).
* **`judge.py`**:
  * Cross-model evaluation (Claude 3.5 Sonnet judging Gemini output) across:
    1. Thesis Clarity & Conviction (1–5)
    2. Falsifiability & Risk Realism (1–5)
    3. Evidence Grounding & Linkage (1–5)
    4. Prose Conviction & Slop Score (1–5)
* **`runner.py`**:
  * CLI tool running Baseline vs. Pipeline vs. Ablated Pipeline (`--no-debate`, `--no-voice`).
  * Generates terminal comparison tables (`rich`), `eval_report.md`, and label-stripped `blind_eval.md`.

---

## 4. Curated Primary Dossier (`data/dossiers/`)

* **Apex Systems (2019 Anonymized S-1)**:
  * Based on Datadog's actual SEC EDGAR August 2019 S-1 registration statement.
  * Fully anonymized to eliminate hindsight bias.
  * Key audited metrics:
    * $148.7M revenue (2018), $153.3M (first 6 months 2019, up 79% YoY).
    * Net Expansion Rate: 130%.
    * Gross Margin: 76%.
    * Customers > $100k ARR: 453 customers (~72% of ARR).
    * Multi-product adoption: 40% of customers using $\ge 2$ products (up from 15% YoY).
    * Cash Flow from Operations: positive $10.9M.
