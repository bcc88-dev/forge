#!/usr/bin/env python3
import re

with open('nyx.py', 'r') as f:
    content = f.read()

# 1. Change ChatHistory default to agentic mode
content = content.replace(
    'self.agentic_mode = False',
    'self.mode = \\'agentic\\'  # \\'agentic\\', \\'chat\\', or \\'review\\' - agentic is default'
)

# 2. Update build_system_prompt signature and usage
content = content.replace(
    'def build_system_prompt(cwd: str, agentic_mode: bool) -> str:',
    'def build_system_prompt(cwd: str, mode: str) -> str:'
)
content = content.replace(
    'agentic_mode = True',
    'mode == \\'agentic\\''
)
content = content.replace(
    'agentic_mode = False',
    'mode == \\'chat\\''
)
content = content.replace(
    'build_system_prompt(cwd, chat.agentic_mode)',
    'build_system_prompt(cwd, chat.mode)'
)
content = content.replace(
    'build_system_prompt(cwd, True)',
    'build_system_prompt(cwd, \\'agentic\\')'
)
content = content.replace(
    'build_system_prompt(cwd, False)',
    'build_system_prompt(cwd, \\'chat\\')'
)

# 3. Update print_status_bar signature and calls
content = content.replace(
    'def print_status_bar(provider: str, model: str, agentic_mode: bool, cwd: str):',
    'def print_status_bar(provider: str, model: str, mode: str, cwd: str):'
)
content = content.replace(
    'if agentic_mode:',
    'if mode == \\'agentic\\':'
)
content = content.replace(
    'else:',
    'elif mode == \\'chat\\':'
)
content = content.replace(
    'print_status_bar(provider, model, chat.agentic_mode, cwd)',
    'print_status_bar(provider, model, chat.mode, cwd)'
)

# 4. Update /agentic command
content = content.replace(
    \"if user_input.lower() == '/agentic':\",
    \"if user_input.lower() in ('/agentic', '/mode agentic'):\"
)
content = content.replace(
    'chat.agentic_mode = True',
    \"chat.mode = 'agentic'\"
)

# 5. Update /chat command
content = content.replace(
    \"if user_input.lower() == '/chat':\",
    \"if user_input.lower() in ('/chat', '/mode chat'):\"
)
content = content.replace(
    'chat.agentic_mode = False',
    \"chat.mode = 'chat'\"
)

# 6. Update agentic_mode checks
content = content.replace(
    'if chat.agentic_mode:',
    \"if chat.mode == 'agentic':\"
)
content = content.replace(
    'elif chat.agentic_mode:',
    \"elif chat.mode in ('agentic', 'review'):\"
)

# 7. Add new status bar mode display (replace the simple if/else with full mode buttons)
old_status_bar = '''    # Build mode string
    if agentic_mode:
        mode_str = f'[{AGENTIC_SYMBOL}] [bold magenta on #1a1a2e]AGENTIC[/bold magenta on #1a1a2e]'
    else:
        mode_str = '[dim]💬 CHAT[/dim]'''

new_status_bar = '''    # Build mode buttons - show all 3 modes with current highlighted
    modes = ['agentic', 'chat', 'review']
    mode_buttons = []
    for m in modes:
        if m == mode:
            if m == 'agentic':
                mode_buttons.append(f'[bold magenta on #1a1a2e]⚡ AGENTIC[/bold magenta on #1a1a2e]')
            elif m == 'chat':
                mode_buttons.append(f'[bold cyan on #1a1a2e]💬 CHAT[/bold cyan on #1a1a2e]')
            elif m == 'review':
                mode_buttons.append(f'[bold yellow on #1a1a2e]👁️ REVIEW[/bold yellow on #1a1a2e]')
        else:
            if m == 'agentic':
                mode_buttons.append(f'[dim]⚡ agentic[/dim] ([dim]m a[/dim])')
            elif m == 'chat':
                mode_buttons.append(f'[dim]💬 chat[/dim] ([dim]m c[/dim])')
            elif m == 'review':
                mode_buttons.append(f'[dim]👁️ review[/dim] ([dim]m r[/dim])')
    
    mode_str = ' '.join(mode_buttons)'''

content = content.replace(old_status_bar, new_status_bar)

# 8. Add mode hint after status bar
old_print_end = '''    console.print()
    console.print(f'[dim]┌─ [{CLOCK_SYMBOL}] {now} [/dim][dim]│[/dim] [dim]Provider:[/dim] [cyan]{provider}[/cyan] [dim]│[/dim] [dim]Model:[/dim] [magenta]{model}[/magenta] {mode_str} [dim]│[/dim] {git_str} [dim]─┐[/dim]')
    console.print(f'[dim]│[/dim] [dim]CPU:[/dim] [{cpu_color}]{stats['cpu']}[/{cpu_color}] [dim]│[/dim] [dim]MEM:[/dim] [{mem_color}]{stats['mem']}[/{mem_color}] [dim]│[/dim] [dim]DISK:[/dim] [cyan]{stats['disk']}[/cyan] [dim]│[/dim]')
    console.print(f'[dim]└─[/dim] [dim]📁[/dim] [cyan]{display_cwd}[/cyan]')
    console.print()'''

new_print_end = '''    console.print()
    console.print(f'[dim]┌─ [{CLOCK_SYMBOL}] {now} [/dim][dim]│[/dim] [dim]Provider:[/dim] [cyan]{provider}[/cyan] [dim]│[/dim] [dim]Model:[/dim] [magenta]{model}[/magenta][dim] │[/dim] {mode_str} [dim]│[/dim] {git_str} [dim]─┐[/dim]')
    console.print(f'[dim]│[/dim] [dim]CPU:[/dim] [{cpu_color}]{stats['cpu']}[/{cpu_color}] [dim]│[/dim] [dim]MEM:[/dim] [{mem_color}]{stats['mem']}[/{mem_color}] [dim]│[/dim] [dim]DISK:[/dim] [cyan]{stats['disk']}[/cyan] [dim]│[/dim]')
    console.print(f'[dim]└─[/dim] [dim]📁[/dim] [cyan]{display_cwd}[/cyan]')
    console.print()
    # Show mode switch hint
    if mode == 'agentic':
        console.print(f'[dim]  💡 Agentic: commands execute directly. m c for chat, m r for review[/dim]')
    elif mode == 'chat':
        console.print(f'[dim]  💡 Chat: AI only responds. m a for agentic, m r for review[/dim]')
    elif mode == 'review':
        console.print(f'[dim]  💡 Review: AI suggests, you approve. m a for agentic, m c for chat[/dim]')
    console.print()'''

content = content.replace(old_print_end, new_print_end)

with open('nyx.py', 'w') as f:
    f.write(content)

print('Changes applied successfully')