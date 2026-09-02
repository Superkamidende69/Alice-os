from __future__ import annotations

from dataclasses import dataclass


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


def list_skills() -> list[dict[str, str]]:
    return [{"id": skill.id, "name": skill.name, "description": skill.description} for skill in _SKILLS]


def get_skill(skill_id: str) -> AgentSkill:
    return _BY_ID.get(skill_id, _BY_ID["general"])
