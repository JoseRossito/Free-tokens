from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from rich.console import Console
from rich.table import Table


@dataclass
class UsageRecord:
    source: Literal["api", "response_cache", "prompt_cache"]
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    prompt_preview: str = ""
    model: str = ""
    session_id: str = ""


@dataclass
class UsageTracker:
    _records: list[UsageRecord] = field(default_factory=list)

    def record(self, rec: UsageRecord) -> None:
        self._records.append(rec)

    def total_input_tokens(self) -> int:
        return sum(r.input_tokens for r in self._records)

    def total_output_tokens(self) -> int:
        return sum(r.output_tokens for r in self._records)

    def tokens_saved_response_cache(self) -> int:
        return sum(
            r.input_tokens + r.output_tokens
            for r in self._records
            if r.source == "response_cache"
        )

    def tokens_saved_prompt_cache(self) -> int:
        # cache_read tokens are charged at ~10% of normal; saving is 90% of those tokens
        total_read = sum(r.cache_read_input_tokens for r in self._records)
        return int(total_read * 0.9)

    def api_calls(self) -> int:
        return sum(1 for r in self._records if r.source == "api")

    def cache_hits(self) -> int:
        return sum(1 for r in self._records if r.source == "response_cache")

    def print_report(self) -> None:
        console = Console()
        table = Table(title="Token Usage Report", show_lines=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")

        table.add_row("Total turns", str(len(self._records)))
        table.add_row("API calls", str(self.api_calls()))
        table.add_row("Response cache hits", str(self.cache_hits()))
        table.add_row("Input tokens used", str(self.total_input_tokens()))
        table.add_row("Output tokens used", str(self.total_output_tokens()))
        table.add_row("Saved via response cache", str(self.tokens_saved_response_cache()))
        table.add_row("Saved via prompt cache (~90%)", str(self.tokens_saved_prompt_cache()))

        console.print(table)
