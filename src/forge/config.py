import os
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".forge"
CONFIG_FILE = CONFIG_DIR / "config.json"
LICENSE_FILE = CONFIG_DIR / "license.json"
MEMORY_CACHE = CONFIG_DIR / "memory.db"

DEFAULTS = {
    "provider": "ollama",
    "model": "qwen2.5-coder:latest",
    "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    "temperature": 0.5,
    "max_tokens": 1000,
    "auto_apply": False,
    "theme": "dark",
    "supabase_url": os.getenv("SUPABASE_URL", "https://bzfgbkhkjxspvonwxtku.supabase.co"),
    "supabase_anon_key": os.getenv("SUPABASE_ANON_KEY", ""),
    "supabase_service_key": os.getenv("SUPABASE_SERVICE_KEY", ""),
    "groq_api_key": os.getenv("GROQ_API_KEY", ""),
    "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
    "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    "stripe_publishable_key": os.getenv("STRIPE_PUBLISHABLE_KEY", ""),
    "stripe_secret_key": os.getenv("STRIPE_SECRET_KEY", ""),
}

def ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        os.chmod(CONFIG_FILE, 0o600)
    if LICENSE_FILE.exists():
        os.chmod(LICENSE_FILE, 0o600)

def load_config():
    ensure_dir()
    try:
        if CONFIG_FILE.exists():
            data = json.loads(CONFIG_FILE.read_text())
            merged = DEFAULTS.copy()
            merged.update(data)
            return merged
    except:
        pass
    return DEFAULTS.copy()

def save_config(settings: dict):
    ensure_dir()
    current = load_config()
    current.update(settings)
    CONFIG_FILE.write_text(json.dumps(current, indent=2))
    os.chmod(CONFIG_FILE, 0o600)

def get_api_key(provider: str = None) -> str:
    cfg = load_config()
    if not provider:
        provider = cfg.get("provider", "ollama")
    provider = provider.lower()
    if provider == "groq":
        return cfg.get("groq_api_key", "") or os.getenv("GROQ_API_KEY", "")
    elif provider == "openrouter":
        return cfg.get("openrouter_api_key", "") or os.getenv("OPENROUTER_API_KEY", "")
    elif provider == "openai":
        return cfg.get("openai_api_key", "") or os.getenv("OPENAI_API_KEY", "")
    return ""
