"""Local, interactive first-install setup; runs before any services start."""
from __future__ import annotations

import getpass
import json
import os
import sys
import tempfile
from pathlib import Path

from .auth import create_auth_file
from .config import default_data_dir, installation_file


def initialize_installation(data_dir: Path, username: str, password: str) -> Path:
    target = data_dir.expanduser()
    if not target.is_absolute():
        raise ValueError("Choose an absolute data directory")
    target = target.resolve()
    pointer = installation_file()
    if target == pointer.parent or pointer.parent in target.parents:
        raise ValueError("Choose a data directory outside the Alice application folder")
    if pointer.exists():
        raise ValueError("Installation is already configured; its location was not changed")
    if not username.strip() or len(password) < 12:
        raise ValueError("Username is required and password must be at least 12 characters")
    if target.exists() and any(target.iterdir()):
        raise ValueError("Choose an empty directory to avoid overwriting existing data")
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Check writability before committing either credentials or the location.
    with tempfile.TemporaryFile(dir=target):
        pass
    for name in ("models", "workspaces", "logs", "secrets"):
        (target / name).mkdir(mode=0o700, exist_ok=True)
    create_auth_file(target / "network-auth.json", username, password)
    temporary = pointer.with_suffix(".tmp")
    temporary.write_text(json.dumps({"data_dir": str(target)}, indent=2) + "\n", encoding="utf-8")
    temporary.replace(pointer)
    return target


def ensure_installation() -> Path:
    current = default_data_dir()
    if (current / "network-auth.json").is_file():
        return current
    if not sys.stdin.isatty():
        raise ValueError("Run alice --setup in an interactive terminal before starting Alice")
    print("Alice OS first-install setup")
    existing = (current / "settings.json").is_file()
    if existing:
        print(f"Keeping existing data at {current}. This setup will add an administrator login.")
        target = current
    else:
        print("Choose an external folder for models, conversations, memories, and workspaces.")
        target = Path(input(f"Data directory [{current}]: ").strip() or str(current))
    username = input("Administrator username: ").strip()
    password = getpass.getpass("Password (at least 12 characters): ")
    if password != getpass.getpass("Confirm password: "):
        raise ValueError("Passwords do not match")
    if existing:
        create_auth_file(target / "network-auth.json", username, password)
    else:
        override = os.environ.get("ALICE_HOME")
        if override and Path(override).expanduser().resolve() != target.expanduser().resolve():
            raise ValueError("Remove ALICE_HOME or select its directory so future launches use this installation")
        target = initialize_installation(target, username, password)
    print(f"Setup complete. Data: {target}\nManaged models: {target / 'models'}")
    return target
