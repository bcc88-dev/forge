"""Test Groq API integration."""
import sys
sys.path.insert(0, "src")

print("=== Testing Groq integration ===")

from forge.config import load_config
cfg = load_config()
print(f"groq_api_key set: {bool(cfg.get('groq_api_key'))}")
print(f"provider: {cfg.get('provider')}")
print(f"model: {cfg.get('model')}")

from forge.api_client import chat
result = chat("say hello in one word", provider="groq", model="llama-3.1-8b-instant")
print(f"Result: {result[:100]}")

# Now test with full agent
from forge.agent import run
result = run("say hello back", auto=True)
print(f"Agent success: {result.get('success', False)}")
if not result.get('success'):
    print(f"Error: {result.get('error', 'unknown')[:200]}")
