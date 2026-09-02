from __future__ import annotations

import argparse
import threading
import webbrowser

import uvicorn

from .api import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alice", description="Run the Alice OS local AI operator."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=7788, type=int)
    parser.add_argument("--no-browser", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Alice OS currently binds only to localhost for safety.")
    url = f"http://127.0.0.1:{args.port}"
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=args.port, log_level="info")
