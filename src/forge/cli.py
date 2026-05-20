"""CLIDE CLI - command line interface."""

import sys
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .config import load_config, save_config
from .agent import run
from .memory import Memory
from .supabase import supabase
from .license import LicenseClient
from .api_client import check_provider

console = Console()


def cmd_interactive(args, instruction_text=""):
    mem = Memory()
    sup_mode = mem.supabase_mode
    if "offline" in sup_mode:
        console.print(Panel.fit(
            "[bold green]CLIDE[/bold green] - local only (no Supabase)",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            f"[bold green]CLIDE[/bold green] - memory synced via Supabase ({sup_mode})",
            border_style="green"
        ))
    instruction = instruction_text
    if not instruction:
        instruction = console.input("\n[bold]What should I do?[/bold]\n> ")

    run(instruction, auto=args.auto)


def cmd_config(args):
    cfg = load_config()
    if args.set:
        key, value = args.set.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        save_config({key: value})
        console.print(f"[green]Set:[/green] {key} = {value[:20]}...")
    elif args.get:
        value = cfg.get(args.get, "[not set]")
        console.print(f"{args.get} = {value}")
    else:
        console.print("[bold]CLIDE Configuration:[/bold]")
        for k, v in cfg.items():
            if any(secret in k for secret in ["key", "secret", "token", "password"]):
                v = str(v)[:8] + "..." if v else "[not set]"
            console.print(f"  {k} = {v}")


def cmd_memory(args):
    mem = Memory()
    console.print(f"  Memory: local + Supabase {mem.supabase_mode}")
    if args.remember:
        parts = args.remember.split("=", 1)
        key = parts[0].strip()
        value = parts[1].strip() if len(parts) > 1 else console.input("Value: ")
        mem.remember(key, value)
        console.print(f"[green]Remembered:[/green] {key}")
    elif args.recall:
        results = mem.recall(args.recall)
        if results:
            for r in results:
                console.print(f"  [cyan]{r['key']}[/cyan]: {r['value'][:100]}")
        else:
            console.print("[yellow]No memories found[/yellow]")
    else:
        results = mem.history(20)
        console.print("[bold]Recent memories:[/bold]")
        for r in results:
            console.print(f"  [dim]{r['created_at'][:19]}[/dim] [cyan]{r['key']}[/cyan]")


def cmd_license(args):
    lic = LicenseClient()
    status = lic.validate()
    if status.get("valid"):
        source = status.get("source", "unknown")
        if source == "trial":
            days = status.get("days_remaining", 7)
            console.print(f"[yellow]Trial mode:[/yellow] {days} days remaining")
        else:
            console.print(f"[green]Licensed:[/green] via {source}")
    else:
        console.print("[red]No valid license found[/red]")
        console.print("Run: clide license --set YOUR_KEY")


def cmd_login(args):
    if not args.email:
        args.email = console.input("Email: ")
    if not args.password:
        import getpass
        args.password = getpass.getpass("Password: ")
    result = supabase.sign_in(args.email, args.password)
    if result.get("success"):
        console.print("[green]Logged in![/green]")
    else:
        console.print(f"[red]Login failed:[/red] {result.get('error', 'unknown')}")


def cmd_signup(args):
    if not args.email:
        args.email = console.input("Email: ")
    if not args.password:
        import getpass
        args.password = getpass.getpass("Password: ")
    result = supabase.sign_up(args.email, args.password)
    if result.get("success"):
        console.print("[green]Account created! Check your email for confirmation.[/green]")
    else:
        console.print(f"[red]Signup failed:[/red] {result.get('error', 'unknown')}")


def cmd_providers(args):
    for provider in ["ollama", "groq"]:
        available, models = check_provider(provider)
        status = "[green]available[/green]" if available else "[red]unavailable[/red]"
        console.print(f"  {provider}: {status}")
        if models:
            for m in models[:5]:
                console.print(f"    - {m}")


def cmd_status(args):
    mem = Memory()
    console.print("[bold]CLIDE Status[/bold]")
    console.print(f"  Version: {__version__}")
    console.print(f"  Memory: local + Supabase {mem.supabase_mode}")
    lic = LicenseClient()
    lic_status = lic.validate()
    if lic_status.get("valid"):
        console.print(f"  License: [green]active[/green] ({lic_status.get('source', 'unknown')})")
    else:
        console.print(f"  License: [yellow]trial[/yellow]")
    for provider in ["ollama", "groq"]:
        available, models = check_provider(provider)
        if available:
            console.print(f"  {provider}: [green]ok[/green]")
        else:
            console.print(f"  {provider}: [red]unavailable[/red]")


def main():
    parser = argparse.ArgumentParser(
        description="CLIDE - The AI coding agent that never forgets",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--version", action="version", version=f"clide {__version__}")
    parser.add_argument("--auto", action="store_true", help="Auto-apply changes")

    args, unknown = parser.parse_known_args()

    if not unknown:
        cmd_interactive(args)
        return

    cmd = unknown[0]
    cmd_args = unknown[1:]

    if cmd == "config":
        p = argparse.ArgumentParser(prog="clide config")
        p.add_argument("--set", metavar="KEY=VALUE")
        p.add_argument("--get", metavar="KEY")
        cmd_config(p.parse_args(cmd_args))
    elif cmd == "memory":
        p = argparse.ArgumentParser(prog="clide memory")
        p.add_argument("--remember", metavar="KEY=VALUE")
        p.add_argument("--recall", metavar="QUERY", nargs="?", const="")
        cmd_memory(p.parse_args(cmd_args))
    elif cmd == "license":
        p = argparse.ArgumentParser(prog="clide license")
        p.add_argument("--set", metavar="KEY")
        parsed = p.parse_args(cmd_args)
        if parsed.set:
            LicenseClient().set_license_key(parsed.set)
            console.print(f"[green]License key saved[/green]")
        else:
            cmd_license(parsed)
    elif cmd == "login":
        p = argparse.ArgumentParser(prog="clide login")
        p.add_argument("--email")
        p.add_argument("--password")
        cmd_login(p.parse_args(cmd_args))
    elif cmd == "signup":
        p = argparse.ArgumentParser(prog="clide signup")
        p.add_argument("--email")
        p.add_argument("--password")
        cmd_signup(p.parse_args(cmd_args))
    elif cmd == "providers":
        cmd_providers(None)
    elif cmd == "status":
        cmd_status(None)
    else:
        cmd_interactive(args, " ".join(unknown))


if __name__ == "__main__":
    main()
