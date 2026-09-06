"""Experimental llama.cpp model splitting over authenticated loopback tunnels."""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

from .runtimes import RuntimeOperationError


class DistributedSettings(BaseModel):
    enabled: bool = False
    endpoints: list[str] = Field(default_factory=list, max_length=16)
    worker_ids: list[str] = Field(default_factory=list, max_length=16)

    @field_validator("worker_ids")
    @classmethod
    def validate_workers(cls, values):
        if len(set(values)) != len(values) or any(not re.fullmatch(r"cluster_[a-f0-9]{32}", value) for value in values):
            raise ValueError("Select unique paired GPU workers")
        return values

    @field_validator("endpoints")
    @classmethod
    def validate_endpoints(cls, endpoints):
        result = []
        for endpoint in endpoints:
            host, separator, port = endpoint.strip().rpartition(":")
            if host != "127.0.0.1" or not separator or not port.isdigit() or not 1 <= int(port) <= 65535:
                raise ValueError("Use SSH tunnel addresses such as 127.0.0.1:50053; raw LAN RPC is disabled")
            normalized = f"127.0.0.1:{int(port)}"
            if normalized in result:
                raise ValueError("Each tunnel endpoint must be unique")
            result.append(normalized)
        return result

    @model_validator(mode="after")
    def require_endpoints(self):
        if self.enabled and not (self.endpoints or self.worker_ids):
            raise ValueError("Add at least one GPU worker tunnel before enabling model splitting")
        return self

    def arguments(self):
        if self.enabled and self.worker_ids:
            raise RuntimeOperationError("Load this model from Alice so it can connect the selected GPU workers")
        return ["--rpc", ",".join(self.endpoints), "--split-mode", "layer"] if self.enabled else []


class DistributedStore:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "distributed.json"

    def get(self) -> DistributedSettings:
        if not self.path.exists():
            return DistributedSettings()
        return DistributedSettings.model_validate_json(self.path.read_text("utf-8"))

    def save(self, settings: DistributedSettings):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(self.path)


async def probe_devices(executable: Path, settings: DistributedSettings) -> str:
    """Require a successful native RPC handshake before stopping a loaded model."""
    if not executable.is_file():
        raise RuntimeOperationError("The bundled llama.cpp runtime is missing")
    process = await asyncio.create_subprocess_exec(
        str(executable), *settings.arguments(), "--list-devices",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout=20)
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise
    text = output.decode("utf-8", errors="replace")[-16000:]
    if process.returncode != 0:
        raise RuntimeOperationError("GPU discovery failed. Check the worker runtime, SSH tunnels, and matching llama.cpp builds.\n" + text)
    # llama.cpp may log a failed remote connection yet exit successfully.
    if settings.enabled and not all(
        re.search(r"^\s*RPC\S*:\s*" + re.escape(endpoint) + r"(?=\s|$)", text, re.MULTILINE)
        for endpoint in settings.endpoints
    ):
        raise RuntimeOperationError("Not all RPC workers reported devices. Check the SSH tunnels and runtime versions.\n" + text)
    return text


def matches_settings(arguments: list[str], settings: DistributedSettings) -> bool:
    def value(flag):
        try:
            return arguments[arguments.index(flag) + 1]
        except (ValueError, IndexError):
            return ""
    if not settings.enabled:
        return not value("--rpc")
    return value("--rpc") == ",".join(settings.endpoints) and value("--split-mode") == "layer"


def main():
    import argparse

    from .config import default_data_dir

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arguments", action="store_true")
    parser.add_argument("--lines", action="store_true")
    parser.add_argument("--startup", action="store_true")
    args = parser.parse_args()
    settings = DistributedStore(default_data_dir()).get()
    if args.startup:
        managed = settings.enabled and bool(settings.worker_ids)
        print(json.dumps({"defer": managed, "arguments": [] if managed else settings.arguments()}))
    if args.arguments:
        print(json.dumps(DistributedStore(default_data_dir()).get().arguments()))
    if args.lines:
        if settings.enabled and settings.worker_ids:
            print("ALICE_MANAGED_GPU_WORKERS")
            return
        for argument in settings.arguments():
            print(argument)


if __name__ == "__main__":
    main()
