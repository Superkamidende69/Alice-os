from __future__ import annotations

import ctypes
import os
from pathlib import Path


class SecretStoreError(RuntimeError):
    """Raised when a host-local secret cannot be protected or unlocked."""


_WINDOWS_MAGIC = b"ALICE-DPAPI-1\n"
_FALLBACK_MAGIC = b"ALICE-LOCAL-1\n"


if os.name == "nt":
    from ctypes import wintypes

    class _DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

    _crypt_protect = ctypes.WinDLL("crypt32", use_last_error=True).CryptProtectData
    _crypt_protect.argtypes = [
        ctypes.POINTER(_DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    _crypt_protect.restype = wintypes.BOOL

    _crypt_unprotect = ctypes.WinDLL("crypt32", use_last_error=True).CryptUnprotectData
    _crypt_unprotect.argtypes = [
        ctypes.POINTER(_DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_DataBlob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_DataBlob),
    ]
    _crypt_unprotect.restype = wintypes.BOOL

    _local_free = ctypes.WinDLL("kernel32", use_last_error=True).LocalFree
    _local_free.argtypes = [wintypes.HLOCAL]
    _local_free.restype = wintypes.HLOCAL


def _windows_protect(value: bytes) -> bytes:
    source_buffer = ctypes.create_string_buffer(value)
    source = _DataBlob(
        len(value), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte))
    )
    protected = _DataBlob()
    if not _crypt_protect(
        ctypes.byref(source),
        "Alice OS Hugging Face token",
        None,
        None,
        None,
        0,
        ctypes.byref(protected),
    ):
        raise SecretStoreError(f"Windows could not protect the token (error {ctypes.get_last_error()})")
    try:
        return ctypes.string_at(protected.pbData, protected.cbData)
    finally:
        if protected.pbData:
            _local_free(ctypes.cast(protected.pbData, wintypes.HLOCAL))


def _windows_unprotect(value: bytes) -> bytes:
    source_buffer = ctypes.create_string_buffer(value)
    source = _DataBlob(
        len(value), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte))
    )
    unprotected = _DataBlob()
    description = wintypes.LPWSTR()
    if not _crypt_unprotect(
        ctypes.byref(source),
        ctypes.byref(description),
        None,
        None,
        None,
        0,
        ctypes.byref(unprotected),
    ):
        raise SecretStoreError(f"Windows could not unlock the token (error {ctypes.get_last_error()})")
    try:
        return ctypes.string_at(unprotected.pbData, unprotected.cbData)
    finally:
        if description:
            _local_free(ctypes.cast(description, wintypes.HLOCAL))
        if unprotected.pbData:
            _local_free(ctypes.cast(unprotected.pbData, wintypes.HLOCAL))


class SecretStore:
    """A small host-local secret store for credentials used by Alice."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self) -> str | None:
        try:
            payload = self.path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError as error:
            raise SecretStoreError("The saved secret could not be read") from error
        if not payload:
            return None
        try:
            if os.name == "nt":
                if not payload.startswith(_WINDOWS_MAGIC):
                    raise SecretStoreError("The saved secret uses an unsupported format")
                value = _windows_unprotect(payload[len(_WINDOWS_MAGIC):])
            else:
                if not payload.startswith(_FALLBACK_MAGIC):
                    raise SecretStoreError("The saved secret uses an unsupported format")
                value = payload[len(_FALLBACK_MAGIC):]
            token = value.decode("utf-8").strip()
        except UnicodeDecodeError as error:
            raise SecretStoreError("The saved secret is not valid text") from error
        return token or None

    def set(self, value: str) -> None:
        token = value.strip()
        if not token:
            raise ValueError("A token is required")
        if os.name == "nt":
            payload = _WINDOWS_MAGIC + _windows_protect(token.encode("utf-8"))
        else:
            payload = _FALLBACK_MAGIC + token.encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.tmp")
        try:
            temporary.write_bytes(payload)
            try:
                temporary.chmod(0o600)
            except OSError:
                pass
            temporary.replace(self.path)
            try:
                self.path.chmod(0o600)
            except OSError:
                pass
        except OSError as error:
            raise SecretStoreError("The token could not be saved on this host") from error

    def clear(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError as error:
            raise SecretStoreError("The saved token could not be cleared") from error
