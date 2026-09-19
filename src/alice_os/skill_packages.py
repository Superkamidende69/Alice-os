"""Declarative capability packages. Importing a package never executes its code."""
from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .tools import ToolRegistry


class SkillManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,38}$")
    name: str = Field(min_length=1, max_length=80)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$", max_length=40)
    description: str = Field(min_length=1, max_length=240)
    instructions: str = Field(min_length=1, max_length=8000)
    tools: list[str] = Field(max_length=64)
    read_only: bool = True
    requires: list[Literal["git", "docker"]] = Field(default_factory=list, max_length=2)

    @field_validator("name", "description", "instructions")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Must not be blank")
        return value.strip()

    @field_validator("tools", "requires")
    @classmethod
    def unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate entries are not allowed")
        return value


TEMPLATES = [
    SkillManifest(
        id="workspace-inspector", name="Workspace inspector", version="1.0.0",
        description="Explore project files and explain how they fit together.",
        instructions="Inspect relevant files before answering. Cite paths and distinguish observations from assumptions. Do not modify files.",
        tools=["workspace_list", "workspace_read", "workspace_search"],
    ),
    SkillManifest(
        id="git-reviewer", name="Git reviewer", version="1.0.0",
        description="Review local changes and flag concrete problems.",
        instructions="Read Git status and diff, then inspect relevant source. Report concrete findings with paths and evidence. Do not modify files or claim tests ran.",
        tools=["git_status", "git_diff", "workspace_read", "workspace_search"],
        requires=["git"],
    ),
    SkillManifest(
        id="memory-recall", name="Memory recall", version="1.0.0",
        description="Answer questions using your saved memories.",
        instructions="Search saved memories before answering personal-history questions. Say when a fact is not found. Never invent memories or claim to save new facts.",
        tools=["memory_search"],
    ),
]


class PackageStore:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "skill-packages.json"
        self._lock = threading.RLock()
        self._entries: dict[str, dict] = {}
        self.load_error = ""
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("Expected a package catalog object")
            for package_id, entry in raw.items():
                manifest = SkillManifest.model_validate(entry["manifest"])
                if manifest.id != package_id or type(entry["enabled"]) is not bool:
                    raise ValueError("Invalid package record")
                self._entries[package_id] = {"manifest": manifest, "enabled": entry["enabled"]}
        except FileNotFoundError:
            pass
        except (OSError, ValueError, KeyError, TypeError) as error:
            self._entries.clear()
            self.load_error = f"Package catalog could not be loaded: {error}"

    def _save(self) -> None:
        if self.load_error:
            raise ValueError(self.load_error + ". Repair the catalog before changing packages.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: {"manifest": value["manifest"].model_dump(), "enabled": value["enabled"]}
                   for key, value in self._entries.items()}
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def health(manifest: SkillManifest) -> list[str]:
        registry = ToolRegistry()
        known = {tool["function"]["name"] for tool in registry.definitions()}
        readable = {tool["function"]["name"] for tool in registry.definitions(read_only=True)}
        issues = [f"Unknown tool: {name}" for name in manifest.tools if name not in known]
        if manifest.read_only:
            issues.extend(f"Read-only package cannot use: {name}" for name in manifest.tools
                          if name in known and name not in readable)
        issues.extend(f"Required executable not found: {name}" for name in manifest.requires
                      if shutil.which(name) is None)
        return issues

    def list(self) -> list[dict]:
        with self._lock:
            result = []
            for entry in self._entries.values():
                manifest = entry["manifest"]
                issues = self.health(manifest)
                result.append({**manifest.model_dump(), "enabled": entry["enabled"],
                               "available": entry["enabled"] and not issues,
                               "issues": issues, "packaged": True, "built_in": False})
            return result

    def get(self, package_id: str) -> dict | None:
        return next((entry for entry in self.list() if entry["id"] == package_id), None)

    def install(self, manifest: SkillManifest) -> dict:
        with self._lock:
            old = self._entries.get(manifest.id)
            # Every import/update requires an explicit enable after permissions are reviewed.
            self._entries[manifest.id] = {"manifest": manifest, "enabled": False}
            try:
                self._save()
            except Exception:
                if old is None:
                    self._entries.pop(manifest.id)
                else:
                    self._entries[manifest.id] = old
                raise
            return self.get(manifest.id)

    def set_enabled(self, package_id: str, enabled: bool) -> dict:
        with self._lock:
            entry = self._entries[package_id]
            if enabled and (issues := self.health(entry["manifest"])):
                raise ValueError("; ".join(issues))
            previous = entry["enabled"]
            entry["enabled"] = enabled
            try:
                self._save()
            except Exception:
                entry["enabled"] = previous
                raise
            return self.get(package_id)

    def delete(self, package_id: str) -> None:
        with self._lock:
            previous = self._entries.pop(package_id)
            try:
                self._save()
            except Exception:
                self._entries[package_id] = previous
                raise

    def export(self, package_id: str) -> dict:
        with self._lock:
            return self._entries[package_id]["manifest"].model_dump()
