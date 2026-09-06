"""LAN URL handling and a redirect-only HTTP listener."""
from __future__ import annotations

import re
import socket
import threading
from urllib.parse import quote

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse


def normalize_hostname(value: str) -> str:
    name = value.lower().rstrip(".")
    if len(name) > 253 or not all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in name.split(".")
    ):
        raise ValueError("Hostname must be a DNS name, for example aliceos.local")
    return name


def public_url(scheme: str, host: str, port: int) -> str:
    suffix = "" if (scheme, port) in {("https", 443), ("http", 80)} else f":{port}"
    return f"{scheme}://{host}{suffix}"


def redirect_app(target: str) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    async def redirect(request: Request, path: str):
        # Destination never comes from an untrusted Host or forwarded header.
        suffix = quote(request.url.path, safe="/")
        query = f"?{request.url.query}" if request.url.query else ""
        return RedirectResponse(target + suffix + query, status_code=308)

    return app


class HTTPRedirect:
    def __init__(self, host: str, target: str, port: int = 80):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.bind((host, port))
            self.socket.listen(128)
        except OSError:
            self.socket.close()
            raise
        self.server = uvicorn.Server(uvicorn.Config(
            redirect_app(target), log_level="warning", proxy_headers=False,
        ))
        self.thread = threading.Thread(target=self.server.run,
                                       kwargs={"sockets": [self.socket]}, daemon=True)
        self.thread.start()

    def close(self):
        self.server.should_exit = True
        self.thread.join(timeout=5)
        self.socket.close()


def start_http_redirect(host: str, target: str) -> HTTPRedirect:
    return HTTPRedirect(host, target)
