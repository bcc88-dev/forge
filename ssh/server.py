"""SSH server - accept connections, validate license keys, spawn agent."""

import asyncio
import asyncssh
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forge.config import load_config
from ssh.auth import validate_license_key
from ssh.session import CLIDESession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clide-sshd")


class CLIDESSHServer(asyncssh.SSHServer):
    def __init__(self):
        self._user_id = None
        self._email = None

    def begin_auth(self, username: str) -> bool:
        return True

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        result = validate_license_key(password)
        if result.get("valid"):
            self._user_id = result.get("user_id")
            self._email = result.get("email", username)
            logger.info(f"Authenticated user: {self._email}")
            return True
        logger.warning(f"Failed auth attempt for {username}")
        return False

    def session_requested(self):
        return CLIDESession(self._user_id, self._email)


async def start_server(host: str = "0.0.0.0", port: int = 2222):
    cfg = load_config()
    host_key_path = cfg.get(
        "ssh_host_key", str(Path.home() / ".ssh" / "clide_host_key")
    )

    host_key = asyncssh.import_private_key(
        await _get_or_create_host_key(host_key_path)
    )

    server = await asyncssh.create_server(
        CLIDESSHServer,
        host,
        port,
        server_host_keys=[host_key],
    )

    logger.info(f"CLIDE SSH server listening on {host}:{port}")
    await server.wait_closed()


async def _get_or_create_host_key(path: str):
    key_path = Path(path)
    if key_path.exists():
        logger.info(f"Using existing host key: {path}")
        return key_path.read_text()

    logger.info(f"Generating new host key: {path}")
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key = asyncssh.generate_private_key("ssh-rsa")
    key_path.write_text(key.export_private_key("openssh") or "")
    key_path.chmod(0o600)
    return key.export_private_key("openssh") or ""


def main():
    host = os.getenv("CLIDE_SSH_HOST", "0.0.0.0")
    port = int(os.getenv("CLIDE_SSH_PORT", "2222"))

    try:
        asyncio.run(start_server(host, port))
    except KeyboardInterrupt:
        logger.info("Server shutting down")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
