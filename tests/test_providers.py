from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

import alice_os.providers as providers
from alice_os.models import ProviderProfile


def install_transport(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def client_factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(providers.httpx, "AsyncClient", client_factory)


@pytest.mark.asyncio
async def test_openai_sse_aggregates_tokens_and_fragmented_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    chunks = [
        {"choices": [{"delta": {"content": "Hel"}}]},
        {"choices": [{"delta": {"content": "lo "}}]},
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call_read",
                                "type": "function",
                                "function": {
                                    "name": "workspace_",
                                    "arguments": '{"pa',
                                },
                            }
                        ]
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "function": {
                                    "name": "read",
                                    "arguments": 'th":"README.md"}',
                                },
                            }
                        ]
                    }
                }
            ]
        },
    ]
    stream = "event: message\n" + "\n\n".join(f"data: {json.dumps(chunk)}" for chunk in chunks)
    stream += "\n\ndata: not-json\n\ndata: [DONE]\n\n"

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream; charset=utf-8"},
            content=stream.encode("utf-8"),
        )

    install_transport(monkeypatch, handler)
    monkeypatch.setenv("TEST_ALICE_API_KEY", "secret-value")
    profile = ProviderProfile(
        id="test",
        name="Mock provider",
        kind="openai",
        base_url="https://provider.test/v1/",
        api_key_env="TEST_ALICE_API_KEY",
    )
    tokens: list[str] = []

    async def on_token(token: str) -> None:
        tokens.append(token)

    turn = await providers.chat(
        profile,
        model="test-model",
        messages=[{"role": "user", "content": "hello", "metadata": {}}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "workspace_read",
                    "parameters": {"type": "object"},
                },
            }
        ],
        on_token=on_token,
    )

    assert captured["url"] == "https://provider.test/v1/chat/completions"
    assert captured["authorization"] == "Bearer secret-value"
    assert captured["body"]["stream"] is True
    assert captured["body"]["tool_choice"] == "auto"
    assert captured["body"]["messages"] == [{"role": "user", "content": "hello"}]
    assert tokens == ["Hel", "lo "]
    assert turn.content == "Hello "
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].id == "call_read"
    assert turn.tool_calls[0].name == "workspace_read"
    assert turn.tool_calls[0].arguments == {"path": "README.md"}


@pytest.mark.asyncio
async def test_openai_tool_rejection_raises_compatibility_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(422, text="tools are not supported")

    install_transport(monkeypatch, handler)
    profile = ProviderProfile(
        id="test",
        name="Mock provider",
        kind="openai",
        base_url="https://provider.test",
    )

    with pytest.raises(providers.ToolsUnsupportedError, match="not supported"):
        await providers.chat(
            profile,
            model="test-model",
            messages=[{"role": "user", "content": "hello"}],
            tools=[{"type": "function", "function": {"name": "test"}}],
        )
