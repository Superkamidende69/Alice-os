from __future__ import annotations

import json
import os
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from .models import AssistantTurn, ProviderProfile, ToolCall

TokenCallback = Callable[[str], Awaitable[None]]


class ProviderError(RuntimeError):
    pass


class ToolsUnsupportedError(ProviderError):
    pass


def _api_headers(profile: ProviderProfile) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if profile.api_key_env:
        api_key = os.environ.get(profile.api_key_env)
        if not api_key:
            raise ProviderError(f"Environment variable {profile.api_key_env!r} is not set")
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _openai_url(base_url: str, suffix: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}{suffix}"
    return f"{base}/v1{suffix}"


async def list_models(profile: ProviderProfile) -> list[str]:
    timeout = httpx.Timeout(10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            if profile.kind == "ollama":
                response = await client.get(f"{profile.base_url}/api/tags")
                response.raise_for_status()
                payload = response.json()
                return sorted(
                    model.get("name", "")
                    for model in payload.get("models", [])
                    if model.get("name")
                )
            response = await client.get(
                _openai_url(profile.base_url, "/models"),
                headers=_api_headers(profile),
            )
            response.raise_for_status()
            payload = response.json()
            return sorted(item.get("id", "") for item in payload.get("data", []) if item.get("id"))
    except (httpx.HTTPError, ValueError) as error:
        raise ProviderError(f"Could not list models from {profile.name}: {error}") from error


def _normalize_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        item: dict[str, Any] = {
            "role": message["role"],
            "content": message.get("content") or "",
        }
        metadata = message.get("metadata") or {}
        if message["role"] == "assistant" and metadata.get("tool_calls"):
            item["tool_calls"] = metadata["tool_calls"]
        if message["role"] == "tool":
            item["tool_call_id"] = metadata.get("tool_call_id", "")
            if metadata.get("name"):
                item["name"] = metadata["name"]
        normalized.append(item)
    return normalized


def _normalize_ollama_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        item: dict[str, Any] = {
            "role": message["role"],
            "content": message.get("content") or "",
        }
        metadata = message.get("metadata") or {}
        if message["role"] == "assistant" and metadata.get("tool_calls"):
            item["tool_calls"] = [
                {
                    "function": {
                        "name": call["function"]["name"],
                        "arguments": _arguments_object(call["function"].get("arguments", {})),
                    }
                }
                for call in metadata["tool_calls"]
            ]
        if message["role"] == "tool" and metadata.get("name"):
            item["tool_name"] = metadata["name"]
        normalized.append(item)
    return normalized


def _arguments_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


async def chat(
    profile: ProviderProfile,
    *,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    on_token: TokenCallback | None = None,
) -> AssistantTurn:
    if not model:
        raise ProviderError("Select a model before sending a message")
    if profile.kind == "ollama":
        return await _ollama_chat(
            profile, model=model, messages=messages, tools=tools, on_token=on_token
        )
    return await _openai_chat(
        profile, model=model, messages=messages, tools=tools, on_token=on_token
    )


async def _openai_chat(
    profile: ProviderProfile,
    *,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    on_token: TokenCallback | None,
) -> AssistantTurn:
    body: dict[str, Any] = {
        "model": model,
        "messages": _normalize_openai_messages(messages),
        "stream": True,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"
    timeout = httpx.Timeout(connect=15.0, read=300.0, write=30.0, pool=15.0)
    content_parts: list[str] = []
    tool_parts: dict[int, dict[str, str]] = {}
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            async with client.stream(
                "POST",
                _openai_url(profile.base_url, "/chat/completions"),
                headers=_api_headers(profile),
                json=body,
            ) as response:
                if response.status_code >= 400:
                    detail = (await response.aread()).decode("utf-8", errors="replace")[:1500]
                    if tools and response.status_code in {400, 404, 422}:
                        raise ToolsUnsupportedError(detail or "Provider rejected tool definitions")
                    raise ProviderError(
                        f"{profile.name} returned HTTP {response.status_code}: {detail}"
                    )
                content_type = response.headers.get("content-type", "")
                if "text/event-stream" not in content_type:
                    raw = await response.aread()
                    return await _parse_openai_nonstream(raw, on_token)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    token = delta.get("content")
                    if isinstance(token, str) and token:
                        content_parts.append(token)
                        if on_token:
                            await on_token(token)
                    for tool_delta in delta.get("tool_calls") or []:
                        index = int(tool_delta.get("index", 0))
                        aggregate = tool_parts.setdefault(
                            index, {"id": "", "name": "", "arguments": ""}
                        )
                        if tool_delta.get("id"):
                            aggregate["id"] = tool_delta["id"]
                        function = tool_delta.get("function") or {}
                        aggregate["name"] += function.get("name") or ""
                        arguments = function.get("arguments")
                        if isinstance(arguments, str):
                            aggregate["arguments"] += arguments
    except ToolsUnsupportedError:
        raise
    except httpx.HTTPError as error:
        raise ProviderError(f"Could not reach {profile.name}: {error}") from error
    return AssistantTurn(
        content="".join(content_parts),
        tool_calls=[_build_tool_call(value) for _, value in sorted(tool_parts.items())],
    )


async def _parse_openai_nonstream(raw: bytes, on_token: TokenCallback | None) -> AssistantTurn:
    try:
        payload = json.loads(raw)
        message = payload["choices"][0]["message"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
        raise ProviderError("Provider returned an invalid chat response") from error
    content = message.get("content") or ""
    if content and on_token:
        await on_token(content)
    calls = []
    for call in message.get("tool_calls") or []:
        function = call.get("function") or {}
        calls.append(
            _build_tool_call(
                {
                    "id": call.get("id") or "",
                    "name": function.get("name") or "",
                    "arguments": function.get("arguments") or "{}",
                }
            )
        )
    return AssistantTurn(content=content, tool_calls=calls)


def _build_tool_call(value: dict[str, str]) -> ToolCall:
    raw_arguments = value.get("arguments") or "{}"
    try:
        arguments = json.loads(raw_arguments)
        if not isinstance(arguments, dict):
            arguments = {"value": arguments}
    except json.JSONDecodeError:
        arguments = {"_invalid_json": raw_arguments}
    return ToolCall(
        id=value.get("id") or f"call_{uuid.uuid4().hex[:12]}",
        name=value.get("name") or "unknown",
        arguments=arguments,
    )


async def _ollama_chat(
    profile: ProviderProfile,
    *,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
    on_token: TokenCallback | None,
) -> AssistantTurn:
    body: dict[str, Any] = {
        "model": model,
        "messages": _normalize_ollama_messages(messages),
        "stream": True,
    }
    if tools:
        body["tools"] = tools
    timeout = httpx.Timeout(connect=15.0, read=300.0, write=30.0, pool=15.0)
    content_parts: list[str] = []
    calls: list[ToolCall] = []
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            async with client.stream("POST", f"{profile.base_url}/api/chat", json=body) as response:
                if response.status_code >= 400:
                    detail = (await response.aread()).decode("utf-8", errors="replace")[:1500]
                    if tools and response.status_code in {400, 404, 422}:
                        raise ToolsUnsupportedError(detail or "Ollama rejected tool definitions")
                    raise ProviderError(
                        f"{profile.name} returned HTTP {response.status_code}: {detail}"
                    )
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("error"):
                        raise ProviderError(str(chunk["error"]))
                    message = chunk.get("message") or {}
                    token = message.get("content") or ""
                    if token:
                        content_parts.append(token)
                        if on_token:
                            await on_token(token)
                    for call in message.get("tool_calls") or []:
                        function = call.get("function") or {}
                        calls.append(
                            ToolCall(
                                id=call.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                                name=function.get("name") or "unknown",
                                arguments=_arguments_object(function.get("arguments")),
                            )
                        )
    except ToolsUnsupportedError:
        raise
    except httpx.HTTPError as error:
        raise ProviderError(f"Could not reach {profile.name}: {error}") from error
    return AssistantTurn(content="".join(content_parts), tool_calls=calls)
