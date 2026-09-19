"""Own a loopback-only God’s Eye View process without touching other services."""
from __future__ import annotations

import asyncio
import ipaddress
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import psutil

from .paths import bundled, resource_root

REVISION = "a65d9d85f1faa06ae7df235d7fa8a29b026b7a5b"
PORT = 4173


def is_host_client(host: str) -> bool:
    """Recognize this PC even when its browser connects through its LAN hostname."""
    try:
        address = ipaddress.ip_address(host.split("%", 1)[0])
        address = getattr(address, "ipv4_mapped", None) or address
    except ValueError:
        return False
    if address.is_loopback:
        return True
    if address.is_unspecified:
        return False
    try:
        for entries in psutil.net_if_addrs().values():
            for entry in entries:
                if entry.family not in {socket.AF_INET, socket.AF_INET6}:
                    continue
                try:
                    local = ipaddress.ip_address(entry.address.split("%", 1)[0])
                    local = getattr(local, "ipv4_mapped", None) or local
                    if address == local:
                        return True
                except ValueError:
                    continue
    except (OSError, psutil.Error):
        pass
    return False


class WorldView:
    def __init__(self, data_dir: Path, root: Path | None = None) -> None:
        base = Path(sys.executable).parent if bundled() else resource_root()
        self.root = root or Path(os.environ.get("ALICE_GODS_EYE_HOME", str(base / "tools/gods-eye-view")))
        self.node = str(self.root.parent / "node-v24.14.0-win-x64/node.exe")
        if not Path(self.node).is_file():
            self.node = shutil.which("node") or ""
        self.log = data_dir / "logs/gods-eye-view.log"
        self.process: subprocess.Popen | None = None
        self.ready = False
        self.lock = asyncio.Lock()

    def status(self) -> dict:
        running = self.process is not None and self.process.poll() is None
        installed = bool(self.node and (self.root / "node_modules/vite/bin/vite.js").is_file())
        return {"installed": installed, "running": running, "ready": running and self.ready,
                "url": f"http://127.0.0.1:{PORT}/" if running and self.ready else None,
                "revision": REVISION, "log_path": str(self.log),
                "setup": "powershell -ExecutionPolicy Bypass -File scripts/setup-gods-eye.ps1"}

    async def start(self) -> dict:
        async with self.lock:
            if self.status()["ready"]:
                return self.status()
            if not self.status()["installed"]:
                raise RuntimeError("Run scripts/setup-gods-eye.ps1 on the Alice host first.")
            with socket.socket() as probe:
                try:
                    probe.bind(("127.0.0.1", PORT))
                except OSError as error:
                    raise RuntimeError("Port 4173 is occupied. Stop that service before starting the globe; Alice will not terminate an unrelated process.") from error
            self.log.parent.mkdir(parents=True, exist_ok=True)
            # Do not pass Alice's model credentials or network tokens to a separate app.
            allowed = {"path", "systemroot", "windir", "comspec", "pathext", "temp", "tmp", "home", "userprofile", "appdata", "localappdata", "programdata"}
            env = {k: v for k, v in os.environ.items() if k.lower() in allowed}
            env.update({"HOST": "127.0.0.1", "PORT": str(PORT), "BROWSER": "none"})
            with self.log.open("ab") as log:
                self.process = subprocess.Popen(
                    [self.node, "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", str(PORT), "--strictPort"],
                    cwd=self.root, env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            try:
                async with httpx.AsyncClient(timeout=2, trust_env=False) as client:
                    deadline = time.monotonic() + 30
                    while time.monotonic() < deadline:
                        if self.process.poll() is not None:
                            raise RuntimeError("The globe stopped during startup. Check the God’s Eye log on the Alice host.")
                        try:
                            response = await client.get(f"http://127.0.0.1:{PORT}/")
                            if response.status_code == 200 and "<title>God's Eye View</title>" in response.text and self.process.poll() is None:
                                self.ready = True
                                return self.status()
                        except httpx.HTTPError:
                            pass
                        await asyncio.sleep(0.25)
                raise RuntimeError("Globe startup timed out. Check the God’s Eye log on the Alice host.")
            except BaseException:
                await asyncio.to_thread(self._stop)
                raise

    def _stop(self) -> None:
        process, self.process = self.process, None
        self.ready = False
        if process is None or process.poll() is not None:
            return
        try:
            children = psutil.Process(process.pid).children(recursive=True)
        except psutil.Error:
            children = []
        process.terminate()
        for child in children:
            try:
                child.terminate()
            except psutil.Error:
                pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        _, alive = psutil.wait_procs(children, timeout=2)
        for child in alive:
            try:
                child.kill()
            except psutil.Error:
                pass

    async def stop(self) -> dict:
        async with self.lock:
            await asyncio.to_thread(self._stop)
            return self.status()
