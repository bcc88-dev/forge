#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║                    NYX v2.0 — The General                     ║
║        Persistent Supermemory • Universal Agents • GitHub     ║
╚═══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import hashlib
import asyncio
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich import box
    import httpx
    from supabase import create_client, Client
except ImportError as e:
    print(f"[!] Missing dependency: {e}")
    print("   pip install rich httpx supabase-py")
    sys.exit(1)

console = Console()

# ========================= CONFIG =========================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
SUPABASE_URL       = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY       = os.getenv("SUPABASE_ANON_KEY", "")

# ====================== SUPABASE SUPERMEMORY ======================
class SupabaseMemory:
    def __init__(self):
        self.client = None
        self.project_id = "nyx-main-project"  # Change if you want multiple projects
        self._connect()

    def _connect(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            console.print("[yellow]⚠ Running without Supabase (ephemeral mode)[/yellow]")
            return
        try:
            self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
            console.print(f"[green]✓ Supermemory connected (500GB available)[/green]")
        except Exception as e:
            console.print(f"[red]Supabase connection failed: {e}[/red]")

    async def write(self, agent: str, type_: str, content: str, metadata: dict = None, importance: float = 0.7):
        if not self.client:
            return
        try:
            self.client.table("context").insert({
                "project_id": self.project_id,
                "agent": agent,
                "type": type_,
                "content": content[:25000],
                "metadata": {**(metadata or {}), "timestamp": datetime.utcnow().isoformat()},
                "importance": importance
            }).execute()
        except:
            pass

    async def recall(self, query: str, limit: int = 12, hours_ago: int = 72) -> List[Dict]:
        """Universal powerful recall"""
        if not self.client:
            return []
        try:
            # Semantic + recency hybrid (vector not used yet - can be added)
            result = self.client.table("context").select(
                "agent,type,content,metadata,importance,created_at"
            ).eq("project_id", self.project_id)\
             .gte("created_at", (datetime.utcnow() - timedelta(hours=hours_ago)).isoformat())\
             .order("importance", desc=True)\
             .limit(limit).execute()
            return result.data or []
        except:
            return []

    async def get_project_state(self) -> str:
        """Restore last known state"""
        if not self.client:
            return "No previous state found."
        try:
            data = self.client.table("context").select("content")\
                .eq("project_id", self.project_id)\
                .eq("type", "project_state")\
                .order("created_at", desc=True).limit(1).execute()
            return data.data[0]["content"] if data.data else "New project session."
        except:
            return "New project session."

# ====================== GITHUB AUTOMATER ======================
class GitHubAutomater:
    def __init__(self):
        self.available = subprocess.run(["which", "gh"], capture_output=True).returncode == 0

    async def handle(self, task: str, memory: SupabaseMemory):
        console.print(f"[bold green]GitHub Automater[/bold green] → {task}")

        if "create repo" in task.lower():
            name = Prompt.ask("Repository name")
            result = subprocess.run(["gh", "repo", "create", name, "--public", "--source=.", "--push"], 
                                  capture_output=True, text=True)
            await memory.write("github", "repo_create", result.stdout or result.stderr, {"repo": name})
            return result.stdout or result.stderr

        elif any(x in task.lower() for x in ["commit", "save"]):
            msg = Prompt.ask("Commit message", default="Updates from Nyx v2.0")
            subprocess.run(["git", "add", "."], check=True)
            result = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True)
            await memory.write("github", "commit", result.stdout, {"message": msg})
            return result.stdout or "Committed."

        elif "push" in task.lower():
            result = subprocess.run(["git", "push"], capture_output=True, text=True)
            return result.stdout or result.stderr

        elif "pr" in task.lower():
            title = Prompt.ask("PR Title", default="Nyx Changes")
            result = subprocess.run(["gh", "pr", "create", "--title", title, "--body", "Generated by Nyx"], 
                                  capture_output=True, text=True)
            return result.stdout or result.stderr

        else:
            # Raw command fallback
            try:
                args = task.split()
                result = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=30)
                return result.stdout or result.stderr
            except Exception as e:
                return f"Error: {e}"

# ====================== UNIVERSAL AGENT ======================
async def universal_agent(agent_name: str, task: str, memory: SupabaseMemory):
    console.print(f"[bold blue]→ {agent_name.upper()}[/bold blue]")

    # Universal Recall
    memories = await memory.recall(task, limit=10)
    context = "\n".join([f"[{m['agent']}] {m['content'][:280]}" for m in memories])

    system_prompt = f"""You are {agent_name} — a specialized subagent of NYX.
You have access to long-term project memory.
Be concise, high-signal, and professional."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Recent Context:\n{context}\n\nTask: {task}"}
    ]

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen/qwen3-coder-480b-a35b-instruct:free",
                    "messages": messages,
                    "temperature": 0.3
                }
            )
            resp.raise_for_status()
            answer = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        answer = f"Agent unavailable: {e}"

    await memory.write(agent_name.lower(), "output", answer, {"task": task[:120]}, importance=0.8)
    console.print(Panel(answer[:1200], title=agent_name, border_style="blue"))
    return answer

# ====================== MAIN ======================
async def main():
    console.print(Panel(
        "[bold magenta]NYX v2.0 — The General[/bold magenta]\n"
        "Persistent Supermemory • GitHub Automater • Universal Agents",
        border_style="magenta"
    ))

    memory = SupabaseMemory()
    github = GitHubAutomater()

    # Restore last state
    last_state = await memory.get_project_state()
    console.print(Panel(last_state[:500] + ("..." if len(last_state) > 500 else ""), 
                       title="Restored Project State", border_style="dim"))

    while True:
        try:
            user_input = Prompt.ask("\n[bold white]You[/bold white]").strip()

            if user_input.lower() in ["/exit", "exit", "/quit"]:
                # Save final state
                await memory.write("nyx", "project_state", "Session ended. Ready to resume.", importance=1.0)
                console.print("[yellow]Nyx standing down. Memory preserved.[/yellow]")
                break

            # GitHub Agent
            if user_input.lower().startswith(("/github", "/git", "@github", "@git")):
                task = user_input.split(maxsplit=1)[1] if " " in user_input else "status"
                await github.handle(task, memory)

            # Specific Agent
            elif user_input.lower().startswith("/agent "):
                parts = user_input[7:].split(maxsplit=1)
                agent = parts[0]
                task = parts[1] if len(parts) > 1 else "What should we do next?"
                await universal_agent(agent, task, memory)

            # Default Smart Flow
            else:
                await universal_agent("Planner", user_input, memory)
                await universal_agent("Recall", f"Summarize current project state: {user_input}", memory)
                await universal_agent("Basher", "Show git status and project files", memory)

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye. All memory saved.[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    if not OPENROUTER_API_KEY:
        console.print("[red]Please export OPENROUTER_API_KEY[/red]")
        sys.exit(1)
    asyncio.run(main())
