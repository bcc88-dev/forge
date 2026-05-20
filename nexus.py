#!/usr/bin/env python3
'''
╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗
║ ║╠═╝║╣ ║╣ ╠═╗║╣ ║ ╦║╣ ║ ║║ ║╚═╗╚═╗
╚═╝╩  ╚═╝╚═╝╩ ╩╚═╝╚═╝╚═╝╚═╝╚═╝╚═╝
Nexus. The hub of your code universe.
Free. Powerful. No ads. Local + Cloud.
'''

import os
import sys
import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Literal

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.table import Table
    from rich.align import Align
    from rich.style import Style
except ImportError:
    os.system('pip install rich')
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.table import Table
    from rich.align import Align
    from rich.style import Style

console = Console()

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG_DIR = Path.home() / '.nexus'
CONFIG_FILE = CONFIG_DIR / 'config.json'
MEMORY_FILE = CONFIG_DIR / 'memory.json'

OLLAMA_BASE_URL = 'http://localhost:11434'
OLLAMA_MODEL = 'nemotron-3-super:cloud'
OLLAMA_FALLBACK_MODELS = ['llama3.2:latest', 'mistral:latest', 'codellama:latest']

# Free OpenRouter models - completely free tier
FREE_OPENROUTER_MODELS = [
    ('anthropic/claude-3.5-haiku', 'Claude 3.5 Haiku', 'Fast, capable reasoning'),
    ('deepseek/deepseek-chat-v3', 'DeepSeek V3', 'Excellent coding'),
    ('google/gemini-2.0-flash-exp', 'Gemini 2.0 Flash', 'Ultra fast, huge context'),
    ('mistralai/mistral-nemo', 'Mistral Nemo', 'Balanced performance'),
    ('openai/gpt-4o-mini', 'GPT-4o Mini', 'Reliable, good at coding'),
    ('meta-llama/llama-3.1-8b-instruct', 'Llama 3.1 8B', 'Open source favorite'),
    ('qwen/qwen-2.5-7b-instruct', 'Qwen 2.5 7B', 'Great multilingual'),
    ('databricks/dbrx-instruct', 'DBRX Instruct', 'Fast mixture-of-experts'),
]

DEFAULT_PROVIDER = 'ollama'
DEFAULT_MODEL = OLLAMA_MODEL

# Colors
BRAND_COLOR = 'cyan'
ACCENT_COLOR = 'green'
WARNING_COLOR = 'yellow'
ERROR_COLOR = 'red'

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def init_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not CONFIG_FILE.exists():
        default_config = {
            'provider': DEFAULT_PROVIDER,
            'ollama_model': OLLAMA_MODEL,
            'openrouter_model': FREE_OPENROUTER_MODELS[0][0],
            'ollama_base_url': OLLAMA_BASE_URL,
            'temperature': 0.7,
            'max_tokens': 16000,
            'stream': True,
            'auto_apply': False,
            'show_diff': True,
        }
        save_config(default_config)
    return load_config()

def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text())
    except:
        return {}

def save_config(config: dict):
    CONFIG_FILE.write_text(json.dumps(config, indent=2))

def load_memory() -> dict:
    try:
        return json.loads(MEMORY_FILE.read_text())
    except:
        return {'history': [], 'project_context': {}, 'last_session': None}

def save_memory(memory: dict):
    MEMORY_FILE.write_text(json.dumps(memory, indent=2))

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# ============================================================================
# OLLAMA FUNCTIONS
# ============================================================================

def check_ollama(base_url: str = OLLAMA_BASE_URL) -> tuple[bool, list]:
    try:
        r = requests.get(f'{base_url}/api/tags', timeout=5)
        if r.status_code == 200:
            models = r.json().get('models', [])
            model_names = [m.get('name', str(m)) for m in models]
            return True, model_names
        return False, []
    except:
        return False, []

def call_ollama(
    messages: list,
    model: str,
    base_url: str = OLLAMA_BASE_URL,
    stream_callback: Optional[Callable[[str], None]] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096
) -> str:
    try:
        payload = {
            'model': model,
            'messages': messages,
            'stream': True,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens
            }
        }
        
        r = requests.post(f'{base_url}/api/chat', json=payload, stream=True, timeout=180)
        
        if r.status_code != 200:
            return f'Error: Ollama returned status {r.status_code}'
        
        full_response = []
        for line in r.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    if 'message' in data and 'content' in data['message']:
                        chunk = data['message']['content']
                        full_response.append(chunk)
                        if stream_callback:
                            stream_callback(chunk)
                except json.JSONDecodeError:
                    pass
        
        return ''.join(full_response)
        
    except requests.exceptions.ConnectionError:
        return f'Error: Cannot connect to Ollama at {base_url}. Is it running?\nTip: Start Ollama with: ollama serve'
    except Exception as e:
        return f'Error: {e}'

# ============================================================================
# OPENROUTER FUNCTIONS
# ============================================================================

def get_openrouter_key() -> Optional[str]:
    config = load_config()
    
    # Check config first
    if config.get('openrouter_key'):
        return config['openrouter_key']
    
    # Check environment
    key = os.getenv('OPENROUTER_API_KEY')
    if key:
        return key
    
    # Prompt user
    console.print(f'\n[bold {WARNING_COLOR}]🔑 OpenRouter API key required for cloud models[/bold {WARNING_COLOR}]')
    console.print(f'[dim]Get free key at → [/dim][link=https://openrouter.ai/keys]https://openrouter.ai/keys[/link]')
    key = console.input(f'\nPaste your key (or press Enter to skip): ').strip()
    
    if key:
        config['openrouter_key'] = key
        save_config(config)
        return key
    
    return None

def call_openrouter(
    messages: list,
    model: str,
    stream_callback: Optional[Callable[[str], None]] = None,
    temperature: float = 0.7,
    max_tokens: int = 16000
) -> str:
    key = get_openrouter_key()
    if not key:
        return 'Error: No OpenRouter API key. Use /config to set one.'
    
    try:
        payload = {
            'model': model,
            'messages': messages,
            'stream': True,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        r = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json',
                'HTTP-Referer': 'https://nexus.local',
                'X-Title': 'Nexus - Free Coding Agent'
            },
            json=payload,
            stream=True,
            timeout=180
        )
        
        if r.status_code != 200:
            return f'Error: OpenRouter returned {r.status_code}: {r.text}'
        
        full_response = []
        for line in r.iter_lines():
            if line:
                if line.startswith(b'data: '):
                    data = line[6:]
                    if data == b'[DONE]':
                        break
                    try:
                        parsed = json.loads(data)
                        if 'choices' in parsed:
                            delta = parsed['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_response.append(content)
                                if stream_callback:
                                    stream_callback(content)
                    except json.JSONDecodeError:
                        pass
        
        return ''.join(full_response)
        
    except Exception as e:
        return f'Error: {e}'

# ============================================================================
# UNIFIED AI COMPLETION
# ============================================================================

def ai_complete(
    messages: list,
    provider: str,
    model: str,
    stream_callback: Optional[Callable[[str], None]] = None
) -> str:
    config = load_config()
    temperature = config.get('temperature', 0.7)
    max_tokens = config.get('max_tokens', 16000) if provider != 'ollama' else 4096

    if provider == 'ollama':
        return call_ollama(
            messages, model,
            config.get('ollama_base_url', OLLAMA_BASE_URL),
            stream_callback,
            temperature,
            max_tokens
        )
    else:
        return call_openrouter(
            messages, model,
            stream_callback,
            temperature,
            max_tokens
        )


def ai_complete_with_fallback(
    messages: list,
    provider: str,
    model: str,
    stream_callback: Optional[Callable[[str], None]] = None
) -> str:
    """Call AI with automatic fallback to other cloud providers on failure.
    
    Single fallback attempt — tries one lower-cost provider then gives up.
    Avoids burning through rate limits by not chaining through all candidates.
    """
    # Try primary
    response = ai_complete(messages, provider, model, stream_callback)
    if not response.startswith('Error:'):
        return response

    # Primary failed — try ONE fallback from hardcoded cloud-first order
    console.print(f'[bold yellow]\u26a0\ufe0f  Primary provider {provider}/{model} failed — trying fallback...[/bold yellow]')

    # Hardcoded cloud fallback order (free/cheap first, skip local Ollama)
    CLOUD_FALLBACKS = [
        ('openrouter', 'qwen/qwen-2.5-7b-instruct', 2),
        ('openrouter', 'meta-llama/llama-3.1-8b-instruct', 2),
        ('openrouter', 'deepseek/deepseek-chat-v3', 3),
        ('openrouter', 'google/gemini-2.0-flash-exp', 4),
        ('openrouter', 'anthropic/claude-3.5-haiku', 5),
        ('openrouter', 'mistralai/mistral-nemo', 3),
        ('openrouter', 'openai/gpt-4o-mini', 2),
        ('openrouter', 'databricks/dbrx-instruct', 3),
    ]

    for fb_provider, fb_model, fb_cost in CLOUD_FALLBACKS:
        if fb_provider == provider and fb_model == model:
            continue  # Already tried primary
        console.print(f'  [dim]\u21b3 trying {fb_provider}/{fb_model}...[/dim]')
        fb_response = ai_complete(messages, fb_provider, fb_model, stream_callback)
        if not fb_response.startswith('Error:'):
            console.print(f'  [green]\u2713 Fallback succeeded!\u2713[/green]')
            return fb_response
        console.print(f'  [red]✗ {fb_provider}/{fb_model} failed — giving up[/red]')
        break  # Only try ONE fallback, then give up (rate-limit conservative)

    return response

# ============================================================================
# PROJECT CONTEXT
# ============================================================================

def load_project_context(path: Path = Path('.')) -> dict:
    memory = load_memory()
    project_key = str(path.absolute())
    project_data = memory.get('project_context', {}).get(project_key, {})
    
    # Scan files
    files = []
    gitignore_patterns = {'.git', '__pycache__', '.venv', 'node_modules', '.buff', '.nexus', 'venv', '.env'}
    
    try:
        for p in path.rglob('*'):
            if p.is_file() and not p.is_symlink():
                if any(ign in p.parts for ign in gitignore_patterns):
                    continue
                if any(x.startswith('.') and x not in ['.buff', '.nexus', '.gitignore'] for x in p.parts):
                    continue
                try:
                    if p.stat().st_size > 100000:  # Skip files > 100KB
                        continue
                except:
                    pass
                if len(files) >= 150:
                    break
                files.append(str(p))
    except PermissionError:
        pass
    
    return {
        'files': sorted(files)[:150],
        'summary': project_data.get('summary', ''),
        'history': project_data.get('history', [])[-5:]
    }

def build_system_prompt(context: dict, provider: str, model: str) -> str:
    files_list = '\n'.join(context.get('files', [])) or '(empty directory)'
    summary = context.get('summary', 'New project')
    history = context.get('history', [])
    
    history_text = ''
    if history:
        history_text = '\n\nRecent history:\n' + '\n'.join([f'- {h}' for h in history])
    
    provider_note = f'[Currently using: {provider} / {model}]'
    
    return f'''You are Nexus, an expert coding assistant. The hub of your code universe.

You help users write, modify, and understand code:
- Write new code and files
- Edit existing files using code blocks with filepath markers
- Explain code concepts clearly
- Debug issues and suggest improvements
- Refactor and optimize code

Current Project:
Directory: {Path.cwd()}
Files:
{files_list}

Project Summary: {summary}
{history_text}

Guidelines:
- Be concise and actionable
- When creating/modifying files, use this format EXACTLY:
```filepath: relative/path.py
code content here
```
- Never modify nexus.py or config files
- Focus on working, well-designed code
- Use comments to explain non-obvious code
- Follow existing project conventions'''

# ============================================================================
# UI FUNCTIONS
# ============================================================================

def print_banner():
    console.print()
    console.print(f'[bold cyan]╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗╔═╗[/bold cyan]')
    console.print(f'[bold cyan]║ ║╠═╝║╣ ║╣ ╠═╗║╣ ║ ╦║╣ ║ ║║ ║╚═╗╚═╗[/bold cyan]')
    console.print(f'[bold cyan]╚═╝╩  ╚═╝╚═╝╩ ╩╚═╝╚═╝╚═╝╚═╝╚═╝[/bold cyan]')
    console.print(f'[dim]The hub of your code universe.[/dim]')
    console.print(f'[dim]Free. Powerful. No ads. Local + Cloud.[/dim]')
    console.print()

def print_status(provider: str, model: str, config: dict):
    provider_color = ACCENT_COLOR if provider == 'ollama' else 'blue'
    console.print(f'\n[dim]Provider:[/dim] [{provider_color}]{provider}[/{provider_color}]  [dim]Model:[/dim] [cyan]{model}[/cyan]')
    if provider == 'ollama':
        ollama_url = config.get('ollama_base_url', OLLAMA_BASE_URL)
        console.print(f'[dim]Ollama:[/dim] {ollama_url}')

def cmd_list_models(config: dict):
    console.print(f'\n[bold cyan]📋 Available Models[/bold cyan]\n')
    
    # Ollama section
    console.print('[bold]Local - Ollama:[/bold]')
    available, models = check_ollama(config.get('ollama_base_url', OLLAMA_BASE_URL))
    if available:
        for model in models:
            console.print(f'  [green]•[/green] [cyan]{model}[/cyan]')
    else:
        console.print('  [dim]Ollama not running. Start with: ollama serve[/dim]')
    console.print()
    
    # OpenRouter free section
    console.print('[bold]Cloud - OpenRouter (Free Tier):[/bold]')
    table = Table(show_header=False, box=None, padding=(0, 2))
    for model_id, name, desc in FREE_OPENROUTER_MODELS:
        table.add_row(f'[green]•[/green] [bold]{name}[/bold]', f'[dim]{desc}[/dim]')
        table.add_row(f'    [dim]{model_id}[/dim]', '')
    console.print(table)
    console.print()

def cmd_configure():
    config = load_config()
    ollama_available, ollama_models = check_ollama(config.get('ollama_base_url', OLLAMA_BASE_URL))
    
    console.print(f'\n[bold cyan]⚙️  Configuration[/bold cyan]\n')
    
    # Provider selection
    console.print('[bold]Select provider:[/bold]')
    console.print('[1] [cyan]Ollama[/cyan] (local, free, private)')
    console.print('[2] [blue]OpenRouter[/blue] (cloud, free tier)')
    
    current_provider = config.get('provider', DEFAULT_PROVIDER)
    choice = console.input(f'\nChoice (1/2) [{1 if current_provider == 'ollama' else 2}]: ').strip() or ('1' if current_provider == 'ollama' else '2')
    
    if choice == '2':
        provider = 'openrouter'
        console.print('\n[bold]Select OpenRouter model:[/bold]')
        for i, (model_id, name, desc) in enumerate(FREE_OPENROUTER_MODELS, 1):
            console.print(f'  [{i}] [bold]{name}[/bold] - {desc}')
            console.print(f'      [dim]{model_id}[/dim]')
        
        sel = console.input(f'\nChoice [1-{len(FREE_OPENROUTER_MODELS)}]: ').strip() or '1'
        try:
            idx = max(0, min(int(sel) - 1, len(FREE_OPENROUTER_MODELS) - 1))
            model = FREE_OPENROUTER_MODELS[idx][0]
        except:
            model = FREE_OPENROUTER_MODELS[0][0]
    else:
        provider = 'ollama'
        if ollama_available and ollama_models:
            console.print('\n[bold]Select Ollama model:[/bold]')
            for i, model in enumerate(ollama_models, 1):
                console.print(f'  [{i}] [cyan]{model}[/cyan]')
            
            sel = console.input(f'\nChoice [1-{len(ollama_models)}]: ').strip() or '1'
            try:
                idx = max(0, min(int(sel) - 1, len(ollama_models) - 1))
                model = ollama_models[idx]
            except:
                model = ollama_models[0]
        elif ollama_models:
            console.print(f'\n[dim]Ollama available with {len(ollama_models)} models[/dim]')
            model = config.get('ollama_model', OLLAMA_MODEL)
        else:
            console.print(f'\n[bold {WARNING_COLOR}]⚠️  No Ollama models found[/bold {WARNING_COLOR}]')
            console.print('[dim]Download a model first:[/dim] ollama pull llama3.2')
            model = OLLAMA_MODEL
    
    config['provider'] = provider
    config[f'{provider}_model'] = model
    
    # Temperature
    cur_temp = config.get('temperature', 0.7)
    temp = console.input(f'\nTemperature (0.0-2.0) [{cur_temp}]: ').strip()
    if temp:
        try:
            config['temperature'] = max(0.0, min(2.0, float(temp)))
        except ValueError:
            console.print(f'[yellow]Invalid temperature, keeping {cur_temp}[/yellow]')
    
    # Streaming
    cur_stream = config.get('stream', True)
    stream_q = console.input(f'Stream responses (y/n) [{cur_stream}]: ').strip().lower()
    if stream_q in ['y', 'yes']:
        config['stream'] = True
    elif stream_q in ['n', 'no']:
        config['stream'] = False
    
    # Auto-apply
    cur_auto = config.get('auto_apply', False)
    auto_q = console.input(f'Auto-apply changes (y/n) [{cur_auto}]: ').strip().lower()
    if auto_q in ['y', 'yes']:
        config['auto_apply'] = True
    elif auto_q in ['n', 'no']:
        config['auto_apply'] = False
    
    save_config(config)
    console.print(f'\n[green]✅ Configuration saved![/green]')

def cmd_set_summary():
    memory = load_memory()
    project_key = str(Path.cwd().absolute())
    
    current = memory.get('project_context', {}).get(project_key, {}).get('summary', '(none)')
    console.print(f'\n[bold]Current summary:[/bold] [dim]{current}[/dim]')
    new_summary = console.input('\nNew project summary: ').strip()
    
    if new_summary:
        memory.setdefault('project_context', {}).setdefault(project_key, {})['summary'] = new_summary
        save_memory(memory)
        console.print('[green]✅ Summary updated![/green]')

def cmd_help():
    help_text = '''
[bold cyan]Nexus Commands[/bold cyan]

[bold]Chat:[/bold]
  Just type your request and press Enter to chat with AI

[bold]Special Commands:[/bold]
  /models      - List available models
  /config      - Configure provider and model
  /summary     - Set project summary for context
  /context     - Show current project context
  /clear       - Clear chat history
  /history     - Show session history
  /help        - Show this help
  /exit        - Exit Nexus

[bold]Tips:[/bold]
  - Use [cyan]--auto[/cyan] flag to auto-apply file changes
  - Multi-line input with [dim]\\[/dim] to continue
  - Arrow keys for command history

[bold]Examples:[/bold]
  nexus create a REST API with FastAPI
  nexus --auto add authentication to my app
  nexus fix the bug in main.py

[bold]Privacy:[/bold]
  Ollama runs 100% locally - your code never leaves your machine.
'''
    console.print(Markdown(help_text))

# ============================================================================
# EDIT PARSING & APPLICATION
# ============================================================================

def parse_edits(text: str) -> list:
    patterns = [
        r'```filepath:\n*(.+?)\n*\n(.*?)(?=```|$)',
        r'```file:\n*(.+?)\n*\n(.*?)(?=```|$)',
        r'```(\n?/.+?\/\\/?[^`\n]+)\n(.*?)```',
        r'```python\n(.*?)```',
        r'```(\n?python\n.*?)```',
    ]
    
    edits = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            if len(match.groups()) >= 2:
                path = match.group(1).strip()
                code = match.group(2).strip()
                
                # Clean up artifacts
                code = re.sub(r'</?tool_.*?>', '', code, flags=re.IGNORECASE)
                
                if path and code and path not in ['nexus.py', 'buff.py', 'freebuff.py']:
                    edits.append((path, code))
    
    # Deduplicate
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
        diff_lines = list(diff)[:30]
        if diff_lines:
            console.print('[dim]' + '─' * 60 + '[/dim]')
            for line in diff_lines:
                if line.startswith('+++') or line.startswith('---'):
                    console.print(f'[dim]{line.rstrip()}[/dim]', end='')
                elif line.startswith('+'):
                    console.print(f'[green]{line.rstrip()}[/green]', end='')
                elif line.startswith('-'):
                    console.print(f'[red]{line.rstrip()}[/red]', end='')
                else:
                    console.print(f'[dim]{line.rstrip()}[/dim]', end='')
            console.print('[dim]' + '─' * 60 + '[/dim]\n')
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
# MAIN CHAT LOOP
# ============================================================================

def chat_loop(auto_apply: bool = False, initial_instruction: str = None):
    config = load_config()
    context = load_project_context()
    
    provider = config.get('provider', DEFAULT_PROVIDER)
    default_model = config.get(f'{provider}_model', DEFAULT_MODEL if provider == 'ollama' else FREE_OPENROUTER_MODELS[0][0])
    model = default_model
    
    # Build initial messages
    messages = [
        {'role': 'system', 'content': build_system_prompt(context, provider, model)}
    ]
    
    # Load project history
    memory = load_memory()
    project_key = str(Path.cwd().absolute())
    history = memory.get('project_context', {}).get(project_key, {}).get('history', [])
    
    if history:
        history_text = '\n'.join([f'- {h}' for h in history[-5:]])
        messages[0]['content'] += f'\n\nRecent history:\n{history_text}'
    
    print_banner()
    print_status(provider, model, config)
    
    # Check Ollama status
    if provider == 'ollama':
        available, _ = check_ollama(config.get('ollama_base_url', OLLAMA_BASE_URL))
        if not available:
            console.print(f'\n[bold {WARNING_COLOR}]⚠️  Ollama not running[/bold {WARNING_COLOR}]')
            console.print('[dim]Start with: ollama serve[/dim]')
            console.print('[dim]Or use /config to switch to OpenRouter[/dim]\n')
    
    console.print('[dim]Type /help for commands[/dim]\n')
    
    # Handle initial instruction
    if initial_instruction:
        user_input = initial_instruction
    else:
        try:
            user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()
        except (KeyboardInterrupt, EOFError):
            console.print(f'\n[bold {WARNING_COLOR}]Goodbye![/bold {WARNING_COLOR}]')
            return
    
    while True:
        if not user_input:
            continue
        
        # Handle commands
        if user_input.startswith('/'):
            cmd = user_input[1:].lower()
            
            if cmd == 'exit':
                console.print(f'[bold {WARNING_COLOR}]Goodbye![/bold {WARNING_COLOR}]')
                save_memory(memory)
                break
            elif cmd == 'help':
                cmd_help()
                user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()
                continue
            elif cmd == 'models':
                cmd_list_models(config)
                user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()
                continue
            elif cmd == 'config':
                cmd_configure()
                config = load_config()
                provider = config.get('provider', DEFAULT_PROVIDER)
                model = config.get(f'{provider}_model', DEFAULT_MODEL)
                messages[0] = {'role': 'system', 'content': build_system_prompt(context, provider, model)}
                print_status(provider, model, config)
                user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()
                continue
            elif cmd == 'summary':
                cmd_set_summary()
                context = load_project_context()
                messages[0] = {'role': 'system', 'content': build_system_prompt(context, provider, model)}
                user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()
                continue
            elif cmd == 'context':
                num = len(context['files'])
                console.print(f'\n[bold]Project Files ({num}):[/bold]')
                for f in context['files'][:25]:
                    console.print(f'  [dim]{f}[/dim]')
                if num > 25:
                    console.print(f'  [dim]... and {num - 25} more[/dim]')
                summary_text = context.get('summary', '(none)')
                console.print(f'\n[bold]Summary:[/bold] {summary_text}\n')
                user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()
                continue
            elif cmd == 'clear':
                messages = [
                    {'role': 'system', 'content': build_system_prompt(context, provider, model)}
                ]
                console.print('[green]Chat cleared[/green]\n')
                user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()
                continue
            elif cmd == 'history':
                if history:
                    console.print('\n[bold]Recent History:[/bold]')
                    for i, h in enumerate(history[-10:], 1):
                        console.print(f'  [dim]{i}.[/dim] {h}')
                    console.print()
                else:
                    console.print('\n[dim]No history yet[/dim]\n')
                user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()
                continue
            else:
                console.print(f'[yellow]Unknown command: {cmd}[/yellow] (try /help)\n')
                user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()
                continue
        
        # Process user message
        messages.append({'role': 'user', 'content': user_input})
        
        console.print()
        response_buffer = []
        
        def stream_handler(chunk):
            print(chunk, end='', flush=True)
            response_buffer.append(chunk)
        
        if config.get('stream', True):
            response = ai_complete_with_fallback(messages, provider, model, stream_handler)
            print()
        else:
            with Progress(SpinnerColumn(), TextColumn('[progress.description]{task.description}'), console=console) as progress:
                task = progress.add_task('Thinking...', total=None)
                response = ai_complete_with_fallback(messages, provider, model, None)
                progress.update(task, completed=True)
        
        if response.startswith('Error'):
            console.print(f'[{ERROR_COLOR}]{response}[/{ERROR_COLOR}]\n')
            messages.pop()
            user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()
            continue
        
        full_response = ''.join(response_buffer)
        messages.append({'role': 'assistant', 'content': full_response})
        
        # Render response with markdown only when NOT streaming
        # (when streaming, chunks are already printed via stream_handler)
        if not config.get('stream', True):
            console.print(Markdown(full_response, code_theme="monokai"))
        
        # Parse and apply edits
        edits = parse_edits(response)
        if edits:
            console.print(f'\n[bold cyan]📝 Found {len(edits)} file change(s):[/bold cyan]')
            for path, _ in edits:
                console.print(f'  [green]•[/green] {path}')
            
            should_auto = auto_apply or config.get('auto_apply', False)
            if should_auto or console.input('\nApply changes? [y/N]: ').strip().lower() == 'y':
                success_count = 0
                for path, code in edits:
                    if apply_edit(path, code, config.get('show_diff', True)):
                        success_count += 1
                        console.print(f'[green]✓[/green] {path}')
                
                if success_count:
                    console.print(f'\n[green]✅ Applied {success_count}/{len(edits)} changes![/green]')
                    
                    # Update memory
                    memory.setdefault('project_context', {}).setdefault(project_key, {}).setdefault('history', []).append(user_input[:100])
                    save_memory(memory)
            else:
                console.print('[dim]Changes not applied[/dim]')
        
        console.print()
        user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    import argparse
    
    init_config_dir()
    
    parser = argparse.ArgumentParser(
        description='Nexus - The hub of your code universe. Free, powerful coding agent. No ads.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
[bold]Examples:[/bold]
  nexus                              Start interactive chat
  nexus create a web app             Start chat with request
  nexus --auto fix the bug           Auto-apply file changes
  nexus /models                      List available models
  nexus /config                      Configure provider/model

[bold]Providers:[/bold]
  Ollama      - Local models (private, free, no internet)
  OpenRouter  - Free cloud models (no ads, no subscription)
'''
    )
    parser.add_argument('instruction', nargs='*', help='Initial instruction')
    parser.add_argument('--auto', action='store_true', help='Auto-apply file changes')
    parser.add_argument('--provider', choices=['openrouter', 'ollama'], help='AI provider')
    parser.add_argument('--model', help='Model name')
    
    args = parser.parse_args()
    
    print_banner()
    
    # Handle single-command mode
    if args.instruction:
        instruction = ' '.join(args.instruction)
        
        # Handle /commands
        if instruction.startswith('/'):
            cmd = instruction[1:].lower()
            config = load_config()
            
            if cmd == 'models':
                cmd_list_models(config)
                return
            elif cmd == 'config':
                cmd_configure()
                return
        
        # Interactive chat with instruction
        chat_loop(auto_apply=args.auto, initial_instruction=instruction)
    else:
        chat_loop(auto_apply=args.auto)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print(f'\n[bold yellow]Goodbye![/bold yellow]')