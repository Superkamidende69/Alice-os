import base64

import httpx
from fastapi.testclient import TestClient

from alice_os.api import create_app


def test_images_require_login_and_validate_prompt(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.post("/api/images/generate", json={"prompt": "cat"}).status_code == 401
        assert client.get("/api/images/" + "a" * 32).status_code == 401
        client.get("/")
        for prompt in ("", "   ", "a" * 2001):
            assert client.post("/api/images/generate", json={"prompt": prompt}).status_code == 422
        assert client.get("/api/images/not-a-file").status_code == 404


def test_image_saved_and_served_only_by_generated_id(tmp_path, monkeypatch):
    png = b"\x89PNG\r\n\x1a\nfixture"
    class Backend:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, json):
            assert url == "http://127.0.0.1:8082/v1/images/generations"
            assert json == {"prompt": "A blue cat"}
            return httpx.Response(200, request=httpx.Request("POST", url),
                json={"data": [{"b64_json": base64.b64encode(png).decode()}]})
    with TestClient(create_app(tmp_path)) as client:
        client.get("/")
        monkeypatch.setattr("alice_os.api.httpx.AsyncClient", Backend)
        result = client.post("/api/images/generate", json={"prompt": "A blue cat"})
        assert result.status_code == 200
        response = client.get(result.json()["url"])
        assert response.content == png
        assert response.headers["content-type"] == "image/png"
        assert len(list((tmp_path / "generated-images").glob("*.png"))) == 1


def test_busy_runtime_does_not_save_an_image(tmp_path, monkeypatch):
    class Backend:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs): return httpx.Response(429)
    with TestClient(create_app(tmp_path)) as client:
        client.get("/")
        monkeypatch.setattr("alice_os.api.httpx.AsyncClient", Backend)
        result = client.post("/api/images/generate", json={"prompt": "cat"})
        assert result.status_code == 409
        assert not (tmp_path / "generated-images").exists()
