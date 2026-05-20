"""Supabase client for auth and data operations."""

import json
import urllib.request
import urllib.error
from ..config import load_config

class SupabaseClient:
    def __init__(self):
        cfg = load_config()
        self.url = cfg.get("supabase_url", "")
        self.anon_key = cfg.get("supabase_anon_key", "")
        self.service_key = cfg.get("supabase_service_key", "")
    
    def _headers(self, use_service: bool = False):
        key = self.service_key if use_service else self.anon_key
        return {
            "Content-Type": "application/json",
            "apikey": key,
            "Authorization": f"Bearer {key}"
        }
    
    def sign_up(self, email: str, password: str) -> dict:
        try:
            data = json.dumps({"email": email, "password": password}).encode()
            req = urllib.request.Request(
                f"{self.url}/auth/v1/signup",
                data=data,
                headers=self._headers(),
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=15)
            return {"success": True, "data": json.loads(resp.read())}
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            return {"success": False, "error": body}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def sign_in(self, email: str, password: str) -> dict:
        try:
            data = json.dumps({"email": email, "password": password}).encode()
            req = urllib.request.Request(
                f"{self.url}/auth/v1/token?grant_type=password",
                data=data,
                headers=self._headers(),
                method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=15)
            return {"success": True, "data": json.loads(resp.read())}
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            return {"success": False, "error": body}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_connection(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{self.url}/rest/v1/",
                headers=self._headers(use_service=True)
            )
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status == 200
        except:
            return False
