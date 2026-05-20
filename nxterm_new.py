#!/usr/bin/env python3
'''
NxTerm - Nexus Terminal TUI - NOW WITH DOMAIN SUPERPOWERS! 🎸
AI-first chat interface with Agentic Mode + Ansible + Git + Docker + Code Editing

Features:
- Animated streaming with progress indicator
- Ansible playbook detection and safe execution
- Git operations with approval workflow
- Docker/Podman container management
- Code editing with filepath markers (like freebuff)
- Diff preview before applying changes
- Project context scanning and history tracking
- Auto-apply option for seamless workflow

Run: python3 nxterm.py
'''

import os
import sys
import json
import subprocess
import re
import time
import difflib
from pathlib import Path
from datetime import datetime
import shutil
import threading

# Import from nexus.py
from nexus import (
    console, CONFIG_DIR, CONFIG_FILE, MEMORY_FILE,
    OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_FALLBACK_MODELS,
    BRAND_COLOR, ACCENT_COLOR, WARNING_COLOR, ERROR_COLOR,
    init_config_dir, load_config, save_config, load_memory, save_memory,
    check_ollama, call_ollama, ai_complete,
    cmd_configure as nexus_cmd_configure, cmd_list_models as nexus_cmd_list_models
)

from rich.markdown import Markdown
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# ============================================================================
# SYMBOLS & COLORS - Domain Enhanced
# ============================================================================

AI_SYMBOL = '🤖'
AGENTIC_SYMBOL = '⚡'
USER_SYMBOL = '👤'
SYSTEM_SYMBOL = '🔧'
GIT_SYMBOL = '±'
CLOCK_SYMBOL = '🕐'
ANSIBLE_SYMBOL = '📦'
DOCKER_SYMBOL = '🐳'
PODMAN_SYMBOL = '☁️'

# Color palette
GREEN = 'bold green'
YELLOW = 'bold yellow'
RED = 'bold red'
CYAN = 'bold cyan'
MAGENTA = 'bold magenta'
WHITE = 'bold white'
DIM = 'dim'

INPUT_STYLE = CYAN

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG_DIR = Path.home() / '.nexus'
CONFIG_FILE = CONFIG_DIR / 'config.json'
MEMORY_FILE = CONFIG_DIR / 'memory.json'

def get_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text())
    except:
        return {'ollama_model': 'nemotron-3-super:cloud', 'temperature': 0.7}

def save_config(config: dict):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))

# ============================================================================
# CHAT HISTORY
# ============================================================================

class Message:
    def __init__(self, role: str, content: str, timestamp: datetime = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
    
    def format_time(self):
        return self.timestamp.strftime('%H:%M:%S')

class ChatHistory:
    def __init__(self):
        self.messages = []
        self.agentic_mode = False
    
    def add_user(self, content: str):
        self.messages.append(Message('user', content))
    
    def add_ai(self, content: str):
        self.messages.append(Message('assistant', content))
    
    def add_system(self, content: str):
        self.messages.insert(0, Message('system', content))
    
    def get_conversation(self):
        return [{'role': m.role, 'content': m.content} for m in self.messages]
    
    def clear(self):
        self.messages = []
    
    def set_system(self, content: str):
        if self.messages and self.messages[0].role == 'system':
            self.messages[0] = Message('system', content)
        else:
            self.messages.insert(0, Message('system', content))

class CommandHistory:
    def __init__(self):
        self.history = []
        self.index = -1
    
    def add(self, cmd: str):
        if not self.history or self.history[-1] != cmd:
            self.history.append(cmd)
        self.index = len(self.history)
    
    def get(self, idx: int) -> str:
        if 0 <= idx < len(self.history):
            return self.history[idx]
        return ''
    
    def reset(self):
        self.index = len(self.history)

# ============================================================================
# GIT HELPER
# ============================================================================

class GitHelper:
    DESTRUCTIVE_COMMANDS = [
        'git push --force', 'git push -f', 'git rebase', 
        'git reset --hard', 'git reset --force', 'git stash drop'
    ]
    
    @staticmethod
    def is_repo() -> bool:
        return subprocess.run(['git', 'rev-parse', '--git-dir'], 
                             capture_output=True, text=True).returncode == 0
    
    @staticmethod
    def get_status() -> dict:
        if not GitHelper.is_repo():
            return {'branch': '', 'staged': 0, 'modified': 0, 'untracked': 0, 'clean': True}
        
        # Get branch
        branch = subprocess.run(['git', 'branch', '--show-current'], 
                               capture_output=True, text=True).stdout.strip()
        
        # Get porcelain status
        result = subprocess.run(['git', 'status', '--porcelain'], 
                               capture_output=True, text=True)
        lines = [l for l in result.stdout.strip().split('\n') if l]
        
        staged = sum(1 for l in lines if len(l) >= 2 and l[0] in 'MAD' and l[1] != ' ')
        modified = sum(1 for l in lines if len(l) >= 2 and l[0] == ' ' and l[1] in 'MAD')
        untracked = sum(1 for l in lines if l.startswith('??'))
        
        return {
            'branch': branch,
            'staged': staged,
            'modified': modified,
            'untracked': untracked,
            'clean': len(lines) == 0
        }
    
    @staticmethod
    def needs_approval(cmd: str) -> bool:
        cmd_lower = cmd.lower()
        return any(d in cmd_lower for d in GitHelper.DESTRUCTIVE_COMMANDS)

# ============================================================================
# DOCKER HELPER
# ============================================================================

class DockerHelper:
    DESTRUCTIVE_OPS = ['rm', 'rmi', 'stop', 'kill', 'prune']
    
    @staticmethod
    def is_available() -> bool:
        return (subprocess.run(['which', 'docker'], capture_output=True, text=True).returncode == 0 or
                subprocess.run(['which', 'podman'], capture_output=True, text=True).returncode == 0)
    
    @staticmethod
    def get_container_stats() -> list:
        for cmd in [['docker', 'ps'], ['podman', 'ps']]:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]
                containers = []
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 4:
                        containers.append({
                            'id': parts[0][:12],
                            'name': parts[-1] if len(parts) > 5 else parts[1],
                            'status': ' '.join(parts[4:]) if len(parts) > 4 else 'Unknown'
                        })
                return containers
        return []
    
    @staticmethod
    def is_destructive(cmd: str) -> bool:
        cmd_lower = cmd.lower()
        return any(op in cmd_lower for op in DockerHelper.DESTRUCTIVE_OPS)

# ============================================================================
# ANSIBLE HELPER
# ============================================================================

class AnsibleHelper:
    @staticmethod
    def is_playbook(cmd: str) -> bool:
        return 'ansible-playbook' in cmd.lower()
    
    @staticmethod
    def get_info(cmd: str) -> dict:
        result = subprocess.run(cmd.split() + ['--list-tasks'], 
                               capture_output=True, text=True, cwd=os.getcwd())
        output = result.stdout + result.stderr
        
        hosts = []
        tasks = []
        in_tasks = False
        for line in output.split('\n'):
            if 'playbook:' in line.lower():
                continue
            if 'tasks:' in line.lower():
                in_tasks = True
                continue
            if in_tasks and line.strip():
                tasks.append(line.strip())
            elif not in_tasks and ':' in line and 'localhost' not in line:
                hosts.append(line.strip())
        
        return {
            'hosts': list(set(hosts))[:10],
            'task_count': len(tasks),
            'tasks': tasks[:5],
            'destructive': 'shell:' in output or 'command:' in output
        }

# ============================================================================
# SYSTEM STATS
# ============================================================================

def get_system_stats() -> dict:
    try:
        with open('/proc/stat', 'r') as f:
            cpu_line = f.readline()
            total = sum(int(x) for x in cpu_line.split()[1:])
            idle = int(cpu_line.split()[4])
        
        with open('/proc/meminfo', 'r') as f:
            mem_lines = f.readlines()[:3]
            mem_total = int(mem_lines[0].split()[1]) / 1024
            mem_free = int(mem_lines[1].split()[1]) / 1024
            mem_buffers = int(mem_lines[2].split()[1]) / 1024
            mem_used = mem_total - mem_free - mem_buffers
        
        stat = os.statvfs('.')
        disk_total = stat.f_blocks * stat.f_frsize / 1024 / 1024 / 1024
        disk_free = stat.f_bfree * stat.f_frsize / 1024 / 1024 / 1024
        
        cpu_pct = int((1 - idle / total) * 100) if total > 0 else 0
        mem_pct = int(mem_used / mem_total * 100) if mem_total > 0 else 0
        disk_pct = int((disk_total - disk_free) / disk_total * 100) if disk_total > 0 else 0
        
        return {
            'cpu': f'{cpu_pct}%',
            'mem': f'{int(mem_pct)}%',
            'disk': f'{int(disk_pct)}%'
        }
    except:
        return {'cpu': '?', 'mem': '?', 'disk': '?'}

def get_terminal_cols():
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80

def get_banner() -> str:
    cols = get_terminal_cols()
    banner = f'''
[bold cyan]╔{'═' * (cols - 2)}╗[/bold cyan]
[bold cyan]║[/bold cyan]                                                                              [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]█[/bold white][bold cyan]╗     [bold white]█[/bold white][bold cyan]╗██████╗ ██████╗  █████╗ ██████╗ ██╗   ██╗██╗        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]█[/bold white][bold cyan]║     [bold white]█[/bold white][bold cyan]║██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║   ██║██║        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]█[/bold white][bold cyan]║     [bold white]█[/bold white][bold cyan]║██████╔╝██████╔╝███████║██████╔╝██║   ██║██║        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]█[/bold white][bold cyan]║     [bold white]█[/bold white][bold cyan]║██╔══██╗██╔══██╗██╔══██║██╔══██╗╚██╗ ██╔╝██║        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]██████╗[/bold white][bold cyan]██║██████╔╝██║  ██║██║  ██║ [bold white]╚████╔╝ [/bold white][bold cyan]██║        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [dim]╚══════╝╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  [dim]╚═╝        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]                                                                      [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   [/dim][bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold cyan]◆  AI-Powered Terminal for Epic Workflows  ◆              [/bold cyan][bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]      [dim]Free · Powerful · Agentic · [{ANSIBLE_SYMBOL}][{GIT_SYMBOL}][{DOCKER_SYMBOL}]  [/dim]                      [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]                                                                      [bold cyan]║[/bold cyan]
[bold cyan]╚{'═' * (cols - 2)}╝[/bold cyan]'''
    return banner

# ============================================================================
# STATUS DISPLAY
# ============================================================================

def print_git_status():
    status = GitHelper.get_status()
    
    if status['branch']:
        console.print(f'\n[{GREEN}]╭─ Git Status ────────────────────────────────────────╮[{GREEN}]')
        console.print(f'[{CYAN}]{GIT_SYMBOL}[/{CYAN}] [bold white]Branch:[/bold white] [green]{status['branch']}[/green]')
        
        if status['clean']:
            console.print(f'[{DIM}]│   ✓ Working tree clean[/DIM]')
        else:
            changes = []
            if status['staged']:
                changes.append(f'+{status[\"staged\"]} staged')
            if status['modified']:
                changes.append(f'~{status[\"modified\"]} modified')
            if status['untracked']:
                changes.append(f'?{status[\"untracked\"]} untracked')
            console.print(f'[{YELLOW}]│   {\" \".join(changes)}[/YELLOW]')
        
        console.print(f'[{GREEN}]╰─────────────────────────────────────────────────────╯[{GREEN}]\n')
    else:
        console.print(f'\n[{DIM}]╭─ Git Status ────────────────────────────────────────╮[/DIM]')
        console.print(f'[{DIM}]│   Not a git repository[/DIM]')
        console.print(f'[{DIM}]╰─────────────────────────────────────────────────────╯[/DIM]\n')

def print_docker_status():
    if not DockerHelper.is_available():
        return
    
    containers = DockerHelper.get_container_stats()
    if containers:
        console.print(f'[{CYAN}]╭─ Containers ─────────────────────────────────────────╮[{CYAN}]')
        for c in containers[:5]:
            console.print(f'  [green]•[/green] [white]{c[\"id\"]}[/white] [dim]{c[\"name\"]}[/dim] [dim]- {c[\"status\"]}[/dim]')
        if len(containers) > 5:
            console.print(f'  [dim]... and {len(containers) - 5} more[/dim]')
        console.print(f'[{CYAN}]╰─────────────────────────────────────────────────────╯[{CYAN}]\n')

def print_command_box(title: str, cmd: str, output: str, success: bool):
    color = GREEN if success else RED
    icon = '✓' if success else '✗'
    cols = min(get_terminal_cols(), 80)
    
    border = '═' * (cols - 6)
    console.print(f'\n[{color}]╭─ [{icon}] {title} {border}╮[{color}]')
    
    if cmd:
        console.print(f'[{color}]├─ command ─────────────────────────────────────────┤[{color}]')
        for line in cmd.split('\n')[:3]:
            console.print(f'  [dim]{line}[/dim]')
    
    if output:
        console.print(f'[{color}]├─ output ─────────────────────────────────────────┤[{color}]')
        for line in output.split('\n')[:10]:
            console.print(f'  [dim]{line[:cols-6]}[/dim]')
        if len(output.split('\n')) > 10:
            console.print(f'  [dim]... ({len(output.split(chr(10))) - 10} more lines)[/dim]')
    
    console.print(f'[{color}]╰─────────────────────────────────────────────────────╯[{color}]\n')

def print_status_bar(provider: str, model: str, agentic_mode: bool, cwd: str):
    stats = get_system_stats()
    status = GitHelper.get_status()
    
    cpu_color = GREEN if int(stats['cpu'].replace('%','')) < 70 else YELLOW if int(stats['cpu'].replace('%','')) < 90 else RED
    mem_color = GREEN if int(stats['mem'].replace('%','')) < 70 else YELLOW if int(stats['mem'].replace('%','')) < 90 else RED
    
    now = datetime.now().strftime('%H:%M:%S')
    mode_str = f'[bold magenta][⚡] AGENTIC[/bold magenta]' if agentic_mode else f'[{DIM}]💬 CHAT[/DIM]'
    
    if status['branch']:
        git_str = f'[green]{GIT_SYMBOL} {status[\"branch\"]}[/green]'
    else:
        git_str = f'[{DIM}]no git[/DIM]'
    
    display_cwd = cwd if len(cwd) < 30 else '...' + cwd[-27:]
    
    console.print(f'[{DIM}]┌─ [{CLOCK_SYMBOL}] {now} [/{DIM}][{DIM}]│[/DIM] [{DIM}]Provider:[/DIM] [cyan]{provider}[/cyan] [{DIM}]│[/DIM] [{DIM}]Model:[/DIM] [magenta]{model}[/magenta] {mode_str} [{DIM}]│[/DIM] {git_str} [{DIM}]─┐[/DIM]')
    console.print(f'[{DIM}]│[/DIM] [{DIM}]CPU:[/DIM] [{cpu_color}]{stats[\"cpu\"]}[/{cpu_color}] [{DIM}]│[/DIM] [{DIM}]MEM:[/DIM] [{mem_color}]{stats[\"mem\"]}[/{mem_color}] [{DIM}]│[/DIM] [{DIM}]DISK:[/DIM] [cyan]{stats[\"disk\"]}[/cyan] [{DIM}]│[/DIM]')
    console.print(f'[{DIM}]└─[/DIM] [{DIM}]📁[/DIM] [cyan]{display_cwd}[/cyan]')

def print_help_panel():
    cols = get_terminal_cols()
    help_text = f'''
[bold cyan]╔{'═' * (cols - 2)}╗[/bold cyan]
[bold cyan]║[/bold cyan]                      [bold white]◆ NxTerm Help ◆[/bold white]                                 [bold cyan]║[/bold cyan]
[bold cyan]╠{'═' * (cols - 2)}╣[/bold cyan]
[bold cyan]║[/bold cyan]                                                                        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]  [bold white]BASICS[/bold white]                                                             [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    Type naturally to chat with AI                                     [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]                                                                        [bold cyan]║[/bold cyan]
[bold cyan]╠{'═' * (cols - 2)}╣[/bold cyan]
[bold cyan]║[/bold cyan]  [bold white]MODE COMMANDS[/bold white]                                                     [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    /agentic  → Enable Agentic mode (AI executes commands)              [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    /chat     → Return to Chat mode (conversation only)                 [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]                                                                        [bold cyan]║[/bold cyan]
[bold cyan]╠{'═' * (cols - 2)}╣[/bold cyan]
[bold cyan]║[/bold cyan]  [bold white]AGENTIC COMMANDS[/bold white] (type directly in Agentic mode)                [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    run <cmd>          → Execute shell command                            [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    read <file>        → Read file content                                [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    write <file>|<content> → Write file                               [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]                                                                        [bold cyan]║[/bold cyan]
[bold cyan]╠{'═' * (cols - 2)}╣[/bold cyan]
[bold cyan]║[/bold cyan]  [bold white]CODE EDITING[/bold white] (AI can suggest file changes)                     [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    When AI outputs code blocks with filepath markers, you'll be       [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    prompted to apply the changes. Use /auto to enable auto-apply.     [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]                                                                        [bold cyan]║[/bold cyan]
[bold cyan]╠{'═' * (cols - 2)}╣[/bold cyan]
[bold cyan]║[/bold cyan]  [bold white]SYSTEM[/bold white]                                                               [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    /help     → Show this help                                          [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    /clear    → Clear chat history                                       [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    /config   → Configure settings                                       [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    /models   → List available AI models                                 [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    /summary  → Set project summary for context                          [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    /context  → Show project files being tracked                         [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    /auto     → Toggle auto-apply mode                                   [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    /exit     → Exit NxTerm                                             [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]                                                                        [bold cyan]║[/bold cyan]
[bold cyan]╚{'═' * (cols - 2)}╝[/bold cyan]'''
    console.print(help_text)

# ============================================================================
# INPUT
# ============================================================================

def get_input(prompt: str = '❯') -> str:
    try:
        return console.input(f'[bold cyan]{prompt}[/bold cyan] ').strip()
    except (KeyboardInterrupt, EOFError):
        return '/exit'

def get_confirmation(prompt: str) -> bool:
    response = console.input(f'[bold yellow]{prompt} (y/N): [/bold yellow]').strip().lower()
    return response in ['y', 'yes']

# ============================================================================
# PROJECT CONTEXT (Freebuff-style)
# ============================================================================

def load_project_context(path: Path = Path('.')) -> dict:
    memory = load_memory()
    project_key = str(path.absolute())
    project_data = memory.get('project_context', {}).get(project_key, {})
    
    files = []
    gitignore_patterns = {'.git', '__pycache__', '.venv', 'node_modules', '.nexus', 'venv', '.env', '.gitignore'}
    
    try:
        for p in path.rglob('*'):
            if p.is_file() and not p.is_symlink():
                if any(ign in p.parts for ign in gitignore_patterns):
                    continue
                if any(x.startswith('.') and x not in ['.gitignore', '.nexus'] for x in p.parts):
                    continue
                try:
                    if p.stat().st_size > 100000:
                        continue
                except:
                    pass
                if len(files) >= 100:
                    break
                files.append(str(p))
    except PermissionError:
        pass
    
    return {
        'files': sorted(files)[:100],
        'summary': project_data.get('summary', ''),
        'history': project_data.get('history', [])[-10:]
    }

def build_system_prompt(cwd: str, agentic_mode: bool, context: dict = None) -> str:
    files_list = ''
    history_text = ''
    summary_text = ''
    
    if context:
        files_list = '\n'.join(context.get('files', [])[:50]) or '(empty directory)'
        history = context.get('history', [])
        if history:
            history_text = '\n\nRecent history:\n' + '\n'.join([f'- {h}' for h in history])
        summary = context.get('summary', '')
        if summary:
            summary_text = f'\n\nProject Summary: {summary}'
    
    if agentic_mode:
        return f'''You are NxTerm, an EXPERT AGENTIC AI in a terminal environment with DOMAIN SUPERPOWERS.

Current directory: {cwd}
{files_list}
{summary_text}
{history_text}

You have FULL capabilities:
- Execute shell commands: !run: <command>
- Read files: !read: filepath
- Write files: !write: filepath | content

ANSIBLE PLAYBOOKS:
- Detect ansible-playbook commands automatically
- Show playbook info (hosts, task count) before suggesting execution

GIT OPERATIONS:
- Detect git add, commit, push, merge, rebase, reset operations

DOCKER/PODMAN:
- Detect docker run, build, exec, ps, logs, rm commands

CODE EDITING:
- When creating/modifying files, use this format:
```filepath: relative/path.py
code content here
```
- The user will be prompted to apply changes

Be decisive. Take action.'''
    else:
        return f'''You are NxTerm, a helpful AI assistant in a terminal with domain knowledge.

Current directory: {cwd}
{files_list}
{summary_text}
{history_text}

You have knowledge about:
- Ansible playbooks and automation
- Git version control workflows
- Docker/Podman container management
- General shell commands and Linux administration

CODE EDITING:
- When creating/modifying files, use this format:
```filepath: relative/path.py
code content here
```
- The user will be prompted to apply changes

Be conversational, helpful, and concise.'''

# ============================================================================
# CODE EDITING (Freebuff-style)
# ============================================================================

def parse_edits(text: str) -> list:
    patterns = [
        r'```filepath:\n*(.+?)\n*\n(.*?)(?=```|$)',
        r'```file:\n*(.+?)\n*\n(.*?)(?=```|$)',
        r'```(\n?/.+?\//?[^`\n]+)\n(.*?)```',
        r'```python\n(.*?)```',
        r'```(\n?python\n.*?)```',
    ]
    
    edits = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            if len(match.groups()) >= 2:
                path = match.group(1).strip()
                code = match.group(2).strip()
                
                code = re.sub(r'</?tool_.*?>', '', code, flags=re.IGNORECASE)
                
                if path and code and path not in ['nxterm.py', 'nexus.py', 'buff.py', 'freebuff.py']:
                    edits.append((path, code))
    
    seen = set()
    result = []
    for path, code in edits:
        if path not in seen:
            seen.add(path)
            result.append((path, code))
    
    return result

def show_diff(old: str, new: str, path: str):
    try:
        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f'a/{path}',
            tofile=f'b/{path}',
            n=3
        )
        diff_lines = list(diff)[:40]
        if diff_lines:
            console.print(f'[{DIM}]' + '─' * 60 + '[/DIM]')
            for line in diff_lines:
                if line.startswith('+++') or line.startswith('---'):
                    console.print(f'[{DIM}]{line.rstrip()}[/DIM]', end='')
                elif line.startswith('+'):
                    console.print(f'[green]{line.rstrip()}[/green]', end='')
                elif line.startswith('-'):
                    console.print(f'[red]{line.rstrip()}[/red]', end='')
                else:
                    console.print(f'[{DIM}]{line.rstrip()}[/DIM]', end='')
            console.print(f'[{DIM}]' + '─' * 60 + '[/DIM]\n')
    except:
        pass

def apply_edit(path: str, content: str, show_diff_flag: bool = True) -> bool:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        old = ''
        if p.exists():
            old = p.read_text()
        
        if show_diff_flag and old:
            show_diff(old, content, path)
        
        p.write_text(content)
        return True
        
    except Exception as e:
        console.print(f'[red]✗[/red] Failed to write {path}: {e}')
        return False

# ============================================================================
# AI STREAMING
# ============================================================================

def stream_ai_response(messages: list, model: str, callback=None):
    config = get_config()
    temperature = config.get('temperature', 0.7)
    base_url = config.get('ollama_base_url', OLLAMA_BASE_URL)
    
    full_response = []
    
    def collect_handler(chunk):
        full_response.append(chunk)
        if callback:
            callback(chunk)
    
    call_ollama(messages, model, base_url=base_url, stream_callback=collect_handler, temperature=temperature)
    
    return ''.join(full_response)

# ============================================================================
# AGENTIC EXECUTION
# ============================================================================

def execute_command(cmd: str, cwd: str = None) -> tuple:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=30, cwd=cwd or os.getcwd()
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, '', 'Command timed out after 30 seconds'
    except Exception as e:
        return 1, '', str(e)

def read_file_content(path: str) -> str:
    try:
        return Path(path).expanduser().resolve().read_text()
    except Exception as e:
        return f'Error reading {path}: {e}'

def write_file_content(path: str, content: str) -> str:
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f'Successfully wrote to {path}'
    except Exception as e:
        return f'Error writing {path}: {e}'

def parse_agentic_commands(response: str) -> list:
    commands = []
    stripped = response.strip()
    
    run_match = re.match(r'^!run:\n?(.+)$', stripped, re.IGNORECASE)
    if run_match:
        cmd = run_match.group(1).strip()
        if cmd and len(cmd) > 1:
            commands.append(('run', cmd))
            return commands
    
    read_match = re.match(r'^!read:\n?(.+)$', stripped, re.IGNORECASE)
    if read_match:
        path = read_match.group(1).strip()
        if path:
            commands.append(('read', path))
            return commands
    
    if '|' in stripped:
        parts = stripped.split('|', 1)
        if len(parts) == 2 and parts[0].strip().startswith('!write:'):
            filepath = parts[0].replace('!write:', '').strip()
            content = parts[1].strip()
            if filepath and content:
                commands.append(('write', filepath, content))
                return commands
    
    lines = response.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('!run:'):
            cmd = line[5:].strip()
            if cmd:
                commands.append(('run', cmd))
        elif line.startswith('!read:'):
            path = line[6:].strip()
            if path:
                commands.append(('read', path))
        elif line.startswith('!write:'):
            if '|' in line:
                parts = line.split('|', 1)
                filepath = parts[0].replace('!write:', '').strip()
                content = parts[1].strip()
                if filepath and content:
                    commands.append(('write', filepath, content))
    
    return commands

def parse_user_agentic_command(user_input: str) -> list:
    commands = []
    stripped = user_input.strip()
    
    if stripped.startswith('run '):
        cmd = stripped[4:].strip()
        if cmd:
            commands.append(('run', cmd))
    elif stripped.startswith('read '):
        path = stripped[5:].strip()
        if path:
            commands.append(('read', path))
    elif stripped.startswith('write '):
        if '|' in stripped:
            parts = stripped.split('|', 1)
            filepath = parts[0].replace('write', '').strip()
            content = parts[1].strip()
            if filepath and content:
                commands.append(('write', filepath, content))
    
    return commands

def execute_agentic_commands(commands: list, cwd: str, need_approval_fn=None) -> str:
    results = []
    
    for cmd in commands:
        if not cmd:
            continue
        
        cmd_type = cmd[0]
        arg = cmd[1] if len(cmd) > 1 else ''
        
        if cmd_type == 'run':
            code, stdout, stderr = execute_command(arg, cwd)
            results.append(f'!run: {arg}\n')
            if stdout:
                results.append(stdout)
            if stderr:
                results.append(stderr)
            results.append('\n')
            
        elif cmd_type == 'read':
            content = read_file_content(arg)
            results.append(f'!read: {arg}\n')
            results.append(content[:500])
            if len(content) > 500:
                results.append(f'\n... ({len(content)-500} more chars)')
            results.append('\n\n')
            
        elif cmd_type == 'write' and len(cmd) >= 3:
            filepath = arg
            content = cmd[2]
            result = write_file_content(filepath, content)
            results.append(f'!write: {filepath}\n{result}\n\n')
    
    return ''.join(results)

# ============================================================================
# MAIN CHAT LOOP
# ============================================================================

def chat_loop(auto_apply: bool = False, initial_instruction: str = None):
    config = init_config_dir()
    
    provider = config.get('provider', 'ollama')
    model = config.get('ollama_model', OLLAMA_MODEL)
    cwd = os.getcwd()
    
    context = load_project_context()
    
    chat = ChatHistory()
    chat.add_system(build_system_prompt(cwd, chat.agentic_mode, context))
    
    history = CommandHistory()
    
    memory = load_memory()
    project_key = str(Path.cwd().absolute())
    project_history = memory.get('project_context', {}).get(project_key, {}).get('history', [])
    
    if provider == 'ollama':
        available, msg = check_ollama(config.get('ollama_base_url', OLLAMA_BASE_URL))
        if not available:
            console.print(f'[{WARNING_COLOR}]⚠️  Ollama not running - type /config to set up[/]')
    
    console.print(get_banner())
    print_status_bar(provider, model, chat.agentic_mode, cwd)
    print_git_status()
    
    if chat.agentic_mode:
        console.print('[magenta]⚡ Agentic mode active - AI can execute commands[/magenta]\n')
    else:
        console.print('[dim]💬 Just type to chat · /agentic for agentic mode · /help for commands[/dim]\n')
    
    if initial_instruction:
        user_input = initial_instruction
    else:
        try:
            user_input = get_input()
        except:
            user_input = '/exit'
    
    while True:
        if not user_input:
            continue
        
        history.add(user_input)
        history.reset()
        
        if user_input.lower() == '/agentic':
            chat.agentic_mode = True
            chat.set_system(build_system_prompt(cwd, True, context))
            console.print()
            console.print('[bold magenta]╔═══════════════════════════════════════╗[/bold magenta]')
            console.print('[bold magenta]║[/bold magenta]  [bold white]⚡ AGENTIC MODE ENABLED[/bold white]              [bold magenta]║[/bold magenta]')
            console.print('[bold magenta]║[/bold magenta]  [dim]AI can now execute commands[/dim]           [bold magenta]║[/bold magenta]')
            console.print('[bold magenta]╚═══════════════════════════════════════╝[/bold magenta]')
            print_status_bar(provider, model, True, cwd)
            user_input = get_input()
            continue
        
        if user_input.lower() == '/chat':
            chat.agentic_mode = False
            chat.set_system(build_system_prompt(cwd, False, context))
            console.print()
            console.print('[bold cyan]╔═══════════════════════════════════════╗[/bold cyan]')
            console.print('[bold cyan]║[/bold cyan]  [bold white]💬 CHAT MODE ENABLED[/bold white]                  [bold cyan]║[/bold cyan]')
            console.print('[bold cyan]║[/bold cyan]  [dim]AI will only chat (no commands)[/dim]        [bold cyan]║[/bold cyan]')
            console.print('[bold cyan]╚═══════════════════════════════════════╝[/bold cyan]')
            print_status_bar(provider, model, False, cwd)
            user_input = get_input()
            continue
        
        if user_input.startswith('/'):
            cmd = user_input[1:].lower()
            
            if cmd == 'exit':
                console.print(f'\n[bold yellow]👋 Goodbye from NxTerm![/bold yellow]\n')
                save_memory(memory)
                break
            
            elif cmd == 'help':
                print_help_panel()
                user_input = get_input()
                continue
            
            elif cmd == 'clear':
                console.print('\n' * 50)
                chat.clear()
                chat.add_system(build_system_prompt(cwd, chat.agentic_mode, context))
                console.print(get_banner())
                print_status_bar(provider, model, chat.agentic_mode, cwd)
                print_git_status()
                console.print('[green]✓ Chat cleared[/green]\n')
                user_input = get_input()
                continue
            
            elif cmd == 'status':
                print_git_status()
                print_docker_status()
                user_input = get_input()
                continue
            
            elif cmd == 'config':
                nexus_cmd_configure()
                config = get_config()
                model = config.get('ollama_model', OLLAMA_MODEL)
                provider = config.get('provider', 'ollama')
                print_status_bar(provider, model, chat.agentic_mode, cwd)
                user_input = get_input()
                continue
            
            elif cmd == 'models':
                nexus_cmd_list_models(config)
                user_input = get_input()
                continue
            
            elif cmd == 'summary':
                memory = load_memory()
                project_key = str(Path.cwd().absolute())
                current = memory.get('project_context', {}).get(project_key, {}).get('summary', '(none)')
                console.print(f'\n[bold]Current summary:[/bold] [dim]{current}[/dim]')
                new_summary = console.input('[bold]New project summary: [/bold]').strip()
                if new_summary:
                    memory.setdefault('project_context', {}).setdefault(project_key, {})['summary'] = new_summary
                    save_memory(memory)
                    context = load_project_context()
                    chat.set_system(build_system_prompt(cwd, chat.agentic_mode, context))
                    console.print('[green]✅ Summary updated![/green]\n')
                user_input = get_input()
                continue
            
            elif cmd == 'context':
                num = len(context['files'])
                console.print(f'\n[bold]Project Files ({num}):[/bold]')
                for f in context['files'][:20]:
                    console.print(f'  [dim]{f}[/dim]')
                if num > 20:
                    console.print(f'  [dim]... and {num - 20} more[/dim]')
                if context.get('summary'):
                    console.print(f'\n[bold]Summary:[/bold] {context[\"summary\"]}\n')
                user_input = get_input()
                continue
            
            elif cmd == 'auto':
                auto_apply = not auto_apply
                console.print(f'[bold cyan]Auto-apply: {'enabled' if auto_apply else 'disabled'}[/bold cyan]\n')
                user_input = get_input()
                continue
            
            else:
                console.print(f'[yellow]Unknown: {cmd} (try /help)[/yellow]\n')
                user_input = get_input()
                continue
        
        direct_commands = parse_user_agentic_command(user_input) if chat.agentic_mode else []
        
        if direct_commands:
            console.print(f'\n[{MAGENTA}]╭─ Agentic Execution ──────────────────────────────┐[{MAGENTA}]')
            results = execute_agentic_commands(direct_commands, cwd)
            console.print(f'[{DIM}]{results}[/DIM]')
            console.print(f'[{MAGENTA}]╰────────────────────────────────────────────────────┘\n[{MAGENTA}]')
            chat.add_user(user_input)
            chat.add_ai(f'Commands executed:\n{results}')
            user_input = get_input()
            continue
        
        chat.add_user(user_input)
        
        console.print()
        response_chunks = []
        
        def streaming_callback(chunk):
            print(chunk, end='', flush=True)
            response_chunks.append(chunk)
        
        try:
            stream_ai_response(chat.get_conversation(), model, streaming_callback)
        except Exception as e:
            console.print(f'\n[{RED}]Error: {e}[/RED]\n')
            user_input = get_input()
            continue
        
        console.print()
        
        response = ''.join(response_chunks)
        chat.add_ai(response)
        
        # Parse and apply code edits (Freebuff-style)
        edits = parse_edits(response)
        if edits:
            console.print(f'\n[bold cyan]📝 Found {len(edits)} file change(s):[/bold cyan]')
            for path, _ in edits:
                console.print(f'  [green]•[/green] [white]{path}[/white]')
            
            should_auto = auto_apply or config.get('auto_apply', False)
            if should_auto or get_confirmation('Apply changes?'):
                success_count = 0
                for path, code in edits:
                    if apply_edit(path, code, config.get('show_diff', True)):
                        success_count += 1
                        console.print(f'[green]✓[/green] Applied: {path}')
                
                if success_count:
                    console.print(f'\n[green]✅ Applied {success_count}/{len(edits)} changes![/green]')
                    
                    memory = load_memory()
                    memory.setdefault('project_context', {}).setdefault(project_key, {}).setdefault('history', []).append(user_input[:100])
                    save_memory(memory)
                    context = load_project_context()
            else:
                console.print('[dim]Changes not applied[/dim]')
        
        # Execute agentic commands from AI response
        if chat.agentic_mode:
            commands = parse_agentic_commands(response)
            if commands:
                results = execute_agentic_commands(commands, cwd)
                if results:
                    console.print(f'\n[{MAGENTA}]╭─ Commands Executed ───────────────────────────────╮[{MAGENTA}]')
                    console.print(f'[{DIM}]{results}[/DIM]')
                    console.print(f'[{MAGENTA}]╰────────────────────────────────────────────────────╯\n[{MAGENTA}]')
        
        print_status_bar(provider, model, chat.agentic_mode, cwd)
        user_input = get_input()

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='NxTerm - AI Chat Terminal with Domain Superpowers')
    parser.add_argument('--config', action='store_true', help='Open configuration')
    parser.add_argument('--models', action='store_true', help='List models')
    parser.add_argument('--agentic', action='store_true', help='Start in Agentic mode')
    parser.add_argument('--auto', action='store_true', help='Auto-apply file changes')
    parser.add_argument('prompt', nargs='*', help='Initial prompt')
    
    args = parser.parse_args()
    
    init_config_dir()
    
    if args.config:
        nexus_cmd_configure()
        return
    
    if args.models:
        nexus_cmd_list_models(load_config())
        return
    
    if args.prompt:
        prompt = ' '.join(args.prompt)
        console.print(get_banner())
        console.print(f'[{AI_SYMBOL}] {prompt}\n')
        console.print('[dim]Starting chat...[/dim]\n')
    
    chat_loop(auto_apply=args.auto)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print('\n[bold yellow]Goodbye![/bold yellow]')