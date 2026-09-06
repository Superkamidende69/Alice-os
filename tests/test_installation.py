
import pytest
from fastapi.testclient import TestClient

from alice_os import config, installation
from alice_os.api import create_app
from alice_os.auth import verify_auth_file


@pytest.fixture
def pointer(tmp_path, monkeypatch):
    path = tmp_path / "code" / ".alice-install.json"
    path.parent.mkdir()
    monkeypatch.setattr(installation, "installation_file", lambda: path)
    monkeypatch.setattr(config, "installation_file", lambda: path)
    monkeypatch.delenv("ALICE_HOME", raising=False)
    return path


def test_setup_persists_external_storage_and_login(tmp_path, pointer, monkeypatch):
    target = tmp_path / "data"
    installation.initialize_installation(target, "admin", "a long test password")
    assert config.default_data_dir() == target
    assert verify_auth_file(target / "network-auth.json", "admin", "a long test password")
    assert "a long test password" not in (target / "network-auth.json").read_text()
    monkeypatch.delenv("ALICE_NETWORK_MODE", raising=False)
    with TestClient(create_app(target)) as client:
        assert client.get("/api/auth/status").json()["required"] is True
        assert client.post("/api/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401
        assert client.post("/api/auth/login", json={"username": "admin", "password": "a long test password"}).status_code == 200
        assert client.get("/api/auth/status").json()["authenticated"] is True


def test_setup_rejects_code_directory_and_existing_data(tmp_path, pointer):
    for target in (pointer.parent / "data", tmp_path):
        with pytest.raises(ValueError):
            installation.initialize_installation(target, "admin", "a long test password")
    assert not pointer.exists()


def test_setup_cannot_replace_existing_install(tmp_path, pointer):
    installation.initialize_installation(tmp_path / "data", "admin", "a long test password")
    with pytest.raises(ValueError):
        installation.initialize_installation(tmp_path / "other", "other", "another long password")
    assert config.default_data_dir() == tmp_path / "data"


def test_environment_override_wins(tmp_path, pointer, monkeypatch):
    installation.initialize_installation(tmp_path / "data", "admin", "a long test password")
    monkeypatch.setenv("ALICE_HOME", str(tmp_path / "override"))
    assert config.default_data_dir() == tmp_path / "override"
