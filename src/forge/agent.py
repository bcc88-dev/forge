"""CLIDE agent loop - the core execution engine."""

import re
import difflib
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .config import load_config, save_config
from .api_client import chat, check_provider
from .memory import Memory
from .tools import TOOLS, describe_tools
from .license import LicenseClient

console = Console()
memory = Memory()
license = LicenseClient()

SYSTEM_PROMPT = """You are CLIDE. You help users build software.

You have persistent memory across sessions. Use [MEMORY: key=value] to remember things, [RECALL: query] to recall past memories.

Tools: {tools}

Memories from past sessions:
{memories}

Write files using ```filepath: path.ext blocks. Never edit CLIDE files. Be concise."""


def build_prompt(instruction: str, context: dict = None) -> str:
    try:
        recent = memory.history(10)
        mem_lines = [f"  - {m['key']}: {str(m['value'])[:80]}" for m in recent]
        mem_text = "\n".join(mem_lines) if mem_lines else "  (none)"
    except:
        mem_text = "  (unavailable)"

    cfg = load_config()
    cwd = str(Path.cwd())

    files = _get_file_list(cwd)

    project_summary = ""
    if context and context.get("summary"):
        project_summary = f"Project summary: {context['summary']}"

    return (
        f"{SYSTEM_PROMPT.format(tools=describe_tools(), memories=mem_text)}\n\n"
        f"Current directory: {cwd}\n"
        f"{project_summary}\n\n"
        f"Files in project:\n{files}\n\n"
        f"User request: {instruction}"
    )


def _get_file_list(cwd: str, max_files: int = 50) -> str:
    try:
        files = []
        for p in Path(cwd).rglob("*"):
            if p.is_file() and not any(x.startswith(".") for x in p.parts):
                rel = p.relative_to(cwd)
                files.append(str(rel))
        files.sort(key=lambda x: (x.count("/"), x.lower()))
        return "\n".join(files[:max_files])
    except:
        return "(could not list files)"


def parse_code_blocks(text: str):
    pattern = r"```filepath:\s*(.+?)\s*\n(.*?)(?=```|$)"
    blocks = []
    for match in re.finditer(pattern, text, re.DOTALL):
        path = match.group(1).strip()
        code = match.group(2).strip()
        if re.match(r"^[\w./\\-]+\.\w+$", path) and re.search(r"[a-zA-Z]", path):
            blocks.append((path, code))
    return blocks


def process_memory_commands(text: str):
    memories_stored = 0
    for match in re.finditer(r"\[MEMORY:\s*([^=]+)=(.+?)\]", text, re.IGNORECASE):
        key = match.group(1).strip()
        value = match.group(2).strip()
        memory.remember(key, value)
        memories_stored += 1
    for match in re.finditer(r"\[RECALL:\s*(.+?)\]", text, re.IGNORECASE):
        query = match.group(1).strip()
        results = memory.recall(query)
        if results:
            console.print(f"[dim]Memory recall ({query}): {len(results)} results[/dim]")
    if memories_stored:
        console.print(f"[dim]Stored {memories_stored} memory/ies[/dim]")


def show_diff(old: str, new: str, path: str):
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}"
    )
    diff_text = "".join(list(diff)[:30])
    if diff_text.strip():
        console.print("[dim]--- Preview diff ---[/dim]")
        console.print(diff_text[:2000])


def apply_edit(path: str, content: str) -> bool:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        old = p.read_text(encoding="utf-8") if p.exists() else ""
        if old:
            show_diff(old, content, path)
        p.write_text(content, encoding="utf-8")
        console.print(f"[green]Saved:[/green] {path}")
        memory.remember(f"edited {path}", f"Modified {path}", str(Path.cwd()))
        return True
    except Exception as e:
        console.print(f"[red]Failed to save {path}: {e}[/red]")
        return False


def run(instruction: str, auto: bool = False) -> dict:
    cfg = load_config()

    memory.remember("last_instruction", instruction[:200], str(Path.cwd()))

    prompt = build_prompt(instruction, {"summary": instruction[:250]})

    provider = cfg.get("provider", "ollama")
    model = cfg.get("model", "") or cfg.get("ollama_model", "")

    console.print(f"[dim]{provider}/{model or 'default'} working...[/dim]")

    response = chat(prompt, provider=provider, model=model or None)

    # Process any memory commands in the response
    process_memory_commands(response)

    console.print()
    console.print("=" * 70)
    if response.startswith("Error") or response.startswith("Ollama Error") or response.startswith("Groq Error"):
        console.print(f"[red]{response}[/red]")
        result = {"success": False, "error": response, "edits": 0}
    else:
        console.print(Markdown(response))
        console.print("=" * 70)

        edits = parse_code_blocks(response)
        edits_made = 0
        if edits:
            console.print(f"\n[bold cyan]Found {len(edits)} file change(s)[/bold cyan]")
            should_apply = auto or input("Apply changes? (y/n) -> ").lower() == "y"
            if should_apply:
                for path, code in edits:
                    if path and "forge" not in path.lower():
                        if apply_edit(path, code):
                            edits_made += 1
                    else:
                        console.print(f"[yellow]Skipped (protected):[/yellow] {path}")

        result = {"success": True, "response": response, "edits": edits_made}

    return result
