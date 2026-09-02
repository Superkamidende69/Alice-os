from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from .models import AppSettings, ProviderProfile


def default_data_dir() -> Path:
    override = os.environ.get("ALICE_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "AliceOS"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg).expanduser() / "alice-os"
    return Path.home() / ".local" / "share" / "alice-os"


def default_settings() -> AppSettings:
    return AppSettings(
        active_provider_id="ollama",
        providers=[
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
            return AppSettings.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return default_settings()

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
        if provider_id == "ollama":
            raise ValueError("The built-in Ollama profile cannot be deleted")
        with self._lock:
            self._settings.providers = [p for p in self._settings.providers if p.id != provider_id]
            if self._settings.active_provider_id == provider_id:
                self._settings.active_provider_id = "ollama"
            self._save()
            return self.get()

    def set_active(self, provider_id: str) -> AppSettings:
        self.get_provider(provider_id)
        with self._lock:
            self._settings.active_provider_id = provider_id
            self._save()
            return self.get()
