"""Locations for source checkouts and PyInstaller bundles."""
from __future__ import annotations

import sys
from pathlib import Path


def bundled() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    if bundled():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]
