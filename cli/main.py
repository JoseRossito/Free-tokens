import os
import sys

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

console = Console()


def _make_client(
    model: str,
    system: str,
    no_response_cache: bool,
    no_prompt_cache: bool,
    strategy: str,
    context_tokens: int,
    cache_dir: str | None,
    cache_ttl: int,
):
    from free_tokens import FreeTokensClient
    from free_tokens.storage import UsageStorage

    return FreeTokensClient(
        model=model,
        system=system,
        max_context_tokens=context_tokens,
        context_strategy=strategy,
        response_cache_enabled=not no_response_cache,
        prompt_cache_enabled=not no_prompt_cache,
        cache_dir=cache_dir or None,
        cache_ttl=cache_ttl,
        storage=UsageStorage(),
    )


@click.group()
def cli():
    """free-tokens — Save Claude API tokens automatically."""


@cli.command()
@click.option("--model", default="claude-sonnet-4-6", show_default=True)
@click.option("--system", default="You are a helpful assistant.", show_default=True)
@click.option("--no-response-cache", is_flag=True)
@click.option("--no-prompt-cache", is_flag=True)
@click.option("--strategy", default="trim", type=click.Choice(["trim", "summarize"]), show_default=True)
@click.option("--context-tokens", default=150_000, show_default=True)
@click.option("--cache-dir", default=None)
@click.option("--cache-ttl", default=3600, show_default=True)
def chat(model, system, no_response_cache, no_prompt_cache, strategy, context_tokens, cache_dir, cache_ttl):
    """Multi-turn interactive chat with automatic token savings."""
    client = _make_client(model, system, no_response_cache, no_prompt_cache, strategy, context_tokens, cache_dir, cache_ttl)

    console.print(f"[bold green]free-tokens chat[/bold green] — model: {model} | strategy: {strategy}")
    console.print("Type [bold]exit[/bold] or [bold]quit[/bold] to end. [bold]/reset[/bold] clears history.\n")

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            break

        if user_input.strip().lower() in ("exit", "quit"):
            break
        if user_input.strip().lower() == "/reset":
            client.reset_conversation()
            console.print("[yellow]Conversation cleared.[/yellow]")
            continue
        if not user_input.strip():
            continue

        try:
            response = client.chat(user_input)
            console.print("[bold magenta]Claude[/bold magenta]")
            console.print(Markdown(response))
            console.print()
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    console.print("\n[bold]Session summary:[/bold]")
    client.get_usage_report()
    cache_stats = client._response_cache.stats()
    console.print(f"Response cache — hits: {cache_stats['hits']}, misses: {cache_stats['misses']}")


@cli.command()
@click.argument("prompt")
@click.option("--model", default="claude-sonnet-4-6", show_default=True)
@click.option("--system", default="", show_default=True)
@click.option("--no-response-cache", is_flag=True)
@click.option("--no-prompt-cache", is_flag=True)
@click.option("--max-tokens", default=1024, show_default=True)
@click.option("--cache-dir", default=None)
@click.option("--cache-ttl", default=3600, show_default=True)
def single(prompt, model, system, no_response_cache, no_prompt_cache, max_tokens, cache_dir, cache_ttl):
    """Send a single prompt without conversation history."""
    client = _make_client(model, system, no_response_cache, no_prompt_cache, "trim", 150_000, cache_dir, cache_ttl)
    try:
        response = client.send_single(prompt, max_tokens=max_tokens)
        console.print(Markdown(response))
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    finally:
        client.get_usage_report()


@cli.command()
@click.argument("prompt")
@click.option("--times", default=3, show_default=True)
@click.option("--model", default="claude-sonnet-4-6", show_default=True)
@click.option("--max-tokens", default=256, show_default=True)
@click.option("--cache-dir", default=None)
@click.option("--cache-ttl", default=3600, show_default=True)
def bench(prompt, times, model, max_tokens, cache_dir, cache_ttl):
    """Send the same prompt N times to demonstrate response cache hit rate."""
    client = _make_client(model, "", False, True, "trim", 150_000, cache_dir, cache_ttl)
    console.print(f"[bold]Benchmarking[/bold] '{prompt[:60]}...' × {times}\n")

    for i in range(1, times + 1):
        response = client.send_single(prompt, max_tokens=max_tokens)
        stats = client._response_cache.stats()
        label = "[green]HIT[/green]" if i > 1 else "[yellow]MISS[/yellow]"
        console.print(f"  Turn {i} {label}: {response[:80].strip()}...")

    console.print()
    client.get_usage_report()
    stats = client._response_cache.stats()
    hit_rate = stats["hits"] / (stats["hits"] + stats["misses"]) * 100 if (stats["hits"] + stats["misses"]) > 0 else 0
    console.print(f"Cache hit rate: [bold green]{hit_rate:.0f}%[/bold green] ({stats['hits']}/{stats['hits'] + stats['misses']})")


@cli.command()
@click.option("--days", default=7, show_default=True, help="Número de días a incluir en el reporte.")
def report(days):
    """Muestra el reporte de uso de tokens de los últimos N días."""
    from free_tokens.storage import UsageStorage
    from free_tokens.report import ReportGenerator
    ReportGenerator(UsageStorage()).print_report(days=days)


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8080, show_default=True)
@click.option("--model", default="claude-sonnet-4-6", show_default=True)
@click.option("--system", default="You are a helpful assistant.", show_default=True)
def serve(host, port, model, system):
    """Inicia un servidor HTTP para integrar free-tokens con otras apps (agente de WhatsApp, etc.).

    \b
    Endpoints disponibles:
      POST /chat          — chat multi-turno (session_id para separar conversaciones)
      POST /single        — pregunta única sin historial
      DELETE /session/:id — reinicia una conversación
      GET  /report        — reporte JSON de uso
      GET  /health        — health check
    """
    try:
        import uvicorn
    except ImportError:
        console.print("[red]Instala las dependencias del servidor:[/red] pip install 'free-tokens[server]'")
        return
    from free_tokens.server import create_app
    app = create_app(model=model, system=system)
    console.print(f"[bold green]free-tokens API[/bold green] corriendo en [cyan]http://{host}:{port}[/cyan]")
    console.print("[dim]POST /chat  POST /single  DELETE /session/:id  GET /report  GET /health[/dim]")
    uvicorn.run(app, host=host, port=port)
