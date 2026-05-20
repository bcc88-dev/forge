#!/usr/bin/env python3
"""
Forge v3 - Premium Cloud Coding Agent
Inspired by Freebuff
"""

import os
import argparse
import re
import requests
import difflib
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

MODEL = "openrouter/free"
OLLAMA_MODEL = "nematron3"
OLLAMA_BASE_URL = "http://localhost:11434"
MEMORY_FILE = Path(".forge_memory.json")
CONFIG_FILE = Path(".forge_config.json")
DEFAULT_PROVIDER = "openrouter"

def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except:
            return {}
    return {}

def save_config(config):
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")

def load_memory():
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except:
            return {"history": [], "summary": ""}
    return {"history": [], "summary": ""}

def save_memory(memory):
    MEMORY_FILE.write_text(json.dumps(memory, indent=2), encoding="utf-8")

def get_key():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        console.print("\n[bold yellow]🔑 OpenRouter API key required[/bold yellow]")
        console.print("Go to → [link=https://openrouter.ai/keys]https://openrouter.ai/keys[/link]")
        key = console.input("Paste your key (sk-or-...): ").strip()
    return key

def call_openrouter(prompt: str):
    key = get_key()
    if not key:
        return "Error: No API key"

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://forge.local",
                "X-OpenRouter-Title": "Forge-v3"
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 14000
            },
            timeout=100
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"API Error {r.status_code}"
    except Exception as e:
        return f"Connection error: {e}"

def call_ollama(prompt: str, model: str = OLLAMA_MODEL, stream_callback=None):
    try:
        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            },
            timeout=120,
            stream=True
        )
        if r.status_code == 200:
            full_response = []
            for line in r.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            chunk = data["message"]["content"]
                            full_response.append(chunk)
                            if stream_callback:
                                stream_callback(chunk)
                    except json.JSONDecodeError:
                        pass
            return "".join(full_response)
        return f"Ollama Error {r.status_code}: {r.text}"
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to Ollama at {OLLAMA_BASE_URL}. Is Ollama running?"
    except Exception as e:
        return f"Connection error: {e}"

def check_ollama_available():
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return r.status_code == 200, r.json().get("models", []) if r.status_code == 200 else []
    except:
        return False, []

def parse_code_blocks(text: str):
    patterns = [
        r"```filepath:\s*(.+?)\s*\n(.*?)(?=```|$)",
        r"```(?:python)?\s*(\S+)\s*\n(.*?)(?=```|$)"
    ]
    edits = []
    for pattern in patterns:
        for path, code in re.findall(pattern, text, re.DOTALL | re.IGNORECASE):
            path = path.strip()
            code = re.sub(r'</?tool_.*?>', '', code, flags=re.IGNORECASE).strip()
            if path and code and not path.lower().endswith("forge.py"):
                edits.append((path, code))
    return edits

def show_diff(old: str, new: str, path: str):
    diff = difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                fromfile=f"a/{path}", tofile=f"b/{path}")
    console.print("[dim]--- Preview diff ---[/dim]")
    console.print("".join(list(diff)[:40]))

def apply_edit(path: str, content: str):
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        old = p.read_text(encoding="utf-8") if p.exists() else ""
        if old:
            show_diff(old, content, path)
        p.write_text(content, encoding="utf-8")
        console.print(f"[green]✅ Successfully saved:[/green] [bold]{path}[/bold]")
        return True
    except Exception as e:
        console.print(f"[red]❌ Failed to save {path}: {e}[/red]")
        return False

def main():
    console.print(Panel.fit("[bold green]🔨 Forge v3[/bold green] - Your Personal Cloud Coding Agent", border_style="green"))

    parser = argparse.ArgumentParser(description="Forge v3")
    parser.add_argument("instruction", nargs="*", help="What to do")
    parser.add_argument("--auto", action="store_true", help="Auto-apply changes")
    config = load_config()
    
    # Config file defaults override hardcoded defaults, CLI args override both
    default_provider = config.get("provider", DEFAULT_PROVIDER)
    default_ollama_model = config.get("ollama_model", OLLAMA_MODEL)
    
    parser.add_argument("--provider", choices=["openrouter", "ollama"], 
                        default=config.get("provider", DEFAULT_PROVIDER),
                        help="AI provider to use")
    parser.add_argument("--ollama-model", 
                        default=config.get("ollama_model", OLLAMA_MODEL),
                        help=f"Ollama model name")
    parser.add_argument("--save-config", action="store_true",
                        help="Save current provider/model as default settings")
    args = parser.parse_args()

    instruction = " ".join(args.instruction).strip()
    if not instruction:
        instruction = console.input("\n[bold]What should I do?[/bold]\n→ ")

    memory = load_memory()

    provider = args.provider
    
    if provider == "ollama":
        ollama_available, available_models = check_ollama_available()
        if not ollama_available:
            console.print(f"[yellow]⚠️  Ollama not available at {OLLAMA_BASE_URL}[/yellow]")
            console.print("[dim]Make sure Ollama is running with: ollama serve[/dim]")
            if available_models:
                model_names = [m.get("name", str(m)) for m in available_models]
                console.print(f"[dim]Available models: {', '.join(model_names)}[/dim]")
            if console.input("Continue anyway? (y/n) → ").lower() != 'y':
                return
        elif available_models:
            model_names = [m.get("name", str(m)) for m in available_models]
            console.print(f"[dim]Available Ollama models: {', '.join(model_names)}[/dim]")
        
        model_display = args.ollama_model
        console.print(f"[dim]Provider:[/dim] [cyan]ollama[/cyan]   [dim]Model:[/dim] {model_display}   [dim]Folder:[/dim] {Path.cwd()}\n")
    else:
        console.print(f"[dim]Provider:[/dim] [cyan]openrouter[/cyan]   [dim]Model:[/dim] {MODEL}   [dim]Folder:[/dim] {Path.cwd()}\n")

    files = [str(p) for p in Path(".").rglob("*") if p.is_file() and not any(x.startswith(".") for x in p.parts)][:70]

    prompt = (
        "You are Forge v3, a clean and highly effective coding agent.\n\n"
        f"Current directory: {Path.cwd()}\n"
        f"Project summary: {memory.get('summary', 'New project')}\n\n"
        "Files:\n" + "\n".join(sorted(files)) + "\n\n"
        f"User request: {instruction}\n\n"
        "Rules:\n"
        "- Be concise and action-oriented.\n"
        "- Never edit forge.py or .forge_memory.json\n"
        "- When making changes, output using exactly this format:\n\n"
        "```filepath: filename.py\n"
        "FULL CODE HERE\n"
        "```\n"
    )

    if provider == "ollama":
        console.print(f"[yellow]🤖 Thinking with Ollama ({args.ollama_model})...[/yellow]\n")
        response_buffer = []
        def stream_handler(chunk):
            response_buffer.append(chunk)
            print(chunk, end="", flush=True)
        response = call_ollama(prompt, model=args.ollama_model, stream_callback=stream_handler)
        if response_buffer:
            print()  # Newline after streaming
    else:
        console.print("[yellow]🤖 Thinking on cloud...[/yellow]\n")
        response = call_openrouter(prompt)

    console.print("=" * 90)
    console.print(Markdown(response))
    console.print("=" * 90)

    edits = parse_code_blocks(response)
    if edits:
        console.print(f"\n[bold cyan]🔧 Found {len(edits)} file change(s)[/bold cyan]")
        if args.auto or console.input("Apply them? (y/n) → ").lower() == 'y':
            for path, code in edits:
                apply_edit(path, code)
            
            if args.save_config:
                config["provider"] = provider
                config["ollama_model"] = args.ollama_model
                save_config(config)
                console.print(f"[green]✅ Config saved to {CONFIG_FILE}[/green]")
            
            memory["history"].append(instruction[:150])
            memory["summary"] = instruction[:250]
            save_memory(memory)
    else:
        console.print("\n[dim]No file changes detected.[/dim]")

    console.print("\n[green]✅ Done! Ready for the next task.[/green]")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
