#!/usr/bin/env python3
"""
NYX v2.2 — The General
Central Orchestrator + LiteLLM + Ollama Support
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
os.environ["OLLAMA_API_BASE"] = "http://localhost:11434"  # Default Ollama

# ====================== LITELLM SETUP ======================
try:
    from litellm import completion
    LITELLM_AVAILABLE = True
except ImportError:
    console.print("[yellow]LiteLLM not installed. Install with: pip install litellm[/yellow]")
    LITELLM_AVAILABLE = False

# ====================== MODEL STATUS DASHBOARD ======================
def show_model_status():
    table = Table(title="NYX Model Status", box=box.ROUNDED)
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Status", style="bold")
    table.add_column("Notes")

    # Ollama
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            table.add_row("Ollama (Local)", "nemotron-3-super", "[bold green]✓ Connected[/bold green]", "Powerful local model")
        else:
            table.add_row("Ollama", "-", "[red]Not responding[/red]", "")
    except:
        table.add_row("Ollama", "-", "[red]Not running[/red]", "Run: ollama serve")

    # OpenRouter
    if os.getenv("OPENROUTER_API_KEY"):
        table.add_row("OpenRouter", "Multiple", "[green]✓ Authenticated[/green]", "Cloud fallback")
    else:
        table.add_row("OpenRouter", "-", "[yellow]No API Key[/yellow]", "")

    console.print(table)

# ====================== CALL MODEL ======================
def call_model(prompt: str, model: str = "ollama_chat/nemotron-3-super"):
    if not LITELLM_AVAILABLE:
        return "LiteLLM not installed."

    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=4096
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Model error: {e}"

# ====================== MAIN ======================
async def main():
    console.print(Panel(
        "[bold magenta]NYX v2.2 — The General[/bold magenta]\n"
        "You speak only to Nyx • Nyx controls all subagents",
        border_style="magenta"
    ))

    show_model_status()

    while True:
        try:
            user_input = Prompt.ask("\n[bold white]You[/bold white]").strip()

            if user_input.lower() in ["/exit", "/quit", "exit"]:
                console.print("[yellow]Nyx standing down. All memory preserved.[/yellow]")
                break

            # Main Nyx reasoning prompt
            system_prompt = f"""You are Nyx, the central commander.
You have full control over powerful subagents (Basher, Editor, Reviewer, GitHub, Researcher, etc.).

Current capabilities:
- Run terminal commands, Docker, Ansible, Nginx, etc.
- Read/write files
- Use local Nemotron-3-Super (very strong)

User request: {user_input}

Think step by step. Decide which tools/subagents to use.
Be direct and capable. Maximize results."""

            response = call_model(system_prompt, model="ollama_chat/nemotron-3-super")

            console.print(Panel(response, title="[bold magenta]Nyx[/bold magenta]", border_style="magenta"))

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye.[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    asyncio.run(main())

