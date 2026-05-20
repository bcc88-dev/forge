"""SSH session handler - spawns clide agent in PTY."""

import asyncio
import asyncssh
from pathlib import Path


class CLIDESession(asyncssh.SSHServerSession):
    def __init__(self, user_id: str, email: str):
        self._user_id = user_id
        self._email = email
        self._process = None

    def connection_made(self, chan):
        self._chan = chan

    def shell_requested(self):
        return True

    def exec_requested(self, command: str):
        return False

    def start_shell(self):
        asyncio.ensure_future(self._run_agent())

    async def _run_agent(self):
        try:
            self._process = await asyncio.create_subprocess_exec(
                "clide",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={
                    **__import__("os").environ,
                    "CLIDE_SSH_USER": self._email,
                },
            )

            async def read_stdout():
                while True:
                    line = await self._process.stdout.readline()
                    if not line:
                        break
                    self._chan.write(line.decode("utf-8", errors="replace"))

            async def write_stdin():
                while True:
                    data = await self._chan.read(1024)
                    if not data:
                        break
                    self._process.stdin.write(data.encode("utf-8", errors="replace"))
                    await self._process.stdin.drain()

            await asyncio.gather(read_stdout(), write_stdin())

        except FileNotFoundError:
            self._chan.write("Error: clide command not found.\r\n")
            self._chan.write("Install: pip install clide-cli\r\n")
        except Exception as e:
            self._chan.write(f"Error starting agent: {e}\r\n")
        finally:
            self._chan.exit(0)

    def closed(self):
        if self._process and self._process.returncode is None:
            self._process.terminate()
