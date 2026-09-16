from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import psutil

from alice_os.config import ConfigStore
from alice_os.diagnostics import SystemDiagnostics, system_metrics
from alice_os.models import ProviderProfile


async def test_provider_probe_is_shared_cached_and_invalidated_when_model_changes(tmp_path: Path) -> None:
    config = ConfigStore(tmp_path / "data")
    config.set_active_model("test-model")
    diagnostics = SystemDiagnostics()
    calls = 0

    async def models(profile):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return ["test-model"]

    statuses = await asyncio.gather(*(diagnostics.provider_status(config, models) for _ in range(5)))
    assert calls == 1
    assert all(status["ready"] and status["reachable"] for status in statuses)
    assert statuses[0]["status"] == "ready"
    config.set_active_model("missing")
    missing = await diagnostics.provider_status(config, models)
    assert calls == 2
    assert missing["reachable"] and not missing["ready"]
    assert missing["status"] == "model_unavailable"


async def test_slow_provider_probe_is_cancelled_with_actionable_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("alice_os.diagnostics.PROVIDER_PROBE_TIMEOUT", 0.01)
    config = ConfigStore(tmp_path / "data")
    cancelled = False

    async def models(profile):
        nonlocal cancelled
        try:
            await asyncio.Event().wait()
        finally:
            cancelled = True

    async with asyncio.timeout(1):
        result = await SystemDiagnostics().provider_status(config, models)
    assert cancelled
    assert result["status"] == "unavailable"
    assert result["reachable"] is False
    assert "runtime" in result["detail"]


async def test_missing_provider_credentials_do_not_make_network_requests(tmp_path: Path, monkeypatch) -> None:
    config = ConfigStore(tmp_path / "data")
    config.upsert_provider(ProviderProfile(id="private", name="Private", kind="openai", base_url="https://example.invalid/v1", api_key_env="ALICE_TEST_MISSING_KEY"))
    config.set_active("private")
    monkeypatch.delenv("ALICE_TEST_MISSING_KEY", raising=False)

    async def models(profile):
        raise AssertionError("A missing key must prevent the probe")

    result = await SystemDiagnostics().provider_status(config, models)
    assert result["status"] == "credentials_required"
    assert result["reachable"] is None


def test_unavailable_system_counters_are_null(monkeypatch, tmp_path: Path) -> None:
    def unavailable(*args, **kwargs):
        raise psutil.AccessDenied()

    monkeypatch.setattr("alice_os.diagnostics.psutil.Process", unavailable)
    monkeypatch.setattr("alice_os.diagnostics.psutil.virtual_memory", unavailable)
    monkeypatch.setattr("alice_os.diagnostics.psutil.disk_usage", unavailable)
    monkeypatch.setattr("alice_os.diagnostics.psutil.cpu_percent", unavailable)
    monkeypatch.setattr("alice_os.diagnostics.psutil.disk_partitions", unavailable)
    monkeypatch.setattr("alice_os.diagnostics.gpu_metrics", lambda: {"devices": []})
    assert system_metrics(tmp_path) == {"process": None, "memory": None, "disk": None, "cpu": None, "drives": [], "gpu": {"devices": []}}


def test_gpu_metrics_preserves_multiple_devices_and_unsupported_sensors(monkeypatch):
    from alice_os.diagnostics import gpu_metrics

    monkeypatch.setattr("alice_os.diagnostics.shutil.which", lambda _: "nvidia-smi")

    def run(command, **kwargs):
        assert kwargs["timeout"] == 1.5
        assert kwargs["capture_output"]
        return SimpleNamespace(stdout='"NVIDIA GPU, One", 0, 1024, 8192, 42, 55.5\nSecond GPU, [N/A], [N/A], 4096, [N/A], NaN\n')

    monkeypatch.setattr("alice_os.diagnostics.subprocess.run", run)
    first, second = gpu_metrics()["devices"]
    assert first["name"] == "NVIDIA GPU, One"
    assert first["used_percent"] == 0
    assert first["memory_total_bytes"] == 8 * 1024 ** 3
    assert first["temperature_c"] == 42
    assert second["used_percent"] is second["power_watts"] is second["memory_used_bytes"] is None


def test_gpu_timeout_reports_unavailable(monkeypatch):
    import subprocess

    from alice_os.diagnostics import gpu_metrics

    monkeypatch.setattr("alice_os.diagnostics.shutil.which", lambda _: "nvidia-smi")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("nvidia-smi", 1.5)

    monkeypatch.setattr("alice_os.diagnostics.subprocess.run", timeout)
    assert gpu_metrics()["devices"] == []


def test_drive_probe_skips_remote_duplicate_and_unreadable_volumes(monkeypatch, tmp_path):
    partitions = [SimpleNamespace(mountpoint=mount, fstype="NTFS", opts=opts) for mount, opts in
                  [("C:/", "fixed"), ("C:/", "fixed"), ("Z:/", "remote"), ("D:/", "fixed")]]
    monkeypatch.setattr("alice_os.diagnostics.psutil.disk_partitions", lambda **_: partitions)
    monkeypatch.setattr("alice_os.diagnostics.gpu_metrics", lambda: {"devices": []})

    def usage(mount):
        assert mount != "Z:/"
        if mount == "D:/":
            raise PermissionError()
        return SimpleNamespace(total=100, free=40, percent=60)

    monkeypatch.setattr("alice_os.diagnostics.psutil.disk_usage", usage)
    result = system_metrics(tmp_path)
    assert [drive["mount"] for drive in result["drives"]] == ["C:/"]
    assert result["drives"][0]["free_bytes"] == 40


async def test_metrics_probe_shared_and_cached(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("alice_os.diagnostics.system_metrics", lambda path: calls.append(path) or {"cpu": None})
    diagnostics = SystemDiagnostics()
    results = await asyncio.gather(*(diagnostics.metrics(tmp_path) for _ in range(5)))
    assert calls == [tmp_path]
    assert all(result == {"cpu": None} for result in results)


async def test_snapshot_reports_pressure_and_pending_approvals(tmp_path: Path, monkeypatch) -> None:
    config = ConfigStore(tmp_path / "data")
    config.set_active_model("test-model")
    monkeypatch.setattr("alice_os.diagnostics.system_metrics", lambda _: {
        "process": {"pid": 123, "rss_bytes": 1234, "threads": 2},
        "memory": {"total_bytes": 100, "available_bytes": 5, "used_percent": 95},
        "disk": {"total_bytes": 100, "free_bytes": 1, "used_percent": 99},
    })

    async def models(profile):
        return ["test-model"]

    approval = asyncio.get_running_loop().create_future()
    run = SimpleNamespace(terminal=False, approval_futures={"write": approval})
    manager = SimpleNamespace(runs={"run": run}, prune=lambda: None)
    status = await SystemDiagnostics().snapshot(config=config, runs=manager, list_models=models, version="test")
    assert status["status"] == "attention"
    assert status["active_runs"] == status["pending_approvals"] == 1
    assert {alert["id"] for alert in status["alerts"]} == {"disk", "memory"}
    assert status["uptime_seconds"] >= 0
    approval.cancel()
