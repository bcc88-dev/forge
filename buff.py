#!/usr/bin/env python3
'''
Buff - Free, Powerful Coding Agent
Local + Cloud. No ads.
'''

import os
import sys
import json
import re
import requests
import difflib
from pathlib import Path
from typing import Optional, Callable

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
except ImportError:
    os.system('pip install rich')
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table

console = Console()

CONFIG_DIR = Path.home() / '.buff'
CONFIG_FILE = CONFIG_DIR / 'config.json'
MEMORY_FILE = CONFIG_DIR / 'memory.json'

FREE_MODELS = {
    'openrouter': [
        ('anthropic/claude-3.5-haiku', 'Claude 3.5 Haiku (Free)'),
        ('deepseek/deepseek-chat-v3', 'DeepSeek Chat V3 (Free)'),
        ('google/gemini-2.0-flash-exp', 'Gemini 2.0 Flash (Free)'),
        ('mistralai/mistral-nemo', 'Mistral Nemo (Free)'),
        ('openai/gpt-4o-mini', 'GPT-4o Mini (Free)'),
        ('meta-llama/llama-3.1-8b-instruct', 'Llama 3.1 8B (Free)'),
    ],
    'ollama': []
}

DEFAULT_OPENROUTER_MODEL = 'anthropic/claude-3.5-haiku'
DEFAULT_OLLAMA_MODEL = 'nemotron-3-super:cloud'
OLLAMA_BASE_URL = 'http://localhost:11434'

def init_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        default_config = {
            'provider': 'openrouter',
            'openrouter_model': DEFAULT_OPENROUTER_MODEL,
            'ollama_model': DEFAULT_OLLAMA_MODEL,
            'ollama_base_url': OLLAMA_BASE_URL,
            'temperature': 0.7,
            'max_tokens': 16000,
            'stream_responses': True
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
        return {'history': [], 'project_context': {}}

def save_memory(memory: dict):
    MEMORY_FILE.write_text(json.dumps(memory, indent=2))

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
        
        r = requests.post(f'{base_url}/api/chat', json=payload, stream=True, timeout=120)
        
        if r.status_code != 200:
            return f'Ollama error: {r.status_code}'
        
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
        return f'Error: Cannot connect to Ollama at {base_url}. Is it running?'
    except Exception as e:
        return f'Error: {e}'

def get_openrouter_key() -> Optional[str]:
    config = load_config()
    
    if config.get('openrouter_key'):
        return config['openrouter_key']
    
    key = os.getenv('OPENROUTER_API_KEY')
    if key:
        return key
    
    console.print('\n[yellow]🔑 OpenRouter API key required for cloud models[/yellow]')
    console.print('Get free key at → [link=https://openrouter.ai/keys]https://openrouter.ai/keys[/link]')
    key = console.input('Paste your key (or press Enter to use Ollama only): ').strip()
    
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
        return 'Error: No OpenRouter API key'
    
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
                'HTTP-Referer': 'https://buff.local',
                'X-Title': 'Buff - Free Coding Agent'
            },
            json=payload,
            stream=True,
            timeout=120
        )
        
        if r.status_code != 200:
            return f'OpenRouter error {r.status_code}: {r.text}'
        
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

def ai_complete(
    messages: list,
    provider: str,
    model: str,
    stream_callback: Optional[Callable[[str], None]] = None
) -> str:
    config = load_config()
    temperature = config.get('temperature', 0.7)
    
    if provider == 'ollama':
        return call_ollama(
            messages,
            model,
            config.get('ollama_base_url', OLLAMA_BASE_URL),
            stream_callback,
            temperature
        )
    else:
        return call_openrouter(
            messages,
            model,
            stream_callback,
            temperature,
            config.get('max_tokens', 16000)
        )

def load_project_context(path: Path = Path('.')) -> dict:
    memory = load_memory()
    project_key = str(path.absolute())
    project_data = memory.get('project_context', {}).get(project_key, {})
    
    files = []
    gitignore_patterns = {'.git', '__pycache__', '.venv', 'node_modules', '.buff'}
    
    try:
        for p in path.rglob('*'):
            if p.is_file():
                if any(ign in p.parts for ign in gitignore_patterns):
                    continue
                if any(x.startswith('.') and x not in ['.buff', '.gitignore'] for x in p.parts):
                    continue
                if len(files) >= 100:
                    break
                files.append(str(p))
    except:
        pass
    
    return {
        'files': sorted(files)[:100],
        'summary': project_data.get('summary', ''),
        'history': project_data.get('history', [])[-5:]
    }

def build_system_prompt(context: dict) -> str:
    files_list = '\n'.join(context.get('files', [])) or '(empty directory)'
    summary = context.get('summary', 'New project')
    
    return f'''You are Buff, an expert coding assistant. Helpful, concise, and practical.

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

Guidelines:
- Be concise and actionable
- When creating/modifying files, use this format:
  ```filepath: relative/path.py
  code content here
  ```
- Don't modify buff.py or config files
- Focus on working code'''

def print_banner():
    banner = '''
 ═══════════════════════════════════════════════
  █████╗ ███████╗ ██████╗██╗██╗     ██╗
  ██╔══██╗██╔════╝██╔════╝██║██║     ██║
  ███████║███████╗██║     ██║██║     ██║
  ██╔══██║╚════██║██║     ██║██║     ██║
  ██║  ██║███████║╚██████╗██║███████╗███████╗
  ╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝╚══════╝╚══════╝
  
  Free. Powerful. Local + Cloud. No ads.
 ═══════════════════════════════════════════════
'''
    console.print(Panel.fit(banner.strip(), border_style='cyan', padding=(0, 2)))

def print_status(config: dict):
    provider = config.get('provider', 'openrouter')
    if provider == 'ollama':
        model = config.get('ollama_model', 'unknown')
        console.print('[cyan]Provider:[/cyan] Ollama  [cyan]Model:[/cyan] ' + model)
    else:
        model = config.get('openrouter_model', 'unknown')
        console.print('[cyan]Provider:[/cyan] OpenRouter  [cyan]Model:[/cyan] ' + model)

def select_model_interactive(config: dict, ollama_models: list) -> tuple[str, str]:
    console.print('\n[bold]Select provider:[/bold]')
    console.print('[1] OpenRouter (free cloud models)')
    console.print('[2] Ollama (local models)')
    
    choice = console.input('\nChoice (1/2) [Enter=1]: ').strip() or '1'
    
    if choice == '2':
        if not ollama_models:
            console.print('[yellow]No Ollama models available. Is Ollama running?[/yellow]')
            return 'openrouter', config.get('openrouter_model', DEFAULT_OPENROUTER_MODEL)
        
        console.print('\n[bold]Select Ollama model:[/bold]')
        for i, model in enumerate(ollama_models, 1):
            console.print(f'  [{i}] {model}')
        
        sel = console.input(f'\nChoice [1-{len(ollama_models)}]: ').strip() or '1'
        try:
            idx = max(1, min(int(sel), len(ollama_models))) - 1
            return 'ollama', ollama_models[idx]
        except:
            return 'ollama', ollama_models[0]
    else:
        models = FREE_MODELS['openrouter']
        console.print('\n[bold]Select OpenRouter model:[/bold]')
        for i, (model_id, desc) in enumerate(models, 1):
            console.print(f'  [{i}] {desc}')
        
        sel = console.input(f'\nChoice [1-{len(models)}]: ').strip() or '1'
        try:
            idx = max(1, min(int(sel), len(models))) - 1
            return 'openrouter', models[idx][0]
        except:
            return 'openrouter', DEFAULT_OPENROUTER_MODEL

def cmd_list_models(config: dict):
    console.print('\n[bold cyan]📋 Available Models[/bold cyan]\n')
    
    console.print('[bold]OpenRouter (Free Cloud):[/bold]')
    table = Table(show_header=False, box=None)
    for model_id, desc in FREE_MODELS['openrouter']:
        table.add_row('[green]•[/green] ' + desc)
        table.add_row('    [dim]' + model_id + '[/dim]')
    console.print(table)
    
    console.print('\n[bold]Ollama (Local):[/bold]')
    available, models = check_ollama(config.get('ollama_base_url', OLLAMA_BASE_URL))
    if available:
        for model in models:
            console.print('  [cyan]•[/cyan] ' + model)
    else:
        console.print('  [dim]Ollama not running. Run: ollama serve[/dim]')

def cmd_configure():
    config = load_config()
    _, ollama_models = check_ollama(config.get('ollama_base_url', OLLAMA_BASE_URL))
    
    console.print('\n[bold cyan]⚙️  Configuration[/bold cyan]\n')
    
    cur_provider = config.get('provider', 'openrouter')
    console.print('Current provider: [cyan]' + cur_provider + '[/cyan]')
    new_provider, new_model = select_model_interactive(config, ollama_models)
    config['provider'] = new_provider
    if new_provider == 'ollama':
        config['ollama_model'] = new_model
    else:
        config['openrouter_model'] = new_model
    
    cur_temp = config.get('temperature', 0.7)
    temp = console.input(f'\nTemperature [{cur_temp}]: ').strip()
    if temp:
        try:
            config['temperature'] = max(0.0, min(2.0, float(temp)))
        except ValueError:
            console.print('[yellow]Invalid temperature[/yellow]')
    
    cur_stream = config.get('stream_responses', True)
    stream_q = console.input(f'Stream responses (y/n) [{cur_stream}]: ').strip().lower()
    if stream_q in ['y', 'yes']:
        config['stream_responses'] = True
    elif stream_q in ['n', 'no']:
        config['stream_responses'] = False
    
    save_config(config)
    console.print('[green]✅ Configuration saved![/green]')

def cmd_set_project_summary():
    memory = load_memory()
    project_key = str(Path.cwd().absolute())
    
    current_summary = memory.get('project_context', {}).get(project_key, {}).get('summary', '(none)')
    console.print('\n[bold]Current summary:[/bold] ' + current_summary)
    new_summary = console.input('\nNew project summary: ').strip()
    
    if new_summary:
        if 'project_context' not in memory:
            memory['project_context'] = {}
        if project_key not in memory['project_context']:
            memory['project_context'][project_key] = {}
        memory['project_context'][project_key]['summary'] = new_summary
        save_memory(memory)
        console.print('[green]✅ Summary saved![/green]')

def cmd_help():
    help_text = '''
[bold cyan]Buff Commands[/bold cyan]

[bold]Core:[/bold]
  Just type your request and press Enter to chat with AI
  Use --auto flag to auto-apply file changes without asking

[bold]Special Commands:[/bold]
  /models      - List available models (OpenRouter + Ollama)
  /config      - Configure provider and model
  /summary     - Set project summary for context
  /context     - Show current project context
  /clear       - Clear chat history
  /help        - Show this help
  /exit        - Exit Buff

[bold]Examples:[/bold]
  buff create a REST API with FastAPI
  buff --auto add authentication to my app

[bold]Providers:[/bold]
  OpenRouter: Free cloud models with high token limits
  Ollama: Local models (no internet required)
'''
    console.print(Markdown(help_text))

def chat_loop(auto_apply: bool = False):
    config = load_config()
    context = load_project_context()
    
    messages = [
        {'role': 'system', 'content': build_system_prompt(context)}
    ]
    
    memory = load_memory()
    project_key = str(Path.cwd().absolute())
    history = memory.get('project_context', {}).get(project_key, {}).get('history', [])
    
    if history:
        history_text = '\n'.join([f'- {h}' for h in history[-3:]])
        messages[0]['content'] += f'\n\nRecent history:\n{history_text}'
    
    provider = config.get('provider', 'openrouter')
    default_model = DEFAULT_OLLAMA_MODEL if provider == 'ollama' else DEFAULT_OPENROUTER_MODEL
    model = config.get('ollama_model' if provider == 'ollama' else 'openrouter_model', default_model)
    
    print_status(config)
    console.print('[dim]Type /help for commands, /exit to quit[/dim]\n')
    
    if provider == 'ollama':
        available, _ = check_ollama(config.get('ollama_base_url', OLLAMA_BASE_URL))
        if not available:
            console.print('[yellow]⚠️  Ollama not available. Use /config to switch provider[/yellow]\n')
    
    while True:
        try:
            user_input = console.input('[bold cyan]❯[/bold cyan] ').strip()
        except (KeyboardInterrupt, EOFError):
            console.print('\n[yellow]Goodbye![/yellow]')
            break
        
        if not user_input:
            continue
        
        if user_input.startswith('/'):
            cmd = user_input[1:].lower()
            
            if cmd == 'exit':
                console.print('[yellow]Goodbye![/yellow]')
                break
            elif cmd == 'help':
                cmd_help()
                continue
            elif cmd == 'models':
                cmd_list_models(config)
                continue
            elif cmd == 'config':
                cmd_configure()
                config = load_config()
                provider = config.get('provider', 'openrouter')
                default_model = DEFAULT_OLLAMA_MODEL if provider == 'ollama' else DEFAULT_OPENROUTER_MODEL
                model = config.get('ollama_model' if provider == 'ollama' else 'openrouter_model', default_model)
                print_status(config)
                continue
            elif cmd == 'summary':
                cmd_set_project_summary()
                context = load_project_context()
                messages[0] = {'role': 'system', 'content': build_system_prompt(context)}
                continue
            elif cmd == 'context':
                num = len(context['files'])
                console.print('\n[bold]Files (' + str(num) + '):[/bold]')
                for f in context['files'][:20]:
                    console.print('  [dim]' + f + '[/dim]')
                if len(context['files']) > 20:
                    remaining = len(context['files']) - 20
                    console.print('  [dim]... and ' + str(remaining) + ' more[/dim]')
                summary_text = context.get('summary', '(none)')
                console.print('\n[bold]Summary:[/bold] ' + summary_text + '\n')
                continue
            elif cmd == 'clear':
                messages = [
                    {'role': 'system', 'content': build_system_prompt(context)}
                ]
                console.print('[green]Chat cleared[/green]\n')
                continue
            else:
                console.print('[yellow]Unknown command: ' + cmd + '[/yellow] (try /help)\n')
                continue
        
        messages.append({'role': 'user', 'content': user_input})
        
        console.print()
        response_buffer = []
        
        def stream_handler(chunk):
            print(chunk, end='', flush=True)
            response_buffer.append(chunk)
        
        config = load_config()
        if config.get('stream_responses', True):
            response = ai_complete(messages, provider, model, stream_handler)
            print()
        else:
            with Progress(SpinnerColumn(), TextColumn('[progress.description]{task.description}'), console=console) as progress:
                progress.add_task('Thinking...', total=None)
                response = ai_complete(messages, provider, model, None)
        
        if response.startswith('Error'):
            console.print('[red]' + response + '[/red]\n')
            messages.pop()
            continue
        
        messages.append({'role': 'assistant', 'content': ''.join(response_buffer)})
        
        edits = parse_edits(response)
        if edits:
            console.print('\n[cyan]📝 Found ' + str(len(edits)) + ' file change(s):[/cyan]')
            for path, code in edits:
                console.print('  [green]•[/green] ' + path)
            
            if auto_apply or console.input('\nApply changes? [y/N]: ').strip().lower() == 'y':
                for path, code in edits:
                    apply_edit(path, code)
                console.print('[green]✅ Changes applied![/green]')
                
                memory = load_memory()
                project_key = str(Path.cwd().absolute())
                if 'project_context' not in memory:
                    memory['project_context'] = {}
                if project_key not in memory['project_context']:
                    memory['project_context'][project_key] = {}
                memory['project_context'][project_key].setdefault('history', []).append(user_input[:100])
                save_memory(memory)
            else:
                console.print('[dim]Changes not applied[/dim]')
        
        console.print()

def parse_edits(text: str) -> list:
    patterns = [
        r'```filepath:\s*(.+?)\s*\n(.*?)(?=```|$)',
        r'```file:\s*(.+?)\s*\n(.*?)(?=```|$)',
        r'```(\S+\.\S+)\n(.*?)```',
        r'```python\n(.*?)```',
    ]
    
    edits = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.DOTALL):
            if len(match.groups()) >= 2:
                path = match.group(1).strip()
                code = match.group(2).strip()
                
                if path and code and path not in ['buff.py']:
                    code = re.sub(r'</?tool_.*?>', '', code, flags=re.IGNORECASE)
                    edits.append((path, code))
    
    seen = set()
    result = []
    for path, code in edits:
        if path not in seen:
            seen.add(path)
            result.append((path, code))
    
    return result

def apply_edit(path: str, content: str):
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        old = ''
        if p.exists():
            old = p.read_text()
        
        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f'a/{path}',
            tofile=f'b/{path}'
        )
        diff_lines = list(diff)[:20]
        if diff_lines:
            console.print('[dim]' + ''.join(diff_lines) + '[/dim]')
        
        p.write_text(content)
        console.print('[green]✓[/green] ' + path)
        
    except Exception as e:
        console.print('[red]✗[/red] ' + path + ': ' + str(e))

def main():
    import argparse
    
    init_config_dir()
    
    parser = argparse.ArgumentParser(
        description='Buff - Free, powerful coding agent. No ads.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  buff                              Start interactive chat
  buff create a web app             Start chat with specific request
  buff --auto fix the bug           Auto-apply file changes
  buff /models                      List available models
  buff /config                      Configure provider/model

Providers:
  OpenRouter - Free cloud models (high token limits)
  Ollama     - Local models (no internet required)
'''
    )
    parser.add_argument('instruction', nargs='*', help='Initial instruction')
    parser.add_argument('--auto', action='store_true', help='Auto-apply file changes')
    parser.add_argument('--provider', choices=['openrouter', 'ollama'], help='AI provider to use')
    parser.add_argument('--ollama-model', help='Ollama model name')
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.instruction and args.instruction[0].startswith('/'):
        cmd = args.instruction[0][1:].lower()
        config = load_config()
        
        if cmd == 'models':
            cmd_list_models(config)
            return
        elif cmd == 'config':
            cmd_configure()
            return
    
    if args.instruction:
        instruction = ' '.join(args.instruction)
        config = load_config()
        context = load_project_context()
        
        # CLI args override config
        provider = args.provider if args.provider else config.get('provider', 'openrouter')
        default_model = DEFAULT_OLLAMA_MODEL if provider == 'ollama' else DEFAULT_OPENROUTER_MODEL
        if provider == 'ollama' and args.ollama_model:
            model = args.ollama_model
        else:
            model = config.get('ollama_model' if provider == 'ollama' else 'openrouter_model', default_model)
        
        messages = [
            {'role': 'system', 'content': build_system_prompt(context)},
            {'role': 'user', 'content': instruction}
        ]
        
        console.print('[dim]Using ' + provider + ' / ' + model + '[/dim]\n')
        
        response_buffer = []
        def stream_handler(chunk):
            print(chunk, end='', flush=True)
            response_buffer.append(chunk)
        
        response = ai_complete(messages, provider, model, stream_handler)
        print()
        
        if not response.startswith('Error'):
            edits = parse_edits(response)
            if edits:
                console.print('\n[cyan]Found ' + str(len(edits)) + ' file change(s)[/cyan]')
                if args.auto or console.input('Apply? [y/N]: ').strip().lower() == 'y':
                    for path, code in edits:
                        apply_edit(path, code)
    else:
        chat_loop(auto_apply=args.auto)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print('\n[yellow]Goodbye![/yellow]')