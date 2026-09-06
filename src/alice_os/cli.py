from __future__ import annotations

import argparse
import os
import socket
import threading
import webbrowser
from pathlib import Path

import uvicorn

from .api import create_app
from .config import default_data_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="alice", description="Run the Alice OS local AI operator."
    )
    parser.add_argument("--setup", action="store_true", help="Configure storage and administrator, then exit")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, help="Listen port (443 with HTTPS, otherwise 7788)")
    parser.add_argument("--lan", action="store_true", help="Serve LAN HTTPS with an HTTP redirect")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--https", action="store_true", help="Serve HTTPS using Alice's local certificate")
    parser.add_argument("--hostname", default="aliceos.local", help="LAN hostname advertised by Alice")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.lan:
        args.https = True
        args.host = "0.0.0.0"
    args.port = args.port if args.port is not None else (443 if args.https else 7788)
    if not 1 <= args.port <= 65535:
        raise SystemExit("Port must be between 1 and 65535")
    from .network import normalize_hostname, public_url
    try:
        args.hostname = normalize_hostname(args.hostname)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    from .installation import ensure_installation

    try:
        data_directory = ensure_installation()
    except (OSError, ValueError, EOFError) as error:
        raise SystemExit(f"Setup failed: {error}") from error
    if args.setup:
        print(f"Installation configured. Data directory: {data_directory}")
        print("Existing credentials and data were preserved.")
        return
    scheme = "https" if args.https else "http"
    browser_host = args.hostname if args.host not in {"127.0.0.1", "localhost"} else "localhost"
    url = public_url(scheme, browser_host, args.port)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        os.environ["ALICE_NETWORK_MODE"] = "1"
    uvicorn_options = {"log_level": "info"}
    mdns = None
    if args.https:
        from .tls import ensure_tls_certificate

        data_dir = (
            Path(os.environ["ALICE_HOME"]).expanduser()
            if os.environ.get("ALICE_HOME")
            else default_data_dir()
        )
        ca_path, cert_path, key_path = ensure_tls_certificate(data_dir.resolve(), args.hostname)
        print(f"Public CA certificate to trust on client devices: {ca_path}")
        os.environ["ALICE_HTTPS"] = "1"
        uvicorn_options.update(ssl_certfile=str(cert_path), ssl_keyfile=str(key_path))
    else:
        os.environ.pop("ALICE_HTTPS", None)
    app = create_app()
    print(f"Alice OS: {url}/")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    if args.host not in {"127.0.0.1", "localhost"} and args.hostname.endswith(".local"):
        try:
            from zeroconf import ServiceInfo, Zeroconf

            from .tls import _lan_ipv4_addresses
            addresses = _lan_ipv4_addresses()
            if not addresses:
                raise OSError("No LAN IPv4 address was found")
            service_type = "_https._tcp.local." if args.https else "_http._tcp.local."
            service = ServiceInfo(
                service_type,
                f"Alice OS ({args.hostname}).{service_type}",
                addresses=[socket.inet_aton(str(address)) for address in addresses],
                port=args.port,
                properties={"path": "/"},
                server=f"{args.hostname}.",
            )
            mdns = Zeroconf()
            mdns.register_service(service, allow_name_change=True)
        except Exception as error:
            # Discovery is optional: a conflict or adapter failure must not stop HTTP.
            if mdns is not None:
                mdns.close()
                mdns = None
            print(f"mDNS advertisement unavailable ({type(error).__name__}); "
                  "connect using this computer's LAN IP address.")
    redirect = None
    if args.lan:
        from .network import start_http_redirect
        try:
            redirect = start_http_redirect(args.host, url)
        except OSError as error:
            print(f"HTTP redirect unavailable ({error}); use {url}/ directly.")
    try:
        uvicorn.run(app, host=args.host, port=args.port, **uvicorn_options)
    finally:
        if redirect is not None:
            redirect.close()
        if mdns is not None:
            mdns.close()
