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


def cmd_interactive(args):
    """Run interactive mode."""
    console.print(Panel.fit(
        "[bold green]CLIDE[/bold green] - The AI coding agent that never forgets",
        border_style="green"
    ))

    instruction = " ".join(args.instruction).strip() if args.instruction else ""
    if not instruction:
        instruction = console.input("\n[bold]What should I do?[/bold]\n> ")

    run(instruction, auto=args.auto)


def cmd_config(args):
    """Manage configuration."""
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
                v = v[:8] + "..." if v else "[not set]"
            console.print(f"  {k} = {v}")


def cmd_memory(args):
    """Manage memory."""
    mem = Memory()
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
    """Check license status."""
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
    """Login to CLIDE Cloud."""
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
    """Create a CLIDE Cloud account."""
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
    """Check available providers."""
    for provider in ["ollama", "groq"]:
        available, models = check_provider(provider)
        status = "[green]available[/green]" if available else "[red]unavailable[/red]"
        console.print(f"  {provider}: {status}")
        if models:
            for m in models[:5]:
                console.print(f"    - {m}")


def main():
    parser = argparse.ArgumentParser(
        description="CLIDE - The AI coding agent that never forgets",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--version", action="version", version=f"clide {__version__}")
    parser.add_argument("--auto", action="store_true", help="Auto-apply changes")
    parser.add_argument("instruction", nargs="*", help="What to do")

    sub = parser.add_subparsers(dest="command", help="Commands")

    cfg_parser = sub.add_parser("config", help="Manage configuration")
    cfg_parser.add_argument("--set", metavar="KEY=VALUE", help="Set a config value")
    cfg_parser.add_argument("--get", metavar="KEY", help="Get a config value")

    mem_parser = sub.add_parser("memory", help="Manage memory")
    mem_parser.add_argument("--remember", metavar="KEY=VALUE", help="Store a memory")
    mem_parser.add_argument("--recall", metavar="QUERY", nargs="?", const="", help="Recall memories")

    lic_parser = sub.add_parser("license", help="License management")
    lic_parser.add_argument("--set", metavar="KEY", help="Set license key")

    login_parser = sub.add_parser("login", help="Login to CLIDE Cloud")
    login_parser.add_argument("--email", help="Email address")
    login_parser.add_argument("--password", help="Password")

    signup_parser = sub.add_parser("signup", help="Create CLIDE Cloud account")
    signup_parser.add_argument("--email", help="Email address")
    signup_parser.add_argument("--password", help="Password")

    sub.add_parser("providers", help="Check available providers")

    args = parser.parse_args()

    if args.command == "config":
        cmd_config(args)
    elif args.command == "memory":
        cmd_memory(args)
    elif args.command == "license":
        if args.set:
            LicenseClient().set_license_key(args.set)
            console.print(f"[green]License key saved[/green]")
        else:
            cmd_license(args)
    elif args.command == "login":
        cmd_login(args)
    elif args.command == "signup":
        cmd_signup(args)
    elif args.command == "providers":
        cmd_providers(args)
    else:
        cmd_interactive(args)
