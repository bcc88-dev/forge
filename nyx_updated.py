def print_button_bar(agentic_mode: bool = True, session_id: str = None):
    '''Enhanced button bar with menu-style operations and session ID'''
    # Session badge
    sid_badge = f'[bold yellow]#{session_id[-8:]}[/bold yellow]' if session_id else '[dim]no-session[/dim]'
    
    # Mode indicator
    mode_icon = '[bold magenta]⚡[/bold magenta]' if agentic_mode else '[dim]💬[/dim]'
    mode_text = '[bold magenta]AGENTIC[/bold magenta]' if agentic_mode else '[dim]CHAT[/dim]'
    
    console.print()
    
    # Top border with session ID badge
    console.print(f'[dim]┌─{(BOX_H * 78)}┐[dim]')
    
    # Main button row with icons
    buttons = [
        ('A', mode_icon, 'Toggle'),
        ('L', '📋', 'Sessions'),
        ('S', '🔧', 'Status'),
        ('M', '🧠', 'Memory'),
        ('H', '❓', 'Help'),
        ('X', '🗑️', 'Clear'),
    ]
    
    button_str = f'{mode_icon} [{mode_text}] '
    for key, icon, label in buttons:
        button_str += f'[cyan][[/cyan][bold yellow]{key}[/bold yellow][cyan]][/cyan][white]{icon}[/white] {label}   '
    
    button_str += f'[cyan][[/cyan][bold yellow]/exit[/bold yellow][cyan]][/cyan]'
    
    console.print(f'[dim]│[/dim] {button_str}[dim]  │[dim]')
    
    # Session ID row
    console.print(f'[dim]│[/dim] [dim]Session:[/dim] {sid_badge}   [dim]Press key for one-click action[/dim]' + ' ' * 30 + f'[dim]│[dim]')
    
    console.print(f'[dim]└─{(BOX_H * 78)}┘[dim]')