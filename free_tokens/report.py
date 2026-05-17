import warnings
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from .storage import UsageStorage

# Precios oficiales Anthropic por millón de tokens (input, output, cache_read)
# Fuente: https://www.anthropic.com/pricing — mayo 2026
_PRICES: dict[str, tuple[float, float, float]] = {
    "claude-haiku-4-5":  (1.00,  5.00, 0.10),
    "claude-sonnet-4-6": (3.00, 15.00, 0.30),
    "claude-opus-4-7":  (15.00, 75.00, 1.50),
}
_FALLBACK_PRICES = (3.00, 15.00, 0.30)  # Sonnet como fallback


def _get_prices(model: str) -> tuple[float, float, float]:
    for prefix, prices in _PRICES.items():
        if model.startswith(prefix):
            return prices
    warnings.warn(
        f"Modelo '{model}' no encontrado en tabla de precios; usando precios de Sonnet como fallback.",
        stacklevel=2,
    )
    return _FALLBACK_PRICES


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

        # Aggregate — costo calculado por registro con el precio correcto de su modelo
        by_day: dict = {}
        totals = dict(api=0, hits=0, input=0, output=0, cache_read=0, saved_response=0)
        cost_used = 0.0
        cost_saved = 0.0

        for r in records:
            day = r["timestamp"][:10]
            if day not in by_day:
                by_day[day] = dict(api=0, hits=0, input=0, output=0, saved=0)

            in_p, out_p, cr_p = _get_prices(r.get("model", ""))

            if r["source"] == "api":
                by_day[day]["api"] += 1
                by_day[day]["input"] += r["input_tokens"]
                by_day[day]["output"] += r["output_tokens"]
                totals["api"] += 1
                totals["input"] += r["input_tokens"]
                totals["output"] += r["output_tokens"]
                totals["cache_read"] += r["cache_read_tokens"]
                cost_used += (r["input_tokens"] * in_p + r["output_tokens"] * out_p) / 1_000_000
                cost_saved += r["cache_read_tokens"] * (in_p - cr_p) / 1_000_000
            elif r["source"] == "response_cache":
                saved = r["input_tokens"] + r["output_tokens"]
                by_day[day]["hits"] += 1
                by_day[day]["saved"] += saved
                totals["hits"] += 1
                totals["saved_response"] += saved
                cost_saved += saved * (in_p + out_p) / 2 / 1_000_000

        saved_prompt = int(totals["cache_read"] * 0.9)

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
        summary.add_row("Costo estimado", f"${cost_used:.4f}")
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
