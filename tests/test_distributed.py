from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from alice_os import distributed as module
from alice_os.api import create_app
from alice_os.distributed import (
    DistributedSettings,
    DistributedStore,
    matches_settings,
    probe_devices,
)
from alice_os.runtimes import RuntimeOperationError


@pytest.mark.parametrize("endpoint", ["10.0.0.2:50052", "0.0.0.0:50052", "localhost:50052", "127.0.0.1:0", "127.0.0.1:99999", "127.0.0.1:50052 --flag"])
def test_only_loopback_tunnels_are_accepted(endpoint):
    with pytest.raises(ValidationError):
        DistributedSettings(enabled=True, endpoints=[endpoint])


def test_settings_require_unique_workers_and_survive_restart(tmp_path):
    with pytest.raises(ValidationError):
        DistributedSettings(enabled=True)
    with pytest.raises(ValidationError):
        DistributedSettings(endpoints=["127.0.0.1:50053", "127.0.0.1:50053"])
    store = DistributedStore(tmp_path)
    assert store.get().arguments() == []
    settings = DistributedSettings(enabled=True, endpoints=["127.0.0.1:50053"])
    store.save(settings)
    assert DistributedStore(tmp_path).get() == settings
    assert matches_settings(settings.arguments(), settings)
    assert not matches_settings([], settings)
    assert not matches_settings(settings.arguments(), DistributedSettings())


@pytest.mark.parametrize("output, code, valid", [
    ("Available devices:\n CUDA0: Local GPU\n RPC0: 127.0.0.1:50053 (8000 MiB)\n", 0, True),
    ("Could not connect to 127.0.0.1:50053\n CUDA0: Local GPU", 0, False),
    ("RPC0: 127.0.0.1:500530 (8000 MiB)", 0, False),
    ("Incompatible protocol", 1, False),
])
async def test_probe_requires_reported_remote_devices(tmp_path, monkeypatch, output, code, valid):
    executable = tmp_path / "server"
    executable.touch()
    process = Mock(returncode=code)
    process.communicate = AsyncMock(return_value=(output.encode(), None))
    spawn = AsyncMock(return_value=process)
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", spawn)
    settings = DistributedSettings(enabled=True, endpoints=["127.0.0.1:50053"])
    if valid:
        assert await probe_devices(executable, settings) == output
    else:
        with pytest.raises(RuntimeOperationError):
            await probe_devices(executable, settings)
    assert spawn.call_args.args[-1] == "--list-devices"
    assert spawn.call_args.args[1:3] == ("--rpc", "127.0.0.1:50053")


def test_distributed_settings_require_browser_auth(tmp_path, monkeypatch):
    monkeypatch.delenv("ALICE_NETWORK_MODE", raising=False)
    app = create_app(tmp_path)
    with TestClient(app) as client:
        assert client.get("/api/distributed").status_code == 401
        client.get("/")
        assert client.get("/api/distributed").json() == {"enabled": False, "endpoints": [], "worker_ids": []}
        response = client.put("/api/distributed", json={"enabled": True, "endpoints": ["127.0.0.1:50053"]})
        assert response.status_code == 200
        assert response.json()["reload_required"]
        assert client.put("/api/distributed", json={"enabled": True, "endpoints": ["10.0.0.2:50052"]}).status_code == 422
