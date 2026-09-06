import httpx
import pytest

from alice_os.network import normalize_hostname, public_url, redirect_app


def test_canonical_hostname_and_standard_ports():
    assert normalize_hostname("Aliceos.local.") == "aliceos.local"
    assert public_url("https", "aliceos.local", 443) == "https://aliceos.local"
    assert public_url("https", "worker.local", 8443) == "https://worker.local:8443"
    for name in ("https://aliceos.local", "bad name", "-invalid.local", "host\r\nlocation:x"):
        with pytest.raises(ValueError):
            normalize_hostname(name)


async def test_http_redirect_preserves_path_but_never_trusts_host():
    app = redirect_app("https://aliceos.local")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://attacker.invalid") as client:
        response = await client.get("/cluster?tab=workers")
        assert response.status_code == 308
        assert response.headers["location"] == "https://aliceos.local/cluster?tab=workers"
        response = await client.post("/api/auth/login", json={"password": "test"})
        assert response.status_code == 405
