#!/usr/bin/env python3
"""
NYX v2.3 — The General
Fixed + Cleaner Version
"""

import os
import sys
import asyncio
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

console = Console()

# ====================== CONFIG ======================
os.environ["OLLAMA_API_BASE"] = "http://localhost:11434"

# ====================== LITELLM ======================
try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# ====================== MODEL STATUS ======================
def show_model_status():
    table = Table(title="NYX Model Status", show_header=True)
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Status")

    # Ollama Check
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code == 200:
            table.add_row("Ollama (Local)", "nemotron-3-super", "[bold green]CONNECTED[/bold green]")
        else:
            table.add_row("Ollama", "-", "[red]Not responding[/red]")
    except:
        table.add_row("Ollama", "-", "[red]Not running[/red]")

    # OpenRouter
    if os.getenv("OPENROUTER_API_KEY"):
        table.add_row("OpenRouter", "Cloud Models", "[green]Authenticated[/green]")
    else:
        table.add_row("OpenRouter", "-", "[yellow]No Key[/yellow]")

    console.print(table)

# ====================== CALL MODEL ======================
def call_model(prompt: str, model: str = "ollama_chat/nemotron-3-super"):
    if not LITELLM_AVAILABLE:
        return "Please install litellm: pip install litellm"

    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.35,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Model Error: {str(e)[:150]}"

# ====================== MAIN ======================
async def main():
    console.print(Panel(
        "[bold magenta]NYX v2.3 — The General[/bold magenta]\n"
        "You speak only to Nyx • Nyx controls all agents",
        border_style="magenta"
    ))

    show_model_status()

    while True:
        try:
            user_input = Prompt.ask("\n[bold white]You[/bold white]").strip()

            if user_input.lower() in ["/exit", "/quit", "exit"]:
                console.print("[yellow]Nyx standing down.[/yellow]")
                break

            prompt = f"""You are Nyx — a highly capable AI commander.
You can use powerful tools: terminal commands, file operations, Docker, GitHub, etc.

User: {user_input}

Respond directly and powerfully. Use tools when needed."""

            response = call_model(prompt)

            console.print(Panel(response, title="Nyx", border_style="magenta"))

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye.[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    if not LITELLM_AVAILABLE:
        console.print("[yellow]Run: pip install litellm rich httpx[/yellow]")
    asyncio.run(main())

