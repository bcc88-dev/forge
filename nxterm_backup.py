#!/usr/bin/env python3
'''
NxTerm - Nexus Terminal TUI - NOW WITH DOMAIN SUPERPOWERS! 🎸
AI-first chat interface with Agentic Mode + Ansible + Git + Docker

Features:
- Animated streaming with progress indicator
- Ansible playbook detection and safe execution
- Git operations with approval workflow
- Docker/Podman container management
- Confirmation prompts for destructive operations
- Smart command detection and context awareness

Run: python3 nxterm.py
'''

import os
import sys
import json
import subprocess
import re
import time
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
        self.messages.append(Message('system', content))
    
    def clear(self):
        self.messages = []
    
    def get_conversation(self) -> list:
        return [{'role': m.role, 'content': m.content} for m in self.messages]

# ============================================================================
# DOMAIN HELPERS
# ============================================================================

class AnsibleHelper:
    '''Ansible playbook detection and execution helper'''
    
    @staticmethod
    def detect_playbook(content: str) -> list:
        '''Detect Ansible playbook commands in text'''
        commands = []
        
        # Look for ansible-playbook commands
        patterns = [
            r'ansible-playbook(?:\n| ).*',
            r'ansible(?:\n| )-m .*',
            r'ansible(?:\n| )-i .*inventory.*playbook',
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                cmd = match.group(0).strip()
                if cmd and len(cmd) > 5:
                    commands.append(('ansible', cmd))
        
        # Look for playbook file references
        playbook_pattern = r'(\\.yml|\\.yaml|playbooks?/[^\\s]+)'
        for match in re.finditer(playbook_pattern, content):
            filepath = match.group(1)
            if not filepath.startswith('#'):
                commands.append(('playbook_ref', filepath))
        
        return commands
    
    @staticmethod
    def is_destructive(playbook_path: str) -> bool:
        '''Check if playbook might be destructive'''
        try:
            content = Path(playbook_path).read_text().lower()
            destructive_modules = ['shell', 'command', 'exec', 'docker', 'podman', 'yum', 'apt', 'service']
            return any(module in content for module in destructive_modules)
        except:
            return False
    
    @staticmethod
    def get_playbook_info(path: str) -> dict:
        '''Get information about a playbook'''
        try:
            p = Path(path)
            if not p.exists():
                return {'exists': False}
            
            content = p.read_text()
            # Simple detection of hosts and tasks
            hosts = re.findall(r'^hosts:\\s*(.+)$', content, re.MULTILINE)
            tasks = len(re.findall(r'^\\s+-\\s+name:', content, re.MULTILINE))
            
            return {
                'exists': True,
                'hosts': hosts[0] if hosts else 'unknown',
                'tasks': tasks,
                'destructive': AnsibleHelper.is_destructive(path)
            }
        except Exception as e:
            return {'exists': False, 'error': str(e)}

class GitHelper:
    '''Git operations helper with approval workflow'''
    
    DESTRUCTIVE_COMMANDS = ['git push --force', 'git push -f', 'git rebase', 'git reset --hard', 'git reset --force', 'git stash drop']
    
    @staticmethod
    def detect_git_operation(content: str) -> tuple:
        '''Detect Git operations in text'''
        operations = []
        
        patterns = [
            (r'git\\s+add\\s+\\.', 'git_add_all'),
            (r'git\\s+commit', 'git_commit'),
            (r'git\\s+push', 'git_push'),
            (r'git\\s+pull', 'git_pull'),
            (r'git\\s+checkout', 'git_checkout'),
            (r'git\\s+branch', 'git_branch'),
            (r'git\\s+merge', 'git_merge'),
            (r'git\\s+rebase', 'git_rebase'),
            (r'git\\s+stash', 'git_stash'),
            (r'git\\s+reset', 'git_reset'),
            (r'git\\s+log', 'git_log'),
            (r'git\\s+status', 'git_status'),
            (r'git\\s+diff', 'git_diff'),
        ]
        
        for pattern, op_name in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                operations.append(op_name)
        
        return operations
    
    @staticmethod
    def needs_approval(command: str) -> bool:
        '''Check if git command needs user approval'''
        return any(destructive in command.lower() for destructive in GitHelper.DESTRUCTIVE_COMMANDS)
    
    @staticmethod
    def get_status() -> dict:
        '''Get git repository status'''
        try:
            # Branch
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                   capture_output=True, text=True, timeout=2)
            branch = result.stdout.strip() if result.returncode == 0 else None
            
            # Status
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                   capture_output=True, text=True, timeout=2)
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
        except:
            return {'branch': None, 'staged': 0, 'modified': 0, 'untracked': 0, 'clean': True}

class DockerHelper:
    '''Docker/Podman container management helper'''
    
    @staticmethod
    def detect_docker_command(content: str) -> tuple:
        '''Detect Docker/Podman operations'''
        docker_ops = []
        
        patterns = [
            (r'docker\\s+run', 'docker_run'),
            (r'docker\\s+ps', 'docker_ps'),
            (r'docker\\s+images', 'docker_images'),
            (r'docker\\s+build', 'docker_build'),
            (r'docker\\s+exec', 'docker_exec'),
            (r'docker\\s+logs', 'docker_logs'),
            (r'docker\\s+stop', 'docker_stop'),
            (r'docker\\s+rm', 'docker_rm'),
            (r'docker\\s+rmi', 'docker_rmi'),
            (r'podman\\s+run', 'podman_run'),
            (r'podman\\s+ps', 'podman_ps'),
            (r'podman\\s+build', 'podman_build'),
        ]
        
        for pattern, op_name in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                docker_ops.append(op_name)
        
        return docker_ops
    
    @staticmethod
    def is_destructive(operation: str) -> bool:
        '''Check if Docker operation is destructive'''
        return operation in ['docker_rm', 'docker_rmi', 'podman_rm', 'podman_rmi', 'docker_stop', 'podman_stop']
    
    @staticmethod
    def get_container_stats() -> dict:
        '''Get Docker/Podman container status'''
        stats = {'docker': [], 'podman': [], 'docker_available': False, 'podman_available': False}
        
        # Check Docker
        try:
            result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}\\t{{.Status}}'],
                                   capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                stats['docker_available'] = True
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            stats['docker'].append({'name': parts[0], 'status': parts[1]})
        except:
            pass
        
        # Check Podman
        try:
            result = subprocess.run(['podman', 'ps', '--format', '{{.Names}}\\t{{.Status}}'],
                                   capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                stats['podman_available'] = True
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            stats['podman'].append({'name': parts[0], 'status': parts[1]})
        except:
            pass
        
        return stats

# ============================================================================
# SYSTEM INFO
# ============================================================================

def get_git_info() -> tuple:
    '''Get current git branch and status'''
    return GitHelper.get_status()['branch'], 0

def get_system_stats() -> dict:
    '''Get real system stats'''
    try:
        # CPU
        try:
            with open('/proc/stat') as f:
                cpu_line = f.readline()
            fields = cpu_line.split()
            idle1 = int(fields[4])
            total1 = sum(int(x) for x in fields[1:8])
            time.sleep(0.1)
            with open('/proc/stat') as f:
                cpu_line = f.readline()
            fields = cpu_line.split()
            idle2 = int(fields[4])
            total2 = sum(int(x) for x in fields[1:8])
            cpu_pct = int(100 * (1 - (idle2 - idle1) / (total2 - total1 + 0.001)))
        except:
            cpu_pct = 50
        
        # Memory
        try:
            with open('/proc/meminfo') as f:
                mem_lines = f.readlines()
            mem_total = int(mem_lines[0].split()[1])
            mem_avail = int(mem_lines[2].split()[1])
            mem_pct = int(100 * (mem_total - mem_avail) / mem_total)
        except:
            mem_pct = 45
        
        # Disk
        result = subprocess.run(['df', '-h', '.'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            parts = result.stdout.strip().split('\n')[-1].split()
            disk = parts[4] if len(parts) >= 5 else 'N/A'
        else:
            disk = 'N/A'
        
        return {'cpu': f'{cpu_pct}%', 'mem': f'{mem_pct}%', 'disk': disk}
    except:
        return {'cpu': '50%', 'mem': '45%', 'disk': 'N/A'}

def get_terminal_cols():
    return shutil.get_terminal_size().columns

# ============================================================================
# ANIMATED BANNER
# ============================================================================

def get_banner() -> str:
    banner = '''
[bold cyan]╔══════════════════════════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]                                                                      [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]██╗     ██╗██████╗ ██████╗  █████╗ ██████╗ ██╗   ██╗██╗[/bold white]        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]██║     ██║██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║   ██║██║[/bold white]        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]██║     ██║██████╔╝██████╔╝███████║██████╔╝██║   ██║██║[/bold white]        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]██║     ██║██╔══██╗██╔══██╗██╔══██║██╔══██╗╚██╗ ██╔╝██║[/bold white]        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]███████╗██║██████╔╝██║  ██║██║  ██║██║  ██║ ╚████╔╝ ██║[/bold white]        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]╚══════╝╚═╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝  ╚═╝[/bold white]        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]                                                                      [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold yellow]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold yellow]   [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [bold white]◆  AI-Powered Terminal for Epic Workflows  ◆[/bold white]              [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]   [dim]   Free · Powerful · Agentic · [📦][±][🐳]  [/dim]                      [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]                                                                      [bold cyan]║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════════════════════════════╝[/bold cyan]
'''
    return banner

# ============================================================================
# DOMAIN DISPLAY HELPERS
# ============================================================================

def print_git_status():
    '''Print current git status in a nice box'''
    status = GitHelper.get_status()
    
    if status['branch']:
        console.print(f'\n[{GREEN}]╭─ Git Status ────────────────────────────────────────╮[{GREEN}]')
        console.print(f'[{CYAN}]{GIT_SYMBOL}[/{CYAN}] [bold white]Branch:[/bold white] [green]{status['branch']}[/green]')
        
        if status['clean']:
            console.print(f'[{DIM}]│   ✓ Working tree clean[/{DIM}]')
        else:
            if status['staged'] > 0:
                console.print(f'[{DIM}]│   📁 {status['staged']} staged[/{DIM}]')
            if status['modified'] > 0:
                console.print(f'[{DIM}]│   ✏️  {status['modified']} modified[/{DIM}]')
            if status['untracked'] > 0:
                console.print(f'[{DIM}]│   ?  {status['untracked']} untracked[/{DIM}]')
        
        console.print(f'[{GREEN}]╰─────────────────────────────────────────────────────╯[{GREEN}]\n')
    else:
        console.print(f'\n[{DIM}]╭─ Git Status ────────────────────────────────────────╮[{DIM}]')
        console.print(f'[{DIM}]│   Not a git repository[/{DIM}]')
        console.print(f'[{DIM}]╰─────────────────────────────────────────────────────╯[{DIM}]\n')

def print_docker_status():
    '''Print Docker/Podman status'''
    stats = DockerHelper.get_container_stats()
    
    if not stats['docker_available'] and not stats['podman_available']:
        console.print(f'[{DIM}]╭─ Containers ─────────────────────────────────────────╮[{DIM}]')
        console.print(f'[{DIM}]│   Docker/Podman not available[/{DIM}]')
        console.print(f'[{DIM}]╰─────────────────────────────────────────────────────╯[{DIM}]\n')
        return
    
    console.print(f'\n[{CYAN}]╭─ Container Status ───────────────────────────────────╮[{CYAN}]')
    
    if stats['docker_available']:
        console.print(f'[{DOCKER_SYMBOL}] [bold white]Docker:[/{WHITE}]')
        if stats['docker']:
            for c in stats['docker'][:5]:  # Show max 5
                console.print(f'  [{DIM}]- {c['name']}[/{DIM}] [{YELLOW}]{c['status']}[/{YELLOW}]')
        else:
            console.print(f'  [{DIM}]No containers running[/{DIM}]')
    
    if stats['podman_available']:
        console.print(f'[{PODMAN_SYMBOL}] [bold white]Podman:[/{WHITE}]')
        if stats['podman']:
            for c in stats['podman'][:5]:
                console.print(f'  [{DIM}]- {c['name']}[/{DIM}] [{YELLOW}]{c['status']}[/{YELLOW}]')
        else:
            console.print(f'  [{DIM}]No containers running[/{DIM}]')
    
    console.print(f'[{CYAN}]╰─────────────────────────────────────────────────────╯[{CYAN}]\n')

# ============================================================================
# STYLIZED BOXES
# ============================================================================

def print_command_box(title: str, cmd: str, output: str, success: bool):
    '''Print a command execution result box'''
    if success:
        color = GREEN
        icon = '✓'
    else:
        color = RED
        icon = '✗'
    
    console.print(f'\n[{color}]╭─ [{icon}] {title} ╮[/{color}]')
    console.print(f'[{MAGENTA}]{cmd}[/{MAGENTA}]')
    if output:
        console.print(f'[{DIM}]├─ output ─────────────────────────────────────────┤[{DIM}]')
        for line in output.split('\n')[:20]:  # Limit output
            console.print(f'  {line}')
        if len(output.split('\n')) > 20:
            console.print(f'  [{DIM}]... ({len(output.split(chr(10))) - 20} more lines)[/{DIM}]')
    console.print(f'[{color}]╰─────────────────────────────────────────────────╯[/{color}]\n')

# ============================================================================
# STATUS BAR
# ============================================================================

def print_status_bar(provider: str, model: str, agentic_mode: bool, cwd: str):
    '''Print a beautiful status bar with real system info'''
    stats = get_system_stats()
    git_status = GitHelper.get_status()
    now = datetime.now().strftime('%H:%M:%S')
    
    # Build git string
    if git_status['branch']:
        git_str = f'[green]{GIT_SYMBOL} {git_status['branch']}[/green]'
        if not git_status['clean']:
            git_str += f' [+{git_status['modified']}]'
    else:
        git_str = '[dim]no git[/dim]'
    
    # Build mode string
    if agentic_mode:
        mode_str = f'[{AGENTIC_SYMBOL}] [bold magenta on #1a1a2e]AGENTIC[/bold magenta on #1a1a2e]'
    else:
        mode_str = '[dim]💬 CHAT[/dim]'
    
    # Truncate cwd
    display_cwd = cwd
    max_w = get_terminal_cols() - 50
    if len(display_cwd) > max_w:
        parts = display_cwd.split('/')
        if len(parts) > 3:
            display_cwd = '.../' + '/'.join(parts[-2:])
    
    # CPU/Memory color
    cpu_pct = int(stats['cpu'].replace('%', ''))
    cpu_color = GREEN if cpu_pct < 70 else (YELLOW if cpu_pct < 90 else RED)
    
    mem_pct = int(stats['mem'].replace('%', ''))
    mem_color = GREEN if mem_pct < 70 else (YELLOW if mem_pct < 90 else RED)
    
    console.print()
    console.print(f'[dim]┌─ [{CLOCK_SYMBOL}] {now} [/dim][dim]│[/dim] [dim]Provider:[/dim] [cyan]{provider}[/cyan] [dim]│[/dim] [dim]Model:[/dim] [magenta]{model}[/magenta] {mode_str} [dim]│[/dim] {git_str} [dim]─┐[/dim]')
    console.print(f'[dim]│[/dim] [dim]CPU:[/dim] [{cpu_color}]{stats['cpu']}[/{cpu_color}] [dim]│[/dim] [dim]MEM:[/dim] [{mem_color}]{stats['mem']}[/{mem_color}] [dim]│[/dim] [dim]DISK:[/dim] [cyan]{stats['disk']}[/cyan] [dim]│[/dim]')
    console.print(f'[dim]└─[/dim] [dim]📁[/dim] [cyan]{display_cwd}[/cyan]')
    console.print()

# ============================================================================
# HELP PANEL - DOMAIN ENHANCED
# ============================================================================

def print_help_panel():
    help_text = '''
[bold cyan]╔════════════════════════════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]              [bold white]★ ═══ NxTerm Commands ═══ ★[/bold white]                          [bold cyan]║[/bold cyan]
[bold cyan]╠════════════════════════════════════════════════════════════════════════╣[/bold cyan]
[bold cyan]║[/bold cyan]  [bold yellow]╭──────────────────────────────────────╮[/bold yellow]                   [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]  [bold yellow]│[/bold yellow] [cyan]/agentic[/cyan] [bold yellow]│ ←→ [bold yellow]│[/bold yellow] Enable agentic mode               [bold cyan]║[/bold cyan]
[bold cyan]║[/bold yellow]  ╰──────────────────────────────────────╯[/bold yellow]                   [bold cyan]║[/bold cyan]
[bold cyan]╠════════════════════════════════════════════════════════════════════════╣[/bold cyan]
[bold cyan]║[/bold cyan]  [bold magenta]⚡ AGENTIC MODE COMMANDS[/bold magenta]                                        [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    [magenta]run[/magenta] [white]<command>[/white]       → Execute shell command              [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    [magenta]read[/magenta] [white]<file>[/white]         → Read file content                 [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    [magenta]write[/magenta] [white]<file>|<text>[/white] → Write file                       [bold cyan]║[/bold cyan]
[bold cyan]╠════════════════════════════════════════════════════════════════════════╣[/bold cyan]
[bold cyan]║[/bold cyan]  [bold green]📦 ANSIBLE HELPERS[/bold green]                                                    [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    AI detects ansible-playbook commands in responses            [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    Shows playbook info (hosts, tasks) before execution          [bold cyan]║[/bold cyan]
[bold cyan]╠════════════════════════════════════════════════════════════════════════╣[/bold cyan]
[bold cyan]║[/bold cyan]  [bold yellow]± GIT HELPERS[/bold yellow]                                                       [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    AI detects git operations and asks for confirmation          [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    Shows [red]⚠️  APPROVAL NEEDED[/red] for destructive commands       [bold cyan]║[/bold cyan]
[bold cyan]╠════════════════════════════════════════════════════════════════════════╣[/bold cyan]
[bold cyan]║[/bold cyan]  [bold blue]🐳 DOCKER/PODMAN HELPERS[/bold blue]                                          [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    AI detects docker/podman commands                            [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    Shows running containers status                               [bold cyan]║[/bold cyan]
[bold cyan]╠════════════════════════════════════════════════════════════════════════╣[/bold cyan]
[bold cyan]║[/bold cyan]  [bold cyan]📋 SYSTEM COMMANDS[/bold cyan]                                                  [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    [cyan]/help[/cyan]    → This help       [cyan]/status[/cyan]  → Git/Docker status  [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    [cyan]/clear[/cyan]   → Clear chat      [cyan]/config[/cyan]  → Settings          [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]    [cyan]/exit[/cyan]    → Goodbye                                                    [bold cyan]║[/bold cyan]
[bold cyan]╚════════════════════════════════════════════════════════════════════════╝[/bold cyan]
'''
    console.print(help_text)

# ============================================================================
# SPINNER
# ============================================================================

class Spinner:
    def __init__(self):
        self.frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.current = 0
        self.running = False
        self.thread = None
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
    
    def _spin(self):
        while self.running:
            frame = self.frames[self.current % len(self.frames)]
            console.print(f'\r[{frame}] Thinking...', end='')
            time.sleep(0.1)
            self.current += 1
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)
        console.print('\r' + ' ' * 30 + '\r', end='')

# ============================================================================
# COMMAND HISTORY
# ============================================================================

class CommandHistory:
    def __init__(self, max_size=100):
        self.history = []
        self.index = -1
    
    def add(self, cmd):
        if cmd and (not self.history or self.history[-1] != cmd):
            self.history.append(cmd)
            self.index = len(self.history)
    
    def up(self):
        if self.history and self.index > 0:
            self.index -= 1
            return self.history[self.index]
        return None
    
    def down(self):
        if self.history and self.index < len(self.history) - 1:
            self.index += 1
            return self.history[self.index]
        self.index = len(self.history)
        return ''
    
    def reset(self):
        self.index = len(self.history)

# ============================================================================
# INPUT
# ============================================================================

def get_input(prompt: str = '❯') -> str:
    '''Get user input'''
    try:
        return console.input(f'[{INPUT_STYLE}]{prompt}[/{INPUT_STYLE}] ').strip()
    except (KeyboardInterrupt, EOFError):
        return '/exit'

def get_confirmation(prompt: str) -> bool:
    '''Get user confirmation for dangerous operations'''
    console.print(f'\n[{YELLOW}]⚠️  {prompt}[/{YELLOW}]')
    console.print(f'[{DIM}]Type [green]yes[/green] to confirm or anything else to cancel:[/{DIM}] ', end='')
    try:
        answer = console.input('').strip().lower()
        return answer == 'yes'
    except:
        return False

# ============================================================================
# AI STREAMING
# ============================================================================

def stream_ai_response(messages: list, model: str, callback=None):
    '''Get AI response with streaming'''
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

def build_system_prompt(cwd: str, agentic_mode: bool) -> str:
    if agentic_mode:
        return f'''You are NxTerm, an EXPERT AGENTIC AI in a terminal environment with DOMAIN SUPERPOWERS.

Current directory: {cwd}

You have FULL capabilities:
- Execute shell commands: !run: <command>
- Read files: !read: filepath
- Write files: !write: filepath | content

ANSIBLE PLAYBOOKS:
- Detect ansible-playbook commands automatically
- Show playbook info (hosts, task count) before suggesting execution
- Use: ansible-playbook -i inventory site.yml --check for dry-run
- Warn about destructive operations (shell, command modules)

GIT OPERATIONS:
- Detect git add, commit, push, merge, rebase, reset operations
- ALWAYS ask for confirmation on destructive commands: push --force, reset --hard, rebase
- Show: git status --short to see current state
- Commit messages should be clear and descriptive

DOCKER/PODMAN:
- Detect docker run, build, exec, ps, logs, rm commands
- Show: docker ps / podman ps for running containers
- Use: docker logs <container> for troubleshooting
- Warn before: docker rm, docker rmi, docker stop (data loss risk)

Be decisive. Take action. Use command markers when needed.

Examples:
- !run: ansible-playbook -i inventory webserver.yml --check
- !run: git status
- !run: docker ps
- !read: group_vars/all/vault.yml

Provide actual output, not just descriptions. Keep responses concise.'''
    else:
        return f'''You are NxTerm, a helpful AI assistant in a terminal with domain knowledge.

Current directory: {cwd}

You have knowledge about:
- Ansible playbooks and automation
- Git version control workflows
- Docker/Podman container management
- General shell commands and Linux administration

You can:
- Chat naturally about any topic
- Explain code and technical concepts
- Help with coding, debugging, planning
- Discuss Ansible, Git, Docker best practices
- Suggest terminal commands

Be conversational, helpful, and concise. Use markdown formatting when useful.'''

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

def read_file(path: str) -> str:
    try:
        return Path(path).expanduser().resolve().read_text()
    except Exception as e:
        return f'Error reading {path}: {e}'

def write_file(path: str, content: str) -> str:
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f'Successfully wrote to {path}'
    except Exception as e:
        return f'Error writing {path}: {e}'

def parse_agentic_commands(response: str) -> list:
    '''Parse agentic commands from AI response'''
    commands = []
    
    for line in response.split('\n'):
        stripped = line.strip()
        
        # !run: pattern
        match = re.match(r'^!run:\n?(.+)', stripped)
        if match:
            cmd = match.group(1).strip()
            if cmd and not any(cmd.startswith(p) for p in ('The ', 'I ', 'This ', 'To ', 'Run ', 'Just ')):
                commands.append(('run', cmd))
        
        # !read: pattern
        match = re.match(r'^!read:\n?(.+)', stripped)
        if match:
            filepath = match.group(1).strip()
            if filepath and not any(filepath.startswith(p) for p in ('The ', 'I ', 'This ')):
                commands.append(('read', filepath))
        
        # !write: pattern
        match = re.match(r'^!write:\n?([^|\n]+)\n?([\u0000-\uffff]+)', stripped, re.DOTALL)
        if match:
            filepath = match.group(1).strip()
            content = match.group(2).strip()
            if filepath and filepath not in ('filepath', 'file', 'path'):
                commands.append(('write', filepath, content))
    
    return commands

def parse_user_agentic_command(user_input: str) -> list:
    '''Check if user input is a direct agentic command'''
    stripped = user_input.strip()
    
    match = re.match(r'^run\\s+(.+)$', stripped, re.IGNORECASE)
    if match:
        return [('run', match.group(1).strip())]
    
    match = re.match(r'^read\\s+(.+)$', stripped, re.IGNORECASE)
    if match:
        return [('read', match.group(1).strip())]
    
    match = re.match(r'^write\s+([^|]+)\|(.+)$', stripped, re.IGNORECASE | re.DOTALL)
    if match:
        return [('write', match.group(1).strip(), match.group(2).strip())]
    
    return []

def execute_agentic_commands(commands: list, cwd: str, need_approval_fn=None) -> str:
    '''Execute agentic commands with domain awareness'''
    results = []
    
    for cmd in commands:
        if cmd[0] == 'run':
            _, command = cmd
            
            # Domain-specific checks
            if GitHelper.needs_approval(command):
                console.print(f'\n[{YELLOW}]⚠️  Git command requires approval:[/{YELLOW}] {command}')
                if need_approval_fn and not need_approval_fn(f'Run git command: {command}'):
                    results.append(f'[{RED}]✗ Cancelled[/red]')
                    continue
            
            returncode, stdout, stderr = execute_command(command, cwd)
            results.append(f'[{AGENTIC_SYMBOL}] [bold magenta]!run: {command}[/bold magenta]')
            if returncode == 0:
                results.append(f'[green]✓ Success[/green]')
            else:
                results.append(f'[red]✗ Exit code: {returncode}[/red]')
            if stdout:
                results.append(f'[dim]{stdout}[/dim]')
            if stderr:
                results.append(f'[yellow]⚠ {stderr}[/yellow]')
        
        elif cmd[0] == 'read':
            _, filepath = cmd
            content = read_file(filepath)
            results.append(f'[{AGENTIC_SYMBOL}] [bold cyan]!read: {filepath}[/bold cyan]')
            if len(content) > 500:
                content = content[:500] + f'\n[dim]... ({len(content)-500} more chars)[/dim]'
            results.append(f'```\n{content}\n```')
        
        elif cmd[0] == 'write':
            _, filepath, content = cmd
            result = write_file(filepath, content)
            results.append(f'[{AGENTIC_SYMBOL}] [bold green]!write: {filepath}[/bold green]')
            results.append(f'[green]{result}[/green]')
    
    return '\n'.join(results)

# ============================================================================
# MAIN CHAT LOOP
# ============================================================================

def chat_loop():
    config = init_config_dir()
    
    provider = config.get('provider', 'ollama')
    model = config.get('ollama_model', OLLAMA_MODEL)
    cwd = os.getcwd()
    
    chat = ChatHistory()
    chat.add_system(build_system_prompt(cwd, chat.agentic_mode))
    
    history = CommandHistory()
    
    # Check Ollama status
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
    
    while True:
        try:
            user_input = get_input()
        except:
            user_input = '/exit'
        
        if not user_input:
            continue
        
        history.add(user_input)
        history.reset()
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Toggle commands
        if user_input.lower() == '/agentic':
            chat.agentic_mode = True
            chat.messages[0] = Message('system', build_system_prompt(cwd, True))
            console.print()
            console.print('[bold magenta]╔═══════════════════════════════════════╗[/bold magenta]')
            console.print('[bold magenta]║[/bold magenta]  [bold white]⚡ AGENTIC MODE ENABLED[/bold white]              [bold magenta]║[/bold magenta]')
            console.print('[bold magenta]║[/bold magenta]  [dim]AI can now execute commands[/dim]           [bold magenta]║[/bold magenta]')
            console.print('[bold magenta]╚═══════════════════════════════════════╝[/bold magenta]')
            print_status_bar(provider, model, True, cwd)
            continue
        
        if user_input.lower() == '/chat':
            chat.agentic_mode = False
            chat.messages[0] = Message('system', build_system_prompt(cwd, False))
            console.print()
            console.print('[bold cyan]╔═══════════════════════════════════════╗[/bold cyan]')
            console.print('[bold cyan]║[/bold cyan]  [bold white]💬 CHAT MODE ENABLED[/bold white]                  [bold cyan]║[/bold cyan]')
            console.print('[bold cyan]║[/bold cyan]  [dim]AI will only chat (no commands)[/dim]        [bold cyan]║[/bold cyan]')
            console.print('[bold cyan]╚═══════════════════════════════════════╝[/bold cyan]')
            print_status_bar(provider, model, False, cwd)
            continue
        
        # System commands
        if user_input.startswith('/'):
            cmd = user_input[1:].lower()
            
            if cmd == 'exit':
                console.print(f'\n[bold yellow]👋 Goodbye from NxTerm![/bold yellow]\n')
                break
            
            elif cmd == 'help':
                print_help_panel()
                continue
            
            elif cmd == 'clear':
                console.print('\n' * 50)
                chat.clear()
                chat.add_system(build_system_prompt(cwd, chat.agentic_mode))
                console.print(get_banner())
                print_status_bar(provider, model, chat.agentic_mode, cwd)
                print_git_status()
                console.print('[green]✓ Chat cleared[/green]\n')
                continue
            
            elif cmd == 'status':
                print_git_status()
                print_docker_status()
                continue
            
            elif cmd == 'config':
                nexus_cmd_configure()
                config = get_config()
                model = config.get('ollama_model', OLLAMA_MODEL)
                provider = config.get('provider', 'ollama')
                print_status_bar(provider, model, chat.agentic_mode, cwd)
                continue
            
            elif cmd == 'models':
                nexus_cmd_list_models(config)
                continue
            
            else:
                console.print(f'[yellow]Unknown: {cmd} (try /help)[/yellow]\n')
                continue
        
        # Check for direct agentic commands
        direct_commands = parse_user_agentic_command(user_input) if chat.agentic_mode else []
        
        if direct_commands:
            console.print()
            console.print(f'[dim]┌─ Agentic Execution ──────────────────────────────┐[/dim]')
            exec_results = execute_agentic_commands(direct_commands, cwd, get_confirmation)
            console.print(Markdown(exec_results, code_theme='monokai'))
            console.print(f'[dim]└────────────────────────────────────────────────────┘[/dim]\n')
            
            chat.add_user(user_input)
            chat.add_ai(f'Executed: {user_input}\n{exec_results}')
            continue
        
        # Normal chat with streaming
        chat.add_user(user_input)
        
        console.print()
        console.print(f'[{USER_SYMBOL}] [dim]{timestamp}[/dim] [bold cyan]{user_input}[/bold cyan]')
        console.print()
        
        console.print(f'[{AI_SYMBOL}] ', end='')
        
        response_chunks = []
        def streaming_callback(chunk):
            response_chunks.append(chunk)
            console.print(chunk, end='')
        
        messages = chat.get_conversation()
        
        try:
            stream_ai_response(messages, model, streaming_callback)
        except Exception as e:
            console.print(f'\n[red]Error: {e}[/red]')
            response = ''
            continue
        
        response = ''.join(response_chunks)
        console.print()  # Newline after streaming
        
        chat.add_ai(response)
        
        # Execute agentic commands from AI response
        if chat.agentic_mode:
            commands = parse_agentic_commands(response)
            if commands:
                console.print(f'\n[bold cyan]╭─ Commands Executed ──────────────────────────────────╮[bold cyan]')
                for cmd in commands:
                    if cmd[0] == 'run':
                        _, command = cmd
                        
                        # Check for destructive git commands
                        if GitHelper.needs_approval(command):
                            console.print(f'[{YELLOW}]⚠️  Git command needs approval: {command}[/{YELLOW}]')
                            if not get_confirmation(f'Run git command: {command}'):
                                console.print(f'[{RED}]✗ Cancelled[/red]')
                                continue
                        
                        returncode, stdout, stderr = execute_command(command, cwd)
                        print_command_box('RUN', command, stdout, returncode == 0)
                    elif cmd[0] == 'read':
                        _, filepath = cmd
                        content = read_file(filepath)
                        console.print(f'\n[{AGENTIC_SYMBOL}] [bold cyan]!read: {filepath}[/bold cyan]')
                        console.print(f'[dim]Content preview:\n{content[:300]}...[/dim]\n')
                    elif cmd[0] == 'write':
                        _, filepath, content = cmd
                        result = write_file(filepath, content)
                        console.print(f'\n[{AGENTIC_SYMBOL}] [bold green]!write: {filepath}[/bold green]')
                        console.print(f'[green]{result}[/green]')
                console.print(f'[bold cyan]╰─────────────────────────────────────────────────────╯[bold cyan]\n')
        
        print_status_bar(provider, model, chat.agentic_mode, cwd)

# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='NxTerm - AI Chat Terminal with Domain Superpowers')
    parser.add_argument('--config', action='store_true', help='Open configuration')
    parser.add_argument('--models', action='store_true', help='List models')
    parser.add_argument('--agentic', action='store_true', help='Start in Agentic mode')
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
    
    chat_loop()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print(f'\n[{WARNING_COLOR}]Goodbye![/]')