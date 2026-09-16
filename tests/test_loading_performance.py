from __future__ import annotations

import asyncio
import time

import httpx

from alice_os import api, runtimes


async def test_bootstrap_skips_probes_and_concurrent_status_requests_share_work(monkeypatch, tmp_path):
    calls = 0

    async def probe():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return {"gpu": {}, "ollama": {}, "localai": {}, "llama_cpp": {}}

    monkeypatch.setattr(api, "runtime_status", probe)
    app = api.create_app(tmp_path / "data")
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver",
                                     headers={"X-Alice-Token": app.state.session_token}) as client:
            response = await client.get("/api/state?include_runtimes=false")
            assert response.status_code == 200
            assert response.json()["runtimes"] is None
            assert "sessions" in response.json()
            assert calls == 0
            results = await asyncio.gather(*(client.get("/api/runtime/status") for _ in range(5)))
            assert all(response.status_code == 200 for response in results)
            assert calls == 1
            assert (await client.get("/api/state")).json()["runtimes"] == results[0].json()
            assert calls == 1


async def test_runtime_probes_overlap_and_gpu_does_not_block_event_loop(monkeypatch):
    started = set()
    all_started = asyncio.Event()

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            started.add(httpx.URL(url).port)
            if len(started) == 3:
                all_started.set()
            await asyncio.wait_for(all_started.wait(), 1)
            return httpx.Response(200, json={"models": [], "data": [], "status": "ok"},
                                  request=httpx.Request("GET", url))

    def gpu():
        time.sleep(0.1)
        return {"detected": True}

    monkeypatch.setattr(runtimes.httpx, "AsyncClient", Client)
    monkeypatch.setattr(runtimes, "gpu_status", gpu)
    result = await runtimes.runtime_status()
    assert result["gpu"]["detected"]
    assert all(result[key]["running"] for key in ("ollama", "localai", "llama_cpp"))
