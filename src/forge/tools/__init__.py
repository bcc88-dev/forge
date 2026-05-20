"""Tool system - auto-discovered by the agent loop."""

from .bash import bash
from .file_ops import read_file, write_file, edit_file, list_files
from .web import web_fetch

TOOLS = {
    "bash": bash,
    "read": read_file,
    "write": write_file,
    "edit": edit_file,
    "ls": list_files,
    "web_fetch": web_fetch,
}

def describe_tools():
    descriptions = []
    for name, func in TOOLS.items():
        doc = (func.__doc__ or "No description").strip().split("\n")[0]
        descriptions.append(f"  - {name}: {doc}")
    return "\n".join(descriptions)
