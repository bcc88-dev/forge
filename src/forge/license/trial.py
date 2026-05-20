"""Trial management utilities."""

from .client import LicenseClient

license = LicenseClient()

def check():
    if license.is_trial_active():
        days = license.remaining_trial_days()
        return {"status": "trial", "days_remaining": days}
    if license.is_valid():
        return {"status": "licensed"}
    return {"status": "expired"}
