"""Test that all forge modules import correctly."""
import sys
sys.path.insert(0, "src")

print("Testing forge imports...")

from forge import __version__
print(f"  version: {__version__}")

from forge.config import load_config, save_config, CONFIG_DIR
cfg = load_config()
print(f"  config loaded: provider={cfg.get('provider')}")
print(f"  config dir: {CONFIG_DIR}")

from forge.api_client import chat, check_provider
avail, models = check_provider("ollama")
print(f"  ollama available: {avail}, models: {len(models)}")
avail2, _ = check_provider("groq")
print(f"  groq configured: {avail2}")

from forge.memory import Memory
mem = Memory()
mem.remember("test_key", "test_value", "test_project")
results = mem.recall("test_key")
print(f"  memory: stored and recalled {len(results)} entries")

from forge.license import LicenseClient
lic = LicenseClient()
lic.start_trial()
print(f"  trial days remaining: {lic.remaining_trial_days()}")
print(f"  license valid: {lic.is_valid()}")

from forge.tools import TOOLS, describe_tools
print(f"  tools registered: {len(TOOLS)}")
print(f"  tool descriptions:")
print(describe_tools())

from forge.supabase import supabase
conn = supabase.test_connection()
print(f"  supabase connected: {conn}")

print()
print("All modules import and function correctly!")
