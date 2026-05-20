"""Multi-model API client - Groq, Ollama, OpenRouter, OpenAI."""

import json
import requests

from .config import load_config, get_api_key


def call_ollama(prompt: str, model: str = None, stream_callback=None):
    cfg = load_config()
    model = model or cfg.get("ollama_model", "qwen2.5-coder:latest")
    base_url = cfg.get("ollama_base_url", "http://localhost:11434")
    try:
        r = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "options": {"temperature": cfg.get("temperature", 0.5)}
            },
            timeout=120,
            stream=True
        )
        if r.status_code == 200:
            full = []
            for line in r.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            chunk = data["message"]["content"]
                            full.append(chunk)
                            if stream_callback:
                                stream_callback(chunk)
                    except json.JSONDecodeError:
                        pass
            return "".join(full)
        return f"Ollama Error {r.status_code}: {r.text}"
    except requests.exceptions.ConnectionError:
        base = cfg.get("ollama_base_url", "http://localhost:11434")
        return f"Error: Could not connect to Ollama at {base}. Is it running?"
    except Exception as e:
        return f"Connection error: {e}"


def call_groq(prompt: str, model: str = None, stream_callback=None):
    cfg = load_config()
    api_key = get_api_key("groq")
    if not api_key:
        return "Error: No Groq API key set. Run: clide config set groq_api_key YOUR_KEY"
    model = model or "llama-3.1-8b-instant"
    # Groq free tier TPM limit is 6000, so we must keep max_tokens low
    max_tokens = min(cfg.get("max_tokens", 2000), 2000)
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": cfg.get("temperature", 0.5),
                "max_tokens": max_tokens,
            },
            timeout=60
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        if r.status_code == 413:
            return (f"Groq rate limit: Your prompt ({r.json().get('error',{}).get('message','')[:100]}) "
                    f"exceeds free tier limits. Upgrade at https://console.groq.com/settings/billing "
                    f"or use Ollama locally.")
        return f"Groq Error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return f"Connection error: {e}"


def call_openrouter(prompt: str, model: str = None, stream_callback=None):
    cfg = load_config()
    api_key = get_api_key("openrouter")
    if not api_key:
        return "Error: No OpenRouter API key set"
    model = model or "openrouter/free"
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://forge-cli.vercel.app",
                "X-OpenRouter-Title": "CLIDE"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": cfg.get("temperature", 0.5),
                "max_tokens": cfg.get("max_tokens", 4000)
            },
            timeout=120
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"OpenRouter Error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return f"Connection error: {e}"


def call_openai(prompt: str, model: str = None, stream_callback=None):
    cfg = load_config()
    api_key = get_api_key("openai")
    if not api_key:
        return "Error: No OpenAI API key set"
    model = model or "gpt-4o-mini"
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": cfg.get("temperature", 0.5),
                "max_tokens": cfg.get("max_tokens", 4000)
            },
            timeout=120
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"OpenAI Error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return f"Connection error: {e}"


def chat(prompt: str, provider: str = None, model: str = None, stream_callback=None) -> str:
    cfg = load_config()
    provider = provider or cfg.get("provider", "ollama")
    provider = provider.lower()
    if provider == "groq":
        return call_groq(prompt, model, stream_callback)
    elif provider == "openrouter":
        return call_openrouter(prompt, model, stream_callback)
    elif provider == "openai":
        return call_openai(prompt, model, stream_callback)
    else:
        return call_ollama(prompt, model, stream_callback)


def check_provider(provider: str = "ollama") -> tuple:
    cfg = load_config()
    if provider == "ollama":
        base_url = cfg.get("ollama_base_url", "http://localhost:11434")
        try:
            r = requests.get(f"{base_url}/api/tags", timeout=5)
            if r.status_code == 200:
                models = [m.get("name", "") for m in r.json().get("models", [])]
                return True, models
            return False, []
        except:
            return False, []
    elif provider == "groq":
        key = get_api_key("groq")
        return bool(key), []
    elif provider == "openrouter":
        key = get_api_key("openrouter")
        return bool(key), []
    return False, []
