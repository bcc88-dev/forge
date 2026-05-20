def print_detailed_status():
    '''Print detailed system status'''
    stats = get_system_stats()
    git_status = GitHelper.get_status()
    
    # Get Python and venv info
    py_version = sys.version.split()[0]
    venv = os.environ.get('VIRTUAL_ENV', 'none')
    
    console.print(f'\n[{GREEN}]╭─ System Status ──────────────────────────────────────────╮[{GREEN}]')
    console.print(f'[{CYAN}]📋[/cyan] [bold white]Python:[/bold white] [green]{py_version}[/green]')
    console.print(f'[{CYAN}]🧩[/cyan] [bold white]Venv:[/bold white] [yellow]{venv}[/yellow]')
    
    if git_status['branch']:
        console.print(f'[{CYAN}]±[/cyan] [bold white]Git:[/bold white] [green]{git_status['branch']}[/green]', end='')
        if not git_status['clean']:
            console.print(f' [+{git_status['modified']} ?{git_status['untracked']}]')
        else:
            console.print(f' [clean]')
    else:
        console.print(f'[{DIM}]±[/dim] [dim]Git: none[/{dim}]')
    
    console.print(f'[{CYAN}]💾[/cyan] [bold white]CPU:[/bold white] [{GREEN}]{stats['cpu']}[/{GREEN}] [bold white]MEM:[/bold white] [{GREEN}]{stats['mem']}[/{GREEN}] [bold white]Disk:[/bold white] [{GREEN}]{stats['disk']}[/{GREEN}]')
    console.print(f'[{GREEN}]╰─────────────────────────────────────────────────────╯[{GREEN}]\n')

def print_detailed_memory():
    '''Print memory status from memory file'''
    config = load_config()
    memory = load_memory()
    
    console.print(f'\n[{CYAN}]╭─ Memory Status ──────────────────────────────────────────╮[{CYAN}]')
    
    # Show config info
    console.print(f'[{CYAN}]⚙️[/cyan] [bold white]Provider:[/bold white] [magenta]{config.get('ollama_base_url', OLLAMA_BASE_URL)}[/magenta]')
    console.print(f'[{CYAN}]🤖[/cyan] [bold white]Model:[/bold white] [green]{config.get('ollama_model', OLLAMA_MODEL)}[/green]')
    
    # Show session count
    sessions_dir = Path.home() / '.nexus' / 'sessions'
    if sessions_dir.exists():
        session_files = list(sessions_dir.glob('*.json'))
        console.print(f'[{CYAN}]📁[/cyan] [bold white]Sessions:[/bold white] [yellow]{len(session_files)}[/yellow] saved')
    
    # Show message count if available
    if memory:
        console.print(f'[{CYAN}]💬[/cyan] [bold white]Messages:[/bold white] [green]{len(memory.get('messages', []))}[/green]')
    
    console.print(f'[{CYAN}]╰─────────────────────────────────────────────────────╯[{CYAN}]\n')

def print_sessions_list():
    '''Print list of saved sessions'''
    sessions_dir = Path.home() / '.nexus' / 'sessions'
    index_file = sessions_dir / 'sessions.json'
    
    if not sessions_dir.exists():
        console.print(f'\n[{DIM}]╭─ Saved Sessions ───────────────────────────────────────╮[{DIM}]')
        console.print(f'[{DIM}]│   No sessions saved yet[/{DIM}]')
        console.print(f'[{DIM}]╰─────────────────────────────────────────────────────╯[{DIM}]\n')
        return
    
    console.print(f'\n[{CYAN}]╭─ Saved Sessions ───────────────────────────────────────╮[{CYAN}]')
    
    sessions_data = {}
    if index_file.exists():
        try:
            sessions_data = json.loads(index_file.read_text())
        except:
            pass
    
    if not sessions_data:
        console.print(f'[{DIM}]│   No sessions found[/{DIM}]')
    else:
        for name, info in sessions_data.items():
            # Truncate name for display
            display_name = name[:20] + '...' if len(name) > 20 else name
            msg_count = info.get('message_count', 0)
            saved_at = info.get('saved_at', 'unknown')
            
            # Format timestamp
            try:
                if 'T' in saved_at:
                    dt = datetime.fromisoformat(saved_at.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y-%m-%d %H:%M')
                else:
                    time_str = saved_at
            except:
                time_str = saved_at
            
            console.print(f'[{CYAN}]│[/cyan]  [bold green]{display_name}[/bold green] [dim]({msg_count} msgs)[/dim] [yellow]{time_str}[/yellow]')
            
            # Try to get first user message from full session file
            full_session_file = sessions_dir / f'{name}.json'
            if full_session_file.exists():
                try:
                    full_data = json.loads(full_session_file.read_text())
                    messages = full_data.get('messages', [])
                    for msg in messages:
                        if msg.get('role') == 'user':
                            first_msg = msg.get('content', '')[:50]
                            if first_msg:
                                console.print(f'[{DIM}]│      {first_msg}...[/dim]')
                            break
                except:
                    pass
            
            console.print(f'[{DIM}]│      cwd: {info.get('cwd', 'unknown')}[/{DIM}]')
    
    console.print(f'[{CYAN}]╰─────────────────────────────────────────────────────╯[{CYAN}]')
    console.print(f'  [dim]Use /load <name> to load a session[/{dim}]\n')