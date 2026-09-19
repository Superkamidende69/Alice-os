"""Recover a specific Python Proactor socket-close failure on Windows."""
from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Callable

logger = logging.getLogger(__name__)


def recover_connection_reset(context: dict) -> bool:
    error = context.get("exception")
    if not isinstance(error, ConnectionResetError) or getattr(error, "winerror", None) != 10054:
        return False
    handle = context.get("handle")
    callback = getattr(handle, "_callback", None)
    from asyncio.proactor_events import _ProactorBasePipeTransport

    transport = getattr(callback, "__self__", None)
    if not isinstance(transport, _ProactorBasePipeTransport):
        return False
    if getattr(callback, "__func__", None) is not _ProactorBasePipeTransport._call_connection_lost:
        return False
    # Only recover shutdown() raising in asyncio itself, not a protocol callback.
    traceback = error.__traceback__
    if traceback is None:
        return False
    while traceback.tb_next is not None:
        traceback = traceback.tb_next
    frame = traceback.tb_frame
    if frame.f_code is not _ProactorBasePipeTransport._call_connection_lost.__code__:
        return False
    if frame.f_locals.get("self") is not transport or transport._called_connection_lost:
        return False
    # shutdown raised before Python could close the socket or detach from Server.
    # Finish that tail once; do not invoke protocol.connection_lost a second time.
    try:
        if transport._sock is not None:
            transport._sock.close()
            transport._sock = None
        if transport._server is not None:
            transport._server._detach(transport)
            transport._server = None
        transport._called_connection_lost = True
    except Exception:
        logger.exception("Could not finish Windows reset-connection cleanup")
        return False
    logger.debug("Finished cleanup after Windows socket shutdown reset (10054)")
    return True


def install_connection_reset_handler() -> Callable[[], None]:
    """Scope the workaround to Alice's event loop and preserve its prior handler."""
    if sys.platform != "win32":
        return lambda: None
    loop = asyncio.get_running_loop()
    previous = loop.get_exception_handler()

    def handler(active_loop, context):
        if recover_connection_reset(context):
            return
        if previous is not None:
            previous(active_loop, context)
        else:
            active_loop.default_exception_handler(context)

    loop.set_exception_handler(handler)

    def restore():
        if loop.get_exception_handler() is handler:
            loop.set_exception_handler(previous)

    return restore
