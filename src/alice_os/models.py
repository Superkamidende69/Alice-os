from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ProviderKind = Literal["ollama", "openai"]


class ProviderProfile(BaseModel):
    id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=80)
    kind: ProviderKind
    base_url: str = Field(min_length=1)
    default_model: str = ""
    api_key_env: str = ""

    @field_validator("base_url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        return value.strip().rstrip("/")


class AppSettings(BaseModel):
    active_provider_id: str = "ollama"
    providers: list[ProviderProfile] = Field(default_factory=list)


@dataclass(slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(slots=True)
class AssistantTurn:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass(slots=True)
class StoredMessage:
    id: str
    session_id: str
    role: str
    content: str
    metadata: dict[str, Any]
    created_at: str
