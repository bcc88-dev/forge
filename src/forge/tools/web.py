"""Web fetch and search tools."""

import requests

def web_fetch(url: str) -> str:
    """Fetch content from a URL."""
    try:
        r = requests.get(url, timeout=15, headers={
            "User-Agent": "Forge/0.1.0"
        })
        if r.status_code == 200:
            content = r.text[:5000]
            return content
        return f"HTTP {r.status_code}: {r.reason}"
    except Exception as e:
        return f"Error fetching {url}: {e}"
