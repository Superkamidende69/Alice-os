from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from alice_os import model_manager as module
from alice_os.config import ConfigStore
from alice_os.distributed import DistributedSettings
from alice_os.model_manager import ModelManager, inventory
from alice_os.runtimes import RuntimeOperationError


def model_file(root, name="localai/nested/test.gguf"):
    path = root / "models" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"GGUFtest")
    return path


def test_inventory_includes_nested_and_huggingface_files(tmp_path):
    model_file(tmp_path)
    model_file(tmp_path, "huggingface/repo/test.gguf")
    items = inventory(tmp_path)
    assert len(items) == 2
    assert len({item["id"] for item in items}) == 2
    assert all(item["status"] == "Downloaded" for item in items)


async def test_loaded_file_cannot_be_deleted(tmp_path, monkeypatch):
    path = model_file(tmp_path)
    manager = ModelManager(ConfigStore(tmp_path))
    monkeypatch.setattr(manager, "loaded_path", AsyncMock(return_value=str(path)))
    assert (await manager.list())[0]["status"] == "Loaded"
    with pytest.raises(RuntimeOperationError, match="Load another"):
        await manager.delete("localai/nested/test.gguf")
    assert path.is_file()


async def test_paths_outside_inventory_cannot_load_or_delete(tmp_path):
    manager = ModelManager(ConfigStore(tmp_path))
    manager.loaded_path = AsyncMock(return_value="")
    for action in (manager.load, manager.delete):
        with pytest.raises(RuntimeOperationError, match="Select a downloaded"):
            await action("../../outside.gguf")


async def test_invalid_gguf_does_not_stop_server(tmp_path, monkeypatch):
    path = model_file(tmp_path)
    path.write_bytes(b"bad!")
    manager = ModelManager(ConfigStore(tmp_path))
    monkeypatch.setattr(module, "llama_cpp_executable", lambda: path)
    manager.owned_listener = Mock()
    with pytest.raises(RuntimeOperationError, match="not a GGUF"):
        await manager.load("localai/nested/test.gguf")
    manager.owned_listener.assert_not_called()


def test_unmanaged_listener_is_never_stopped(tmp_path, monkeypatch):
    manager = ModelManager(ConfigStore(tmp_path))
    process = Mock()
    process.exe.return_value = str(tmp_path / "other.exe")
    process.cmdline.return_value = []
    monkeypatch.setattr(module.psutil, "net_connections", lambda **_: [
        SimpleNamespace(status="LISTEN", laddr=SimpleNamespace(port=8081), pid=42)])
    monkeypatch.setattr(module.psutil, "Process", lambda _: process)
    with pytest.raises(RuntimeOperationError, match="unmanaged"):
        manager.owned_listener()
    process.terminate.assert_not_called()


async def test_switch_waits_for_health_then_selects_reported_model(tmp_path, monkeypatch):
    path = model_file(tmp_path)
    manager = ModelManager(ConfigStore(tmp_path))
    monkeypatch.setattr(module, "llama_cpp_executable", lambda: path)
    manager.loaded_path = AsyncMock(return_value="")
    old = Mock()
    manager.owned_listener = Mock(return_value=old)
    child = Mock()
    child.poll.return_value = None
    spawn = Mock(return_value=child)
    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(
        200, json={"data": [{"id": "test"}]} if request.url.path.endswith("models") else {"status": "ok"}))
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kw: real_client(transport=transport, **kw))
    result = await manager.load("localai/nested/test.gguf")
    old.terminate.assert_called_once()
    old.wait.assert_called_once()
    assert str(path) in spawn.call_args.args[0]
    assert result["model"] == manager.config.get().active_model == "test"
    assert (tmp_path / "loaded-model.txt").read_text() == str(path)


async def test_failed_model_does_not_update_selection(tmp_path, monkeypatch):
    path = model_file(tmp_path)
    manager = ModelManager(ConfigStore(tmp_path))
    monkeypatch.setattr(module, "llama_cpp_executable", lambda: path)
    manager.loaded_path = AsyncMock(return_value="")
    manager.owned_listener = Mock(return_value=None)
    child = Mock()
    child.poll.return_value = 1
    monkeypatch.setattr(module.subprocess, "Popen", Mock(return_value=child))
    with pytest.raises(RuntimeOperationError, match="failed to load"):
        await manager.load("localai/nested/test.gguf")
    assert manager.config.get().active_provider_id == "localai"
    assert not (tmp_path / "loaded-model.txt").exists()


async def test_unavailable_gpu_worker_does_not_stop_existing_model(tmp_path, monkeypatch):
    path = model_file(tmp_path)
    manager = ModelManager(ConfigStore(tmp_path))
    manager.distributed.save(DistributedSettings(enabled=True, endpoints=["127.0.0.1:50053"]))
    monkeypatch.setattr(module, "llama_cpp_executable", lambda: path)
    monkeypatch.setattr(module, "probe_devices", AsyncMock(side_effect=RuntimeOperationError("Offline worker")))
    manager.owned_listener = Mock()
    with pytest.raises(RuntimeOperationError, match="Offline worker"):
        await manager.load("localai/nested/test.gguf")
    manager.owned_listener.assert_not_called()


async def test_same_model_restarts_when_gpu_topology_changes(tmp_path, monkeypatch):
    path = model_file(tmp_path)
    manager = ModelManager(ConfigStore(tmp_path))
    manager.distributed.save(DistributedSettings(enabled=True, endpoints=["127.0.0.1:50053"]))
    monkeypatch.setattr(module, "llama_cpp_executable", lambda: path)
    monkeypatch.setattr(module, "probe_devices", AsyncMock(return_value="RPC0: 127.0.0.1:50053"))
    manager.loaded_path = AsyncMock(return_value=str(path))
    old = Mock()
    old.cmdline.return_value = [str(path), "-m", str(path)]
    manager.owned_listener = Mock(return_value=old)
    child = Mock()
    child.poll.return_value = None
    spawn = Mock(return_value=child)
    monkeypatch.setattr(module.subprocess, "Popen", spawn)
    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(
        200, json={"data": [{"id": "test"}]} if request.url.path.endswith("models") else {"status": "ok"}))
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kw: real_client(transport=transport, **kw))
    await manager.load("localai/nested/test.gguf")
    old.terminate.assert_called_once()
    assert spawn.call_args.args[0][-4:] == ["--rpc", "127.0.0.1:50053", "--split-mode", "layer"]
