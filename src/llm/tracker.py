"""Token usage tracking and analytics across all pipeline stages."""

from typing import List, Optional
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

console = Console()


class TokenRecord(BaseModel):
    """Token metrics for a single LLM invocation."""
    stage_name: str
    model: str
    prompt_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class TokenTracker:
    """Singleton tracker capturing token consumption across pipeline execution."""

    def __init__(self):
        self.records: List[TokenRecord] = []
        self._current_stage: str = "General"

    def set_current_stage(self, stage_name: str) -> None:
        """Set the active stage label for subsequent LLM calls."""
        self._current_stage = stage_name

    def record_usage(
        self,
        model: str,
        prompt_tokens: int,
        output_tokens: int,
        total_tokens: Optional[int] = None,
        stage_name: Optional[str] = None,
    ) -> TokenRecord:
        """Record token usage for an invocation."""
        label = stage_name or self._current_stage
        tot = total_tokens if total_tokens is not None else (prompt_tokens + output_tokens)
        record = TokenRecord(
            stage_name=label,
            model=model,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            total_tokens=tot,
        )
        self.records.append(record)
        console.print(
            f"     [dim]↳ Tokens: {prompt_tokens:,} input | {output_tokens:,} output | {tot:,} total[/dim]"
        )
        return record

    def get_summary_table(self) -> Table:
        """Render a formatted Rich table summarizing token usage by stage."""
        table = Table(title="Empirical Token Usage Breakdown")
        table.add_column("Stage / Invocation", style="cyan", no_wrap=True)
        table.add_column("Model", style="blue")
        table.add_column("Input Tokens", justify="right", style="magenta")
        table.add_column("Output Tokens", justify="right", style="green")
        table.add_column("Total Tokens", justify="right", style="bold yellow")

        cum_in = 0
        cum_out = 0
        cum_tot = 0
        max_out = 0

        for r in self.records:
            cum_in += r.prompt_tokens
            cum_out += r.output_tokens
            cum_tot += r.total_tokens
            if r.output_tokens > max_out:
                max_out = r.output_tokens
            table.add_row(
                r.stage_name,
                r.model,
                f"{r.prompt_tokens:,}",
                f"{r.output_tokens:,}",
                f"{r.total_tokens:,}",
            )

        table.add_section()
        table.add_row(
            "[bold]TOTALS[/bold]",
            f"Peak Output: {max_out:,}",
            f"[bold]{cum_in:,}[/bold]",
            f"[bold]{cum_out:,}[/bold]",
            f"[bold]{cum_tot:,}[/bold]",
        )
        return table

    def get_markdown_summary(self) -> str:
        """Generate a markdown table of token usage for reports."""
        lines = [
            "### Empirical Token Usage Matrix",
            "",
            "| Stage / Step | Model | Input Tokens | Output Tokens | Total Tokens |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        cum_in = 0
        cum_out = 0
        cum_tot = 0
        max_out = 0

        for r in self.records:
            cum_in += r.prompt_tokens
            cum_out += r.output_tokens
            cum_tot += r.total_tokens
            if r.output_tokens > max_out:
                max_out = r.output_tokens
            lines.append(
                f"| {r.stage_name} | `{r.model}` | {r.prompt_tokens:,} | {r.output_tokens:,} | {r.total_tokens:,} |"
            )

        lines.append(
            f"| **TOTALS (Peak Output: {max_out:,})** | - | **{cum_in:,}** | **{cum_out:,}** | **{cum_tot:,}** |"
        )
        return "\n".join(lines)


# Global singleton instance
token_tracker = TokenTracker()
