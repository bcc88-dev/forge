"""License key authentication via Supabase."""

import json
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from forge.config import load_config


def validate_license_key(license_key: str) -> dict:
    """Check if a license key is valid in Supabase forge_licenses table."""
    cfg = load_config()
    url = cfg.get("supabase_url", "")
    key = cfg.get("supabase_service_key", "")
    if not url or not key:
        return {"valid": False, "error": "Supabase not configured"}

    headers = {
        "Content-Type": "application/json",
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

    try:
        encoded_key = urllib.parse.quote(license_key)
        req = urllib.request.Request(
            f"{url}/rest/v1/forge_licenses"
            f"?license_key=eq.{encoded_key}"
            f"&select=*&limit=1",
            headers=headers,
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())

        if not data:
            return {"valid": False, "error": "Invalid license key"}

        record = data[0]
        if record.get("status") == "active":
            return {
                "valid": True,
                "user_id": record.get("user_id"),
                "email": record.get("email", ""),
            }
        return {"valid": False, "error": f"License status: {record.get('status', 'unknown')}"}

    except urllib.error.HTTPError as e:
        return {"valid": False, "error": f"Supabase error: {e.code}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}
