"""Supabase vector memory for cross-session persistence."""

import json
import urllib.request
import urllib.error
from ..config import load_config

class SupabaseMemory:
    def __init__(self):
        cfg = load_config()
        self.url = cfg.get("supabase_url", "")
        self.key = cfg.get("supabase_service_key", "")
        self._available = bool(self.url and self.key)
    
    @property
    def available(self):
        return self._available
    
    def _headers(self):
        return {
            "Content-Type": "application/json",
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Prefer": "return=minimal"
        }
    
    def remember(self, key: str, value: str, project: str = ""):
        if not self.available:
            return
        try:
            data = json.dumps({
                "key": key,
                "value": value,
                "project_path": project
            }).encode()
            req = urllib.request.Request(
                f"{self.url}/rest/v1/nyx_memory",
                data=data,
                headers=self._headers(),
                method="POST"
            )
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                pass
        except:
            pass
    
    def recall(self, query: str = "", limit: int = 5) -> list:
        if not self.available:
            return []
        try:
            url = f"{self.url}/rest/v1/nyx_memory?select=key,value,project_path,created_at&order=created_at.desc&limit={limit}"
            if query:
                import urllib.parse
                encoded = urllib.parse.quote(f"%{query}%")
                url += f"&key=ilike.{encoded}"
            req = urllib.request.Request(url, headers=self._headers())
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            return [
                {"key": r["key"], "value": r["value"], "project": r.get("project_path", ""), "created_at": r.get("created_at", "")}
                for r in data
            ]
        except:
            return []
