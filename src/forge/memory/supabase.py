"""Supabase vector memory for cross-session persistence."""

import json
import urllib.request
import urllib.error
from ..config import load_config


class SupabaseMemory:
    def __init__(self):
        cfg = load_config()
        self.url = cfg.get("supabase_url", "")
        self.service_key = cfg.get("supabase_service_key", "")
        self.anon_key = cfg.get("supabase_anon_key", "")
        self._service_ok = bool(self.url and self.service_key)
        self._anon_ok = bool(self.url and self.anon_key)
        self.table = "forge_memory"

    @property
    def available(self):
        return self._service_ok or self._anon_ok

    @property
    def mode(self):
        if self._service_ok:
            return "service (read/write)"
        if self._anon_ok:
            return "anon (read-only)"
        return "offline"

    def _headers(self, use_service: bool = False):
        key = self.service_key if use_service else self.anon_key
        return {
            "Content-Type": "application/json",
            "apikey": key,
            "Authorization": f"Bearer {key}",
        }

    def remember(self, key: str, value: str, project: str = ""):
        if not self._service_ok:
            return
        try:
            data = json.dumps({
                "key": key,
                "value": value,
                "project_path": project,
            }).encode()
            req = urllib.request.Request(
                f"{self.url}/rest/v1/{self.table}",
                data=data,
                headers=self._headers(use_service=True),
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                pass
        except Exception:
            pass

    def recall(self, query: str = "", limit: int = 5) -> list:
        if not self.available:
            return []
        try:
            use_service = self._service_ok
            url = (f"{self.url}/rest/v1/{self.table}"
                   f"?select=key,value,project_path,created_at"
                   f"&order=created_at.desc&limit={limit}")
            if query:
                import urllib.parse
                encoded = urllib.parse.quote(f"%{query}%")
                url += f"&or=(key.ilike.{encoded},value.ilike.{encoded})"
            req = urllib.request.Request(
                url, headers=self._headers(use_service=use_service)
            )
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            return [
                {
                    "key": r["key"],
                    "value": r["value"],
                    "project": r.get("project_path", ""),
                    "created_at": r.get("created_at", ""),
                }
                for r in data
            ]
        except Exception:
            return []
