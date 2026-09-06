from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from .models import AppSettings, ProviderProfile


def installation_file() -> Path:
    return Path(__file__).resolve().parents[2] / ".alice-install.json"


def default_data_dir() -> Path:
    override = os.environ.get("ALICE_HOME")
    if override:
        return Path(override).expanduser().resolve()
    pointer = installation_file()
    if pointer.exists():
        data = json.loads(pointer.read_text(encoding="utf-8"))
        target = Path(data["data_dir"])
        if not target.is_absolute():
            raise ValueError("Installation data directory must be absolute")
        return target.resolve()
    legacy = pointer.parent / ".alice-data"
    if (legacy / "settings.json").is_file():
        return legacy.resolve()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AliceOS"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg).expanduser() / "alice-os"
    return Path.home() / ".local" / "share" / "alice-os"


def _latest_managed_gguf(data_dir: Path) -> Path | None:
    model_root = data_dir / "models" / "localai"
    candidates = [path for path in model_root.glob("**/*.gguf") if path.is_file()]
    if not candidates:
        return None
    try:
        return max(candidates, key=lambda path: path.stat().st_mtime).resolve()
    except OSError:
        return None


def default_settings() -> AppSettings:
    return AppSettings(
        active_provider_id="localai",
        providers=[
            ProviderProfile(
                id="localai",
                name="LocalAI (local)",
                kind="localai",
                base_url="http://127.0.0.1:8080",
                default_model="",
            ),
            ProviderProfile(
                id="ollama",
                name="Ollama (local)",
                kind="ollama",
                base_url="http://127.0.0.1:11434",
                default_model="",
            )
        ],
    )


class ConfigStore:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = (data_dir or default_data_dir()).resolve()
        self.path = self.data_dir / "settings.json"
        self._lock = threading.RLock()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._settings = default_settings()
            self._save()
        else:
            self._settings = self._load()

    def _load(self) -> AppSettings:
        try:
            settings = AppSettings.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return default_settings()
        # Existing Alice installations keep their custom providers and history,
        # but gain the built-in LocalAI target during the provider migration.
        changed = False
        if not any(provider.id == "localai" for provider in settings.providers):
            settings.providers.insert(
                0,
                ProviderProfile(
                    id="localai",
                    name="LocalAI (local)",
                    kind="localai",
                    base_url="http://127.0.0.1:8080",
                    default_model="",
                ),
            )
            changed = True
        if settings.active_provider_id == "ollama":
            settings.active_provider_id = "localai"
            settings.active_model = ""
            changed = True
        managed_model = _latest_managed_gguf(self.data_dir)
        for provider in settings.providers:
            if provider.id == "llama_cpp_local" and provider.base_url.endswith(":8080/v1"):
                provider.base_url = provider.base_url[:-len(":8080/v1")] + ":8081/v1"
                changed = True
            if provider.id == "llama_cpp_local":
                configured_model = Path(provider.default_model) if provider.default_model else None
                if configured_model and configured_model.is_absolute() and not configured_model.is_file():
                    provider.default_model = str(managed_model) if managed_model else ""
                    changed = True
                if managed_model and "qwen" in provider.name.casefold():
                    provider.name = "llama.cpp (Alice managed)"
                    changed = True
        if changed:
            self._settings = settings
            self._save()
        return settings

    def _save(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(self._settings.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def get(self) -> AppSettings:
        with self._lock:
            return self._settings.model_copy(deep=True)

    def get_provider(self, provider_id: str) -> ProviderProfile:
        with self._lock:
            for provider in self._settings.providers:
                if provider.id == provider_id:
                    return provider.model_copy(deep=True)
        raise KeyError(f"Unknown provider: {provider_id}")

    def upsert_provider(self, profile: ProviderProfile) -> AppSettings:
        with self._lock:
            providers = [p for p in self._settings.providers if p.id != profile.id]
            providers.append(profile)
            self._settings.providers = providers
            if not self._settings.active_provider_id:
                self._settings.active_provider_id = profile.id
            self._save()
            return self.get()

    def delete_provider(self, provider_id: str) -> AppSettings:
        if provider_id in {"ollama", "localai"}:
            raise ValueError("Built-in provider profiles cannot be deleted")
        with self._lock:
            self._settings.providers = [p for p in self._settings.providers if p.id != provider_id]
            if self._settings.active_provider_id == provider_id:
                self._settings.active_provider_id = "localai"
            self._save()
            return self.get()

    def set_active(self, provider_id: str) -> AppSettings:
        self.get_provider(provider_id)
        with self._lock:
            self._settings.active_provider_id = provider_id
            self._settings.active_model = ""
            self._save()
            return self.get()

    def set_active_model(self, model: str) -> AppSettings:
        with self._lock:
            self._settings.active_model = model.strip()
            self._save()
            return self.get()
