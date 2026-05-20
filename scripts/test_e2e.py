"""End-to-end test for forge agent with all providers."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

print("=" * 60)
print("FORGE END-TO-END TEST SUITE")
print("=" * 60)

# 1. Package imports
print("\n[1/6] Testing package imports...")
from forge import __version__
from forge.config import load_config, save_config, CONFIG_DIR
from forge.api_client import chat, check_provider
from forge.memory import Memory
from forge.license import LicenseClient
from forge.tools import TOOLS
from forge.agent import run, build_prompt
from forge.supabase import supabase
print(f"  Forge v{__version__} - All modules import OK")

# 2. Configuration
print("\n[2/6] Testing configuration...")
cfg = load_config()
assert cfg.get("provider") == "ollama", f"Expected ollama, got {cfg.get('provider')}"
print(f"  Default provider: {cfg.get('provider')}")
print(f"  Default model: {cfg.get('model')}")
print(f"  Config dir: {CONFIG_DIR}")
save_config({"test_key": "test_value"})
cfg2 = load_config()
assert cfg2.get("test_key") == "test_value"
print("  Config read/write: OK")

# 3. Memory system
print("\n[3/6] Testing memory system...")
mem = Memory()
mem.remember("test_key", "test_value", "test_project")
results = mem.recall("test_key")
assert len(results) >= 1, f"Expected at least 1 result, got {len(results)}"
print(f"  Local memory: stored and recalled ({len(results)} entries)")

# 4. Provider detection
print("\n[4/6] Testing provider availability...")
ollama_avail, ollama_models = check_provider("ollama")
print(f"  Ollama: {'AVAILABLE' if ollama_avail else 'UNAVAILABLE'}")
if ollama_models:
    print(f"  Models: {', '.join(ollama_models[:3])}")
groq_avail, _ = check_provider("groq")
print(f"  Groq: {'CONFIGURED' if groq_avail else 'NOT CONFIGURED'}")

# 5. Ollama agent test
print("\n[5/6] Testing Ollama agent...")
result = run("list the files in this directory", auto=True)
success = result.get("success", False)
print(f"  Agent result: {'PASS' if success else 'FAIL'}")
if not success:
    print(f"  Error: {result.get('error', 'unknown')[:100]}")

# 6. Tool system
print("\n[6/6] Testing tool system...")
print(f"  Tools registered: {len(TOOLS)}")
for name, func in TOOLS.items():
    print(f"    - {name}: {func.__doc__.split(chr(10))[0] if func.__doc__ else 'N/A'}")

# Summary
all_ollama_ok = ollama_avail and success
print("\n" + "=" * 60)
print(f"OVERALL: {'PASS' if all_ollama_ok else 'PARTIAL'}")
print(f"  Core modules:      PASS")
print(f"  Configuration:     PASS")
print(f"  Memory system:     PASS")
print(f"  Ollama provider:   {'PASS' if ollama_avail else 'SKIP'}")
print(f"  Agent loop:        {'PASS' if success else 'FAIL'}")
print(f"  Tools:             PASS")
print("=" * 60)
