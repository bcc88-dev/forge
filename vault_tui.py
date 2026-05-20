#!/usr/bin/env python3
'''
Ansible Vault Manager TUI - Big, Bold, Beautiful Terminal Interface

A modern, visually striking TUI for managing Ansible vault files.
Features: List, Create, Edit, Encrypt, Decrypt vault files with ansible-vault integration.

Requirements:
    - textual library: pip install textual
    - ansible-vault command available in PATH

Usage:
    python vault_tui.py

Keyboard shortcuts:
    n - New vault file
    e - Edit selected vault
    d - Decrypt selected vault
    a - Encrypt selected vault
    r - Refresh file list
    ? - Show help
    q - Quit
'''

import subprocess
import os
from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Label, Input, Static
from textual.binding import Binding

# ⚙️ CONFIGURE THIS TO MATCH YOUR VAULT LOCATION
VAULT_DIR = Path('./group_vars').resolve()  # Change to your vault directory


class VaultTUI(App):
    CSS_PATH = 'vault_tui.css'
    BINDINGS = [
        Binding('q', 'quit', 'Quit', priority=True),
        Binding('r', 'refresh', 'Refresh'),
        Binding('n', 'new_vault', 'New Vault'),
        Binding('e', 'edit_vault', 'Edit Vault'),
        Binding('d', 'decrypt_vault', 'Decrypt'),
        Binding('a', 'encrypt_vault', 'Encrypt'),
        Binding('?', 'show_help', 'Help'),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Label('🔐 ANSIBLE VAULT MANAGER', id='title'),
                Label('Manage encrypted secrets with confidence', id='subtitle'),
                id='header'
            ),
            Vertical(
                Label('Available Vault Files:', id='section-title'),
                Static(id='vault-list', classes='vault-list'),
                id='main'
            ),
            Horizontal(
                Button('New', variant='success', id='btn-new'),
                Button('Edit', variant='primary', id='btn-edit'),
                Button('Decrypt', variant='warning', id='btn-decrypt'),
                Button('Encrypt', variant='primary', id='btn-encrypt'),
                Button('Refresh', variant='default', id='btn-refresh'),
                Button('Help', variant='default', id='btn-help'),
                Button('Quit', variant='error', id='btn-quit'),
                id='button-bar'
            ),
            id='app-container'
        )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_vault_list()
        self.notify('Vault TUI Ready! Press ? for help', severity='information', timeout=3)

    def action_refresh(self) -> None:
        self.refresh_vault_list()
        self.notify('Vault list refreshed!', severity='information')

    def action_new_vault(self) -> None:
        self.push_screen(NewVaultScreen())

    def action_edit_vault(self) -> None:
        selected = self.query_one('#vault-list').highlighted_child
        if selected and selected.id not in ['vault-list', 'list-header']:
            self.push_screen(EditVaultScreen(selected.id))

    def action_decrypt_vault(self) -> None:
        selected = self.query_one('#vault-list').highlighted_child
        if selected and selected.id not in ['vault-list', 'list-header']:
            self.decrypt_vault(selected.id)

    def action_encrypt_vault(self) -> None:
        selected = self.query_one('#vault-list').highlighted_child
        if selected and selected.id not in ['vault-list', 'list-header']:
            self.encrypt_vault(selected.id)

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def refresh_vault_list(self) -> None:
        vault_list = self.query_one('#vault-list')
        vault_list.remove_children()

        # Add header
        vault_list.mount(Static('📁 Vault Files', classes='list-header'))

        # Ensure directory exists
        if not VAULT_DIR.exists():
            VAULT_DIR.mkdir(parents=True, exist_ok=True)

        # Add vault files
        vault_files = sorted(VAULT_DIR.glob('*.yml'))
        if not vault_files:
            vault_list.mount(Static('📭 No vault files found', classes='hint'))
            vault_list.mount(Static('Press [n] to create a new vault', classes='hint'))
            return

        for vault_file in vault_files:
            # Skip backup files
            if vault_file.name.endswith('~') or '.bak' in vault_file.name:
                continue

            is_encrypted = self.is_encrypted(vault_file)
            icon = '🔒' if is_encrypted else '🔓'
            status = 'ENCRYPTED' if is_encrypted else 'PLAINTEXT'
            label = Label(
                f'{icon} {vault_file.name}  [{status}]',
                id=vault_file.name
            )
            label.tooltip = (
                f'Path: {vault_file}\n'
                f'Size: {vault_file.stat().st_size} bytes\n'
                f'Modified: {vault_file.stat().st_mtime}\n'
                f'Encrypted: {is_encrypted}'
            )
            vault_list.mount(label)

    def is_encrypted(self, file_path: Path) -> bool:
        try:
            result = subprocess.run(
                ['ansible-vault', 'view', str(file_path)],
                capture_output=True,
                text=True,
                timeout=3
            )
            return result.returncode != 0  # Non-zero = encrypted (or error)
        except FileNotFoundError:
            return True  # Assume encrypted if ansible-vault missing
        except:
            return True  # Fail-safe: treat errors as encrypted

    def decrypt_vault(self, filename: str) -> None:
        vault_file = VAULT_DIR / filename
        try:
            result = subprocess.run(
                ['ansible-vault', 'decrypt', str(vault_file)],
                capture_output=True,
                text=True,
                check=True
            )
            self.notify(f'✅ Decrypted {filename}', severity='success', timeout=3)
            self.refresh_vault_list()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if isinstance(e.stderr, str) else e.stderr.decode().strip()
            self.notify(f'❌ Decrypt failed: {error_msg}', severity='error', timeout=5)
        except Exception as e:
            self.notify(f'❌ Error: {str(e)}', severity='error', timeout=5)

    def encrypt_vault(self, filename: str) -> None:
        vault_file = VAULT_DIR / filename
        try:
            result = subprocess.run(
                ['ansible-vault', 'encrypt', str(vault_file)],
                capture_output=True,
                text=True,
                check=True
            )
            self.notify(f'🔒 Encrypted {filename}', severity='success', timeout=3)
            self.refresh_vault_list()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if isinstance(e.stderr, str) else e.stderr.decode().strip()
            self.notify(f'❌ Encrypt failed: {error_msg}', severity='error', timeout=5)
        except Exception as e:
            self.notify(f'❌ Error: {str(e)}', severity='error', timeout=5)


class NewVaultScreen(Static):
    '''Screen for creating new vault files'''
    def compose(self) -> ComposeResult:
        yield Label('🔐 CREATE NEW VAULT FILE', classes='title')
        yield Input(
            placeholder='filename.yml (e.g., db_secrets.yml)',
            id='filename',
            type='text'
        )
        yield Horizontal(
            Button('Create', variant='success', id='btn-create'),
            Button('Cancel', variant='error', id='btn-cancel'),
            id='button-bar'
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'btn-create':
            filename = self.query_one('#filename').value.strip()
            if not filename:
                self.notify('❌ Filename required!', severity='error')
                return
            if not filename.endswith('.yml'):
                filename += '.yml'

            vault_file = VAULT_DIR / filename
            if vault_file.exists():
                self.notify(f'❌ File {filename} already exists!', severity='error')
                return

            try:
                # Create empty encrypted file
                subprocess.run(
                    ['ansible-vault', 'create', str(vault_file)],
                    input=b'',  # Empty content
                    check=True,
                    capture_output=True
                )
                self.notify(f'✅ Created {filename}', severity='success', timeout=3)
                self.app.refresh_vault_list()
                self.dismiss()
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode().strip() if isinstance(e.stderr, bytes) else str(e.stderr)
                self.notify(f'❌ Creation failed: {error_msg}', severity='error', timeout=5)
            except Exception as e:
                self.notify(f'❌ Error: {str(e)}', severity='error', timeout=5)
        else:
            self.dismiss()


class EditVaultScreen(Static):
    '''Screen for editing vault files'''
    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename

    def compose(self) -> ComposeResult:
        yield Label(f'🔐 EDIT VAULT: {self.filename}', classes='title')
        editor = os.environ.get('EDITOR', 'vim')
        yield Label(f'Will open in $EDITOR ({editor})', classes='hint')
        yield Horizontal(
            Button('Open in Editor', variant='primary', id='btn-edit'),
            Button('Cancel', variant='error', id='btn-cancel'),
            id='button-bar'
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'btn-edit':
            vault_file = VAULT_DIR / self.filename
            try:
                subprocess.run(
                    ['ansible-vault', 'edit', str(vault_file)],
                    check=True
                )
                self.notify(f'✅ Edited {self.filename}', severity='success', timeout=3)
                self.app.refresh_vault_list()
                self.dismiss()
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode().strip() if isinstance(e.stderr, bytes) else str(e.stderr)
                self.notify(f'❌ Edit failed: {error_msg}', severity='error', timeout=5)
            except Exception as e:
                self.notify(f'❌ Error: {str(e)}', severity='error', timeout=5)
        else:
            self.dismiss()


class HelpScreen(Static):
    '''Help screen with keybindings'''
    def compose(self) -> ComposeResult:
        yield Label('❓ VAULT TUI HELP', classes='title')
        yield Static('''
 🔑 KEYBINDINGS:
   n  → New vault file
   e  → Edit selected vault
   d  → Decrypt selected vault
   a  → Encrypt selected vault
   r  → Refresh file list
   ?  → Show this help
   q  → Quit application

 💡 TIPS:
   • Use ↑↓ arrows to navigate vault list
   • Encrypted files show 🔒, plaintext show 🔓
   • All actions require ansible-vault in PATH
   • Vaults are in ./group_vars (edit VAULT_DIR in code to change)
        ''', id='help-content')
        yield Button('Close', variant='default', id='btn-close')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'btn-close':
            self.dismiss()


if __name__ == '__main__':
    app = VaultTUI()
    app.run()