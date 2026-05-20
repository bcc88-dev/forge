"""Auth utilities for user signup/login flows."""

from .client import SupabaseClient

_client = SupabaseClient()

def signup(email: str, password: str) -> dict:
    return _client.sign_up(email, password)

def login(email: str, password: str) -> dict:
    return _client.sign_in(email, password)

def test() -> bool:
    return _client.test_connection()
