"""CLI Evaluation Runner: executes Baseline vs. Pipeline vs. Ablation benchmarks."""

import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.config import DOSSIERS_DIR, DEFAULT_GENERATOR_PROVIDER, DEFAULT_JUDGE_PROVIDER
from src.llm import get_provider
from src.pipeline import run_pipeline, PipelineConfig
from src.eval.baseline import run_baseline
from src.eval.judge import evaluate_memos_blind
from src.llm.tracker import token_tracker

console = Console()


def create_markdown_report(
    company_name: str,
    baseline_memo: str,
    pipeline_result,
    baseline_lint,
    judge_result,
    label_baseline: str,
    label_pipeline: str,
    output_path: Path,
) -> None:
    """Generate a comprehensive markdown evaluation report."""
    base_scorecard = (
        judge_result.memo_a_scorecard if label_baseline == "A" else judge_result.memo_b_scorecard
    )
    pipe_scorecard = (
        judge_result.memo_b_scorecard if label_baseline == "A" else judge_result.memo_a_scorecard
    )
    from_tracker = token_tracker.get_markdown_summary()

    content = f"""# Thesis Engine: Evaluation & Benchmark Report
**Target Subject**: {company_name}  
**Generator Model**: `{pipeline_result.ablation_mode}`  
**Preferred by Judge**: `{'Pipeline' if judge_result.preferred_memo == label_pipeline else 'Baseline'}`

---

## 1. Executive Summary & Verdict
{judge_result.verdict_explanation}

### Key Differentiators Identified by Independent Judge:
"""
    for diff in judge_result.key_differentiators:
        content += f"- {diff}\n"

    content += f"""
---

## 2. Quantitative Benchmark Matrix

| Metric / Evaluation Dimension | Symmetrical Mega-Prompt Baseline | Full Thesis Pipeline |
| :--- | :--- | :--- |
| **Thesis Falsifiability (1-5)** | {base_scorecard.falsifiability.score:.1f} / 5.0 | **{pipe_scorecard.falsifiability.score:.1f} / 5.0** |
| **Evidence Grounding (1-5)** | {base_scorecard.evidence_grounding.score:.1f} / 5.0 | **{pipe_scorecard.evidence_grounding.score:.1f} / 5.0** |
| **Pre-Mortem Realism (1-5)** | {base_scorecard.premortem_realism.score:.1f} / 5.0 | **{pipe_scorecard.premortem_realism.score:.1f} / 5.0** |
| **Prose Conviction & Slop Absence (1-5)** | {base_scorecard.prose_slop_absence.score:.1f} / 5.0 | **{pipe_scorecard.prose_slop_absence.score:.1f} / 5.0** |
| **Overall Judge Score (1-5)** | {base_scorecard.overall_score:.1f} / 5.0 | **{pipe_scorecard.overall_score:.1f} / 5.0** |
| **Deterministic Slop Score (0-100, lower=better)** | {baseline_lint.slop_score:.1f} | **{pipeline_result.lint_result.slop_score:.1f}** |
| **Banned Clichés Detected** | {len(baseline_lint.violations)} violations | **{len(pipeline_result.lint_result.violations)} violations** |
| **Strict Numerical Traceability** | Untracked | **{'PASSED (100% Grounded)' if pipeline_result.traceability_report.is_valid else 'FAILED'}** |

---

## 3. Empirical Token Usage & Peak Capacity
{from_tracker}

---

## 4. Side-by-Side Memo Comparison

### Symmetrical Mega-Prompt Baseline
```markdown
{baseline_memo}
```

### Full Thesis Pipeline Memo
```markdown
{pipeline_result.final_memo}
```
"""
    output_path.write_text(content)


def create_blind_eval_file(
    baseline_memo: str,
    pipeline_memo: str,
    label_baseline: str,
    label_pipeline: str,
    output_path: Path,
) -> None:
    """Generate a label-stripped document for unbiased human blind review."""
    memo_a = baseline_memo if label_baseline == "A" else pipeline_memo
    memo_b = pipeline_memo if label_pipeline == "B" else baseline_memo

    content = f"""# Blind Review Evaluation Document

Please read Candidate Memo A and Candidate Memo B below without knowing which was produced by the 1-shot baseline vs. multi-stage pipeline.

Score both on:
1. Conviction & Thesis Falsifiability (Did it take a stand? Can you bet against it?)
2. Numerical Specificity (Are numbers authentic and tied to claims?)
3. Voice Cleanliness (Does it sound like an understated investor vs generic AI slop?)

================================ CANDIDATE MEMO A ================================
{memo_a}

================================ CANDIDATE MEMO B ================================
{memo_b}

<!-- KEY FOR REVEAL: Candidate A = {'Baseline' if label_baseline == 'A' else 'Pipeline'}, Candidate B = {'Pipeline' if label_pipeline == 'B' else 'Baseline'} -->
"""
    output_path.write_text(content)


def main():
    parser = argparse.ArgumentParser(description="Run Thesis Engine Baseline vs Pipeline benchmark.")
    parser.add_argument(
        "--dossier",
        type=str,
        default=str(DOSSIERS_DIR / "apex_observability_2019.md"),
        help="Path to research dossier markdown file",
    )
    parser.add_argument(
        "--subject",
        "--company",
        dest="subject",
        type=str,
        default="Apex Systems",
        help="Subject, technology, proposal, or company name",
    )
    parser.add_argument("--generator", type=str, default=DEFAULT_GENERATOR_PROVIDER, help="Generator provider (gemini/anthropic)")
    parser.add_argument("--judge", type=str, default=DEFAULT_JUDGE_PROVIDER, help="Judge provider (anthropic/gemini)")
    parser.add_argument(
        "--ablate",
        choices=["none", "debate", "voice"],
        default="none",
        help="Ablation mode: 'debate' (bypass debate) or 'voice' (bypass voice rewrite)",
    )
    args = parser.parse_args()

    dossier_path = Path(args.dossier)
    if not dossier_path.exists():
        console.print(f"[red]Error: Dossier not found at {dossier_path}[/red]")
        sys.exit(1)

    dossier_text = dossier_path.read_text()
    console.print(Panel(f"[bold green]Starting Benchmark for {args.subject}[/bold green]\nDossier: {dossier_path.name}\nGenerator: {args.generator} | Judge: {args.judge} | Ablation: {args.ablate}"))

    # 1. Initialize Providers
    try:
        gen_provider = get_provider(args.generator)
    except Exception as e:
        console.print(f"[red]Failed to initialize generator provider ({args.generator}): {e}[/red]")
        sys.exit(1)

    try:
        judge_provider = get_provider(args.judge)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not initialize cross-model judge ({args.judge}): {e}. Falling back to generator as judge.[/yellow]")
        judge_provider = gen_provider

    # 2. Run Baseline
    console.print("\n[bold cyan]1/3 Running Symmetrical Mega-Prompt Baseline...[/bold cyan]")
    baseline_memo, baseline_lint = run_baseline(dossier_text, gen_provider)

    # 3. Run Pipeline
    pipe_cfg = PipelineConfig(
        company_name=args.subject,
        enable_debate=(args.ablate != "debate"),
        enable_voice=(args.ablate != "voice"),
    )
    console.print(f"[bold cyan]2/3 Running Thesis Pipeline (Ablation: {args.ablate})...[/bold cyan]")
    pipeline_result = run_pipeline(dossier_text, gen_provider, pipe_cfg)

    # 4. Run Independent Cross-Model Judge
    console.print("[bold cyan]3/3 Running Independent Cross-Model Judge...[/bold cyan]")
    judge_result, label_base, label_pipe = evaluate_memos_blind(
        baseline_memo=baseline_memo,
        pipeline_memo=pipeline_result.final_memo,
        judge_provider=judge_provider,
    )

    # 5. Render Comparison Table
    base_scorecard = judge_result.memo_a_scorecard if label_base == "A" else judge_result.memo_b_scorecard
    pipe_scorecard = judge_result.memo_b_scorecard if label_base == "A" else judge_result.memo_a_scorecard

    table = Table(title=f"Benchmark Matrix: {args.subject}")
    table.add_column("Evaluation Dimension / Metric", style="cyan", no_wrap=True)
    table.add_column("Mega-Prompt Baseline", style="magenta")
    table.add_column("Full Thesis Pipeline", style="green")

    table.add_row("Thesis Falsifiability (1-5)", f"{base_scorecard.falsifiability.score:.1f}", f"{pipe_scorecard.falsifiability.score:.1f}")
    table.add_row("Evidence Grounding (1-5)", f"{base_scorecard.evidence_grounding.score:.1f}", f"{pipe_scorecard.evidence_grounding.score:.1f}")
    table.add_row("Pre-Mortem Realism (1-5)", f"{base_scorecard.premortem_realism.score:.1f}", f"{pipe_scorecard.premortem_realism.score:.1f}")
    table.add_row("Prose Slop Absence (1-5)", f"{base_scorecard.prose_slop_absence.score:.1f}", f"{pipe_scorecard.prose_slop_absence.score:.1f}")
    table.add_row("Overall Score (1-5)", f"{base_scorecard.overall_score:.1f}", f"{pipe_scorecard.overall_score:.1f}")
    table.add_row("Slop Score (0-100, lower=better)", f"{baseline_lint.slop_score:.1f}", f"{pipeline_result.lint_result.slop_score:.1f}")
    table.add_row("Banned Clichés Count", str(len(baseline_lint.violations)), str(len(pipeline_result.lint_result.violations)))
    table.add_row("Strict Numerical Traceability", "Untracked", "PASSED" if pipeline_result.traceability_report.is_valid else "FAILED")

    console.print("\n")
    console.print(table)
    console.print("\n")
    console.print(token_tracker.get_summary_table())

    winner = "Thesis Pipeline" if judge_result.preferred_memo == label_pipe else "Baseline"
    console.print(Panel(f"[bold]Judge Preferred Memo[/bold]: [green]{winner}[/green]\n[italic]{judge_result.verdict_explanation}[/italic]"))

    # 6. Save Reports
    report_path = Path("eval_report.md")
    blind_path = Path("blind_eval.md")
    create_markdown_report(
        company_name=args.subject,
        baseline_memo=baseline_memo,
        pipeline_result=pipeline_result,
        baseline_lint=baseline_lint,
        judge_result=judge_result,
        label_baseline=label_base,
        label_pipeline=label_pipe,
        output_path=report_path,
    )
    create_blind_eval_file(
        baseline_memo=baseline_memo,
        pipeline_memo=pipeline_result.final_memo,
        label_baseline=label_base,
        label_pipeline=label_pipe,
        output_path=blind_path,
    )

    console.print(f"[bold green]Saved Benchmark Report to {report_path}[/bold green]")
    console.print(f"[bold green]Saved Blind Evaluation Sheet to {blind_path}[/bold green]")


if __name__ == "__main__":
    main()
