"""File read, write, edit, and listing operations."""

import os
from pathlib import Path

def read_file(path: str) -> str:
    """Read the contents of a file."""
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: {path} does not exist"
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading {path}: {e}"

def write_file(path: str, content: str) -> str:
    """Write content to a file, creating directories if needed."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Written {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error writing {path}: {e}"

def edit_file(path: str, old: str, new: str) -> str:
    """Replace text in a file."""
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: {path} does not exist"
        content = p.read_text(encoding="utf-8")
        if old not in content:
            return f"Error: Could not find matching text in {path}"
        new_content = content.replace(old, new, 1)
        n_changes = content.count(old)
        p.write_text(new_content, encoding="utf-8")
        return f"Replaced 1 occurrence in {path}"
    except Exception as e:
        return f"Error editing {path}: {e}"

def list_files(path: str = ".", max_depth: int = 2) -> str:
    """List files in a directory recursively up to max_depth."""
    try:
        p = Path(path)
        if not p.exists():
            return f"Error: {path} does not exist"
        result = []
        _walk(p, result, 0, max_depth)
        return "\n".join(result) or "(empty directory)"
    except Exception as e:
        return f"Error listing {path}: {e}"

def _walk(path: Path, result: list, depth: int, max_depth: int):
    if depth > max_depth:
        return
    indent = "  " * depth
    try:
        entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        for entry in entries:
            if entry.name.startswith(".") or entry.name.startswith("__"):
                continue
            if entry.is_dir():
                result.append(f"{indent}{entry.name}/")
                _walk(entry, result, depth + 1, max_depth)
            else:
                size = entry.stat().st_size
                result.append(f"{indent}{entry.name} ({size}b)")
    except PermissionError:
        result.append(f"{indent}(permission denied)")
