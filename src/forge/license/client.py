"""License key management - local validation with offline cache."""

import json
import time
import os
import urllib.request
import urllib.error
from pathlib import Path
from ..config import CONFIG_DIR, LICENSE_FILE, ensure_dir

TRIAL_DURATION_DAYS = 7
OFFLINE_GRACE_DAYS = 7
VALIDATION_URL = "https://forge-cli.vercel.app/api/license/validate"

class LicenseClient:
    def __init__(self):
        ensure_dir()
    
    def _load(self) -> dict:
        try:
            if LICENSE_FILE.exists():
                return json.loads(LICENSE_FILE.read_text())
        except:
            pass
        return {}
    
    def _save(self, data: dict):
        LICENSE_FILE.write_text(json.dumps(data, indent=2))
        os.chmod(LICENSE_FILE, 0o600)
    
    def is_trial_active(self) -> bool:
        lic = self._load()
        if "trial_start" in lic:
            elapsed = time.time() - lic["trial_start"]
            return elapsed < TRIAL_DURATION_DAYS * 86400
        return True
    
    def remaining_trial_days(self) -> int:
        lic = self._load()
        if "trial_start" in lic:
            elapsed = time.time() - lic["trial_start"]
            remaining = TRIAL_DURATION_DAYS - (elapsed / 86400)
            return max(0, int(remaining))
        return TRIAL_DURATION_DAYS
    
    def start_trial(self):
        lic = self._load()
        if "trial_start" not in lic:
            lic["trial_start"] = time.time()
            self._save(lic)
    
    def set_license_key(self, key: str):
        lic = self._load()
        lic["key"] = key
        lic["cached_at"] = time.time()
        self._save(lic)
    
    def validate(self) -> dict:
        lic = self._load()
        
        if "key" in lic and lic.get("key"):
            if "cached_at" in lic:
                age = time.time() - lic["cached_at"]
                if age < OFFLINE_GRACE_DAYS * 86400:
                    return {"valid": True, "source": "cache", "key": lic["key"]}
            
            try:
                data = json.dumps({"key": lic["key"]}).encode()
                req = urllib.request.Request(
                    VALIDATION_URL,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                resp = urllib.request.urlopen(req, timeout=10)
                result = json.loads(resp.read())
                if result.get("valid"):
                    lic["cached_at"] = time.time()
                    self._save(lic)
                    return {"valid": True, "source": "server", "key": lic["key"]}
            except:
                if "cached_at" in lic:
                    return {"valid": True, "source": "cache", "key": lic["key"], "note": "offline"}
        
        if self.is_trial_active():
            remaining = self.remaining_trial_days()
            return {"valid": True, "source": "trial", "days_remaining": remaining}
        
        return {"valid": False, "source": "none"}
    
    def is_valid(self) -> bool:
        return self.validate().get("valid", False)
