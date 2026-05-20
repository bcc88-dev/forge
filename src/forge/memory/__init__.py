"""Memory system - local SQLite + Supabase vector memory."""

from .local import LocalMemory
from .supabase import SupabaseMemory


class Memory:
    def __init__(self):
        self.local = LocalMemory()
        self.supabase = SupabaseMemory()
        self._status_printed = False

    @property
    def supabase_mode(self):
        return self.supabase.mode

    def remember(self, key: str, value: str, project: str = "") -> str:
        self.local.remember(key, value, project)
        if self.supabase.available:
            try:
                self.supabase.remember(key, value, project)
            except Exception:
                pass
        elif not self._status_printed:
            self._status_printed = True
        return f"Remembered: {key}"

    def recall(self, query: str = "", limit: int = 5) -> list:
        results = self.local.recall(query, limit)
        if self.supabase.available:
            try:
                remote = self.supabase.recall(query, limit)
                seen = set(r["key"] for r in results)
                for r in remote:
                    if r["key"] not in seen:
                        results.append(r)
                        seen.add(r["key"])
            except Exception:
                pass
        elif not self._status_printed:
            self._status_printed = True
        return results

    def history(self, limit: int = 10) -> list:
        return self.local.history(limit)

    def show_status(self):
        print(f"  Memory: local (always) + Supabase {self.supabase.mode}")
