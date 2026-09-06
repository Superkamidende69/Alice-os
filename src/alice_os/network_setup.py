"""Prepare LAN certificates without passing Python source through a shell."""
from __future__ import annotations

import argparse
import json

import psutil

from .config import default_data_dir
from .network import normalize_hostname
from .tls import ensure_tls_certificate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hostname", default="aliceos.local")
    args = parser.parse_args()
    data = default_data_dir()
    if not (data / "network-auth.json").is_file():
        raise SystemExit("Run scripts/start.cmd once to configure the Alice administrator first.")
    try:
        ca, _, _ = ensure_tls_certificate(data, normalize_hostname(args.hostname))
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps({"ca_path": str(ca), "runtime_python": psutil.Process().exe()}))


if __name__ == "__main__":
    main()
