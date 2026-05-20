# CLIDE

The AI coding agent that **never forgets**.

Every session, every preference, every decision — remembered forever. Cross-session, cross-model, cross-machine.

## Quick Install

```bash
pip install forge-cli
```

## Usage

```bash
# Interactive mode
forge

# One-shot prompt
forge "refactor the auth module to use JWT"

# Headless with auto-apply
forge --auto "fix the test suite"

# Manage memory
forge memory --remember "user prefers tabs"=true
forge memory --recall "tabs"

# Configure providers
forge config set provider groq
forge config set groq_api_key gsk_xxx

# Check license status
forge license
```

## Features

- **Persistent Memory** — remembers everything across sessions via Supabase vector DB
- **Multi-Model** — Groq, OpenAI, Ollama, OpenRouter — you choose
- **Code Generation** — read, write, edit files with smart diff preview
- **Sub-Agents** — parallel task execution
- **Your Data** — API keys never leave your machine, memory in your Supabase
- **Offline-First** — 7-day license grace period, local SQLite cache

## Providers

| Provider | Default Model | Auth |
|---|---|---|
| Ollama (local) | qwen2.5-coder:latest | None |
| Groq | llama3-70b-8192 | API key |
| OpenRouter | openrouter/free | API key |
| OpenAI | gpt-4o-mini | API key |

## Architecture

```
forge/              # Python package (src/forge/)
├── cli.py          # CLI argument parser
├── agent.py        # Agent execution loop
├── api_client.py   # Multi-model API client
├── config.py       # Config management
├── memory/         # Local + Supabase memory
├── license/        # License validation + trial
├── supabase/       # Auth + data client
└── tools/          # Bash, file ops, web

api/                # Vercel serverless
├── license/        # Key creation + validation
└── webhook/        # Stripe events

web/                # Landing page
supabase/           # DB migrations
```

## License

MIT
