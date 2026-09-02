from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AgentSkill:
    id: str
    name: str
    description: str
    instructions: str
    read_only: bool = False


_SKILLS = (
    AgentSkill(
        id="general",
        name="General agent",
        description="Balanced help across research, coding, and local tools.",
        instructions="Work adaptively. Prefer a short plan for multi-step work and verify tool-backed claims.",
    ),
    AgentSkill(
        id="plan",
        name="Plan a feature",
        description="Turn a request into a scoped, implementation-ready plan.",
        instructions="Do not modify files or run processes. Inspect relevant evidence, state assumptions, then produce a concise numbered plan with affected files, validation, and risks.",
        read_only=True,
    ),
    AgentSkill(
        id="debug",
        name="Debug an issue",
        description="Trace a failure from evidence to a focused fix.",
        instructions="Reproduce or inspect the failure first. Separate observed facts from hypotheses, make the smallest safe change, and verify the fix before reporting it.",
    ),
    AgentSkill(
        id="review",
        name="Review code",
        description="Find concrete correctness, safety, and maintainability issues.",
        instructions="Inspect diffs and relevant context. Report findings ordered by impact with file and line references where available. Do not edit files unless the user explicitly asks for fixes.",
        read_only=True,
    ),
    AgentSkill(
        id="implement",
        name="Implement safely",
        description="Build a focused change with approvals and verification.",
        instructions="Inspect before editing. Keep changes minimal and coherent, request approval for writes or commands, then run the most relevant verification and summarize exact changes.",
    ),
)

_BY_ID = {skill.id: skill for skill in _SKILLS}
_SKILL_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,38}")


def list_skills() -> list[dict[str, str]]:
    return [{"id": skill.id, "name": skill.name, "description": skill.description} for skill in _SKILLS]


def get_skill(skill_id: str) -> AgentSkill:
    return _BY_ID.get(skill_id, _BY_ID["general"])


class SkillStore:
    """Small local catalog for user-defined agent workflows."""

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "skills.json"
        self._lock = threading.RLock()
        self._custom = self._load()

    def _load(self) -> dict[str, AgentSkill]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            entries = raw if isinstance(raw, list) else []
        except (OSError, ValueError, json.JSONDecodeError):
            entries = []
        skills: dict[str, AgentSkill] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            skill_id = str(entry.get("id", ""))
            if skill_id in _BY_ID or not _SKILL_ID.fullmatch(skill_id):
                continue
            name = str(entry.get("name", "")).strip()
            description = str(entry.get("description", "")).strip()
            instructions = str(entry.get("instructions", "")).strip()
            if name and description and instructions:
                skills[skill_id] = AgentSkill(
                    id=skill_id,
                    name=name[:80],
                    description=description[:240],
                    instructions=instructions[:8000],
                    read_only=bool(entry.get("read_only", False)),
                )
        return skills

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "instructions": skill.instructions,
                "read_only": skill.read_only,
            }
            for skill in self._custom.values()
        ]
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.path)

    @staticmethod
    def _public(skill: AgentSkill, *, built_in: bool) -> dict[str, str | bool]:
        return {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "instructions": skill.instructions,
            "read_only": skill.read_only,
            "built_in": built_in,
        }

    def list(self) -> list[dict[str, str | bool]]:
        with self._lock:
            return [
                *(self._public(skill, built_in=True) for skill in _SKILLS),
                *(self._public(skill, built_in=False) for skill in self._custom.values()),
            ]

    def get(self, skill_id: str) -> AgentSkill:
        with self._lock:
            return self._custom.get(skill_id, get_skill(skill_id))

    def upsert(self, skill: AgentSkill) -> AgentSkill:
        skill_id = skill.id.strip().lower()
        if skill_id in _BY_ID:
            raise ValueError("Built-in skills cannot be replaced")
        if not _SKILL_ID.fullmatch(skill_id):
            raise ValueError("Skill ID must use lowercase letters, numbers, and hyphens")
        name, description, instructions = skill.name.strip(), skill.description.strip(), skill.instructions.strip()
        if not name or not description or not instructions:
            raise ValueError("Name, description, and instructions are required")
        custom = AgentSkill(
            id=skill_id,
            name=name[:80],
            description=description[:240],
            instructions=instructions[:8000],
            read_only=skill.read_only,
        )
        with self._lock:
            self._custom[skill_id] = custom
            self._save()
        return custom

    def delete(self, skill_id: str) -> None:
        with self._lock:
            if skill_id not in self._custom:
                raise KeyError(skill_id)
            del self._custom[skill_id]
            self._save()
