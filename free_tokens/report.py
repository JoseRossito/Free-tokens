from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from .storage import UsageStorage

# Approximate Haiku pricing (per million tokens)
INPUT_COST  = 0.80
OUTPUT_COST = 4.00
CACHE_READ_COST = 0.08


class ReportGenerator:
    def __init__(self, storage: UsageStorage):
        self._db = storage

    def print_report(self, days: int = 7) -> None:
        since = datetime.now() - timedelta(days=days)
        records = self._db.get_records(since)
        console = Console()

        if not records:
            console.print(f"[yellow]No hay registros en los últimos {days} días.[/yellow]")
            return

        # Aggregate
        by_day: dict = {}
        totals = dict(api=0, hits=0, input=0, output=0, cache_read=0, saved_response=0)

        for r in records:
            day = r["timestamp"][:10]
            if day not in by_day:
                by_day[day] = dict(api=0, hits=0, input=0, output=0, saved=0)
            if r["source"] == "api":
                by_day[day]["api"] += 1
                by_day[day]["input"] += r["input_tokens"]
                by_day[day]["output"] += r["output_tokens"]
                totals["api"] += 1
                totals["input"] += r["input_tokens"]
                totals["output"] += r["output_tokens"]
                totals["cache_read"] += r["cache_read_tokens"]
            elif r["source"] == "response_cache":
                saved = r["input_tokens"] + r["output_tokens"]
                by_day[day]["hits"] += 1
                by_day[day]["saved"] += saved
                totals["hits"] += 1
                totals["saved_response"] += saved

        saved_prompt = int(totals["cache_read"] * 0.9)
        cost_used = (totals["input"] * INPUT_COST + totals["output"] * OUTPUT_COST) / 1_000_000
        cost_saved = (totals["saved_response"] * (INPUT_COST + OUTPUT_COST) / 2 +
                      totals["cache_read"] * (INPUT_COST - CACHE_READ_COST)) / 1_000_000

        # Summary
        summary = Table(show_header=False, box=None, padding=(0, 1))
        summary.add_column("", style="cyan")
        summary.add_column("", justify="right", style="green")
        summary.add_row("Llamadas a la API", str(totals["api"]))
        summary.add_row("Response cache hits", str(totals["hits"]))
        summary.add_row("Tokens entrada usados", f"{totals['input']:,}")
        summary.add_row("Tokens salida usados", f"{totals['output']:,}")
        summary.add_row("Ahorro response cache", f"{totals['saved_response']:,} tokens")
        summary.add_row("Ahorro prompt cache (~90%)", f"{saved_prompt:,} tokens")
        summary.add_row("Costo estimado (Haiku)", f"${cost_used:.4f}")
        summary.add_row("Costo ahorrado estimado", f"${cost_saved:.4f}")
        console.print(Panel(summary, title=f"Reporte — últimos {days} días", border_style="purple"))

        # Daily breakdown
        table = Table(title="Desglose por día", show_lines=True)
        table.add_column("Fecha", style="cyan")
        table.add_column("API calls", justify="right")
        table.add_column("Cache hits", justify="right", style="green")
        table.add_column("Tokens entrada", justify="right")
        table.add_column("Tokens salida", justify="right")
        table.add_column("Tokens ahorrados", justify="right", style="green")

        for day, d in sorted(by_day.items()):
            dt = datetime.fromisoformat(day)
            label = dt.strftime("%a %d %b")
            table.add_row(
                label,
                str(d["api"]),
                str(d["hits"]),
                f"{d['input']:,}",
                f"{d['output']:,}",
                f"{d['saved']:,}",
            )
        console.print(table)
