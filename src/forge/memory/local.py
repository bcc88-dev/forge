"""Local SQLite memory cache."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from ..config import CONFIG_DIR

class LocalMemory:
    def __init__(self):
        self.db_path = CONFIG_DIR / "memory.db"
        self._init_db()
    
    def _init_db(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                project TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project)
        """)
        conn.commit()
        conn.close()
    
    def remember(self, key: str, value: str, project: str = ""):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO memories (key, value, project) VALUES (?, ?, ?)",
            (key, value, project)
        )
        conn.commit()
        conn.close()
    
    def recall(self, query: str = "", limit: int = 5) -> list:
        conn = sqlite3.connect(str(self.db_path))
        if query:
            rows = conn.execute(
                "SELECT key, value, project, created_at FROM memories WHERE key LIKE ? OR value LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{query}%", f"%{query}%", limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT key, value, project, created_at FROM memories ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        conn.close()
        return [
            {"key": r[0], "value": r[1], "project": r[2], "created_at": r[3]}
            for r in rows
        ]
    
    def history(self, limit: int = 10) -> list:
        return self.recall("", limit)
