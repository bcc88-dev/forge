#!/usr/bin/env python3
"""One-time script to migrate forge to src/ package structure."""
import shutil, os, sys
from pathlib import Path

BASE = Path("/root/forge")
SRC = BASE / "src" / "forge"

# Create __init__.py for subpackages
for pkg in [SRC / "memory", SRC / "license", SRC / "tools", SRC / "supabase"]:
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("")
    print(f"Created {pkg}")

# Copy core modules from existing forge.py
import ast
from forge import (
    load_config, save_config, load_memory, save_memory,
    parse_code_blocks, apply_edit, show_diff,
    call_openrouter, call_ollama, check_ollama_available, get_key
)

print("All core functions available for extraction")
print("Forge is ready to be restructured")
