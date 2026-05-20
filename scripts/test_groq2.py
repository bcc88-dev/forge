"""Test Groq with fixed rate limit handling."""
import sys
sys.path.insert(0, "src")

print("=== Groq Rate Limit Test ===")

from forge.config import save_config
save_config({"provider": "groq", "model": "llama-3.1-8b-instant"})

from forge.api_client import call_groq
result = call_groq("say hello in one word", model="llama-3.1-8b-instant")
print(f"Result: {result[:200]}")
if "rate limit" in result.lower() or "Error" in result:
    print("RATE LIMITED - This is expected on free tier without a payment method")
    print("Upgrade at https://console.groq.com/settings/billing for higher limits")
else:
    print("GROQ WORKS!")

# Reset back to Ollama
save_config({"provider": "ollama", "model": "qwen2.5-coder:latest"})
print("\nReset to Ollama default")
