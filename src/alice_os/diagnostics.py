from __future__ import annotations

import asyncio
import csv
import math
import os
import shutil
import subprocess
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import psutil

from .config import ConfigStore
from .models import ProviderProfile

PROVIDER_PROBE_TIMEOUT = 1.5
PROVIDER_CACHE_SECONDS = 10


def gpu_metrics() -> dict[str, Any]:
    """Optional NVIDIA driver counters; missing sensors are never reported as zero."""
    unavailable = {"devices": [], "message": "GPU sensors unavailable (NVIDIA driver telemetry required)."}
    executable = shutil.which("nvidia-smi")
    if not executable:
        return unavailable
    try:
        result = subprocess.run(
            [executable, "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True, timeout=1.5,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.SubprocessError):
        return unavailable

    def number(value: str, multiplier: int = 1) -> float | None:
        try:
            parsed = float(value) * multiplier
            return parsed if math.isfinite(parsed) and parsed >= 0 else None
        except ValueError:
            return None

    devices = []
    for row in csv.reader(result.stdout.splitlines(), skipinitialspace=True):
        if len(row) != 6:
            continue
        name, usage, used, total, temperature, power = row
        devices.append({
            "name": name.strip(), "used_percent": number(usage),
            "memory_used_bytes": number(used, 1024 ** 2), "memory_total_bytes": number(total, 1024 ** 2),
            "temperature_c": number(temperature), "power_watts": number(power),
        })
    return {"devices": devices, "message": "NVIDIA driver telemetry"} if devices else unavailable


def system_metrics(data_dir: Path) -> dict[str, Any]:
    """Local counters plus one time-bounded GPU probe; no recursive disk scans."""
    result: dict[str, Any] = {"process": None, "memory": None, "disk": None, "cpu": None, "drives": []}
    try:
        result["cpu"] = {
            "used_percent": psutil.cpu_percent(interval=0.1),
            "logical_cores": psutil.cpu_count(),
            "physical_cores": psutil.cpu_count(logical=False),
        }
    except (psutil.Error, OSError):
        pass
    try:
        process = psutil.Process()
        result["process"] = {
            "pid": process.pid,
            "rss_bytes": process.memory_info().rss,
            "threads": process.num_threads(),
        }
    except (psutil.Error, OSError):
        pass
    try:
        memory = psutil.virtual_memory()
        result["memory"] = {
            "total_bytes": memory.total,
            "available_bytes": memory.available,
            "used_percent": memory.percent,
        }
    except (psutil.Error, OSError):
        pass
    try:
        disk = psutil.disk_usage(str(data_dir))
        result["disk"] = {
            "total_bytes": disk.total,
            "free_bytes": disk.free,
            "used_percent": disk.percent,
        }
    except (psutil.Error, OSError):
        pass
    try:
        partitions = psutil.disk_partitions(all=False)
    except (psutil.Error, OSError):
        partitions = []
    seen = set()
    for partition in partitions:
        if not partition.fstype or any(kind in partition.opts.lower() for kind in ("cdrom", "remote")) or partition.fstype.lower() in {"nfs", "nfs4", "cifs", "smbfs"}:
            continue
        if partition.mountpoint in seen:
            continue
        seen.add(partition.mountpoint)
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except (psutil.Error, OSError):
            continue
        result["drives"].append({
            "mount": partition.mountpoint, "filesystem": partition.fstype,
            "total_bytes": usage.total, "free_bytes": usage.free, "used_percent": usage.percent,
        })
    result["gpu"] = gpu_metrics()
    return result


class SystemDiagnostics:
    def __init__(self) -> None:
        self.started_at = time.monotonic()
        self._provider_cache: tuple[str, float, dict[str, Any]] | None = None
        self._probe_lock = asyncio.Lock()
        self._metrics_lock = asyncio.Lock()
        self._metrics_cache: tuple[float, dict[str, Any]] | None = None

    async def metrics(self, data_dir: Path) -> dict[str, Any]:
        async with self._metrics_lock:
            if self._metrics_cache and time.monotonic() < self._metrics_cache[0]:
                return self._metrics_cache[1]
            metrics = await asyncio.to_thread(system_metrics, data_dir)
            self._metrics_cache = (time.monotonic() + 5, metrics)
            return metrics

    async def provider_status(
        self,
        config: ConfigStore,
        list_models: Callable[[ProviderProfile], Awaitable[list[str]]],
    ) -> dict[str, Any]:
        settings = config.get()
        try:
            profile = config.get_provider(settings.active_provider_id)
        except KeyError:
            return {
                "id": settings.active_provider_id, "name": "No provider", "kind": "",
                "model": settings.active_model, "reachable": None, "ready": False,
                "status": "unconfigured", "detail": "Choose a provider in Settings.",
                "model_count": None,
            }
        model = settings.active_model or profile.default_model
        result: dict[str, Any] = {
            "id": profile.id, "name": profile.name, "kind": profile.kind, "model": model,
            "reachable": None, "ready": False, "status": "unavailable", "detail": "",
            "model_count": None,
        }
        if profile.api_key_env and not os.environ.get(profile.api_key_env):
            result.update(status="credentials_required", detail="The provider's API key environment variable is not set. Configure it and restart Alice.")
            return result
        key = f"{profile.model_dump_json()}:{model}"
        async with self._probe_lock:
            if self._provider_cache:
                cached_key, expires_at, cached = self._provider_cache
                if key == cached_key and time.monotonic() < expires_at:
                    return dict(cached)
            try:
                models = await asyncio.wait_for(list_models(profile), PROVIDER_PROBE_TIMEOUT)
            except TimeoutError:
                result.update(reachable=False, detail="The provider did not respond in time. Check that its runtime is running and reachable.")
            except Exception:
                # Provider exceptions may contain remote URLs or credentials; don't echo them.
                result.update(reachable=False, detail="Could not reach the provider's model list. Check its runtime, connection, and credentials.")
            else:
                result.update(reachable=True, model_count=len(models))
                if not model:
                    result.update(status="model_required", detail="Select a model to enable the assistant.")
                elif model not in models:
                    result.update(status="model_unavailable", detail="The selected model is not advertised by this provider. Load it or select an available model.")
                else:
                    result.update(ready=True, status="ready", detail="Provider reachable; selected model is advertised. Generation has not been tested.")
            self._provider_cache = (key, time.monotonic() + PROVIDER_CACHE_SECONDS, dict(result))
            return result

    async def snapshot(self, *, config: ConfigStore, runs: Any, list_models: Any, version: str) -> dict[str, Any]:
        metrics, provider = await asyncio.gather(
            self.metrics(config.data_dir),
            self.provider_status(config, list_models),
        )
        runs.prune()
        alerts: list[dict[str, str]] = []
        if not provider["ready"]:
            alerts.append({"id": "provider", "severity": "warning", "message": provider["detail"]})
        memory, disk = metrics["memory"], metrics["disk"]
        if memory and memory["used_percent"] >= 90:
            alerts.append({"id": "memory", "severity": "warning", "message": "System memory is nearly full. Close unused applications or unload a model."})
        if disk and (disk["used_percent"] >= 95 or disk["free_bytes"] < 1024 ** 3):
            alerts.append({"id": "disk", "severity": "warning", "message": "The Alice data drive is low on free space. Free space before downloading more models."})
        return {
            "status": "attention" if alerts else "ready",
            "version": version,
            "uptime_seconds": round(max(0, time.monotonic() - self.started_at), 1),
            "active_runs": sum(not run.terminal for run in runs.runs.values()),
            "pending_approvals": sum(not future.done() for run in runs.runs.values() for future in run.approval_futures.values()),
            "retained_runs": len(runs.runs),
            **metrics,
            "provider": provider,
            "alerts": alerts,
        }
