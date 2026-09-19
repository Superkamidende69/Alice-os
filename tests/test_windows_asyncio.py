import asyncio
import sys
from types import SimpleNamespace, TracebackType
from unittest.mock import Mock

import pytest

from alice_os.windows_asyncio import install_connection_reset_handler, recover_connection_reset

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows Proactor workaround")


def reset_error():
    error = ConnectionResetError("Peer reset")
    error.winerror = 10054
    return error


def test_reset_cleanup_closes_socket_detaches_server_and_notifies_protocol_once():
    from asyncio.proactor_events import _ProactorBasePipeTransport

    transport = object.__new__(_ProactorBasePipeTransport)
    transport._called_connection_lost = False
    transport._sock = sock = Mock()
    sock.fileno.return_value = 42
    sock.shutdown.side_effect = reset_error()
    transport._server = server = Mock()
    transport._protocol = protocol = Mock()
    transport._closing = True
    try:
        transport._call_connection_lost(None)
    except ConnectionResetError as error:
        # Native socket.shutdown adds no Python frame. Remove the Mock frames
        # to reproduce the real traceback supplied by Windows' socket module.
        tb = error.__traceback__
        while tb.tb_frame.f_code is not _ProactorBasePipeTransport._call_connection_lost.__code__:
            tb = tb.tb_next
        error.__traceback__ = TracebackType(None, tb.tb_frame, tb.tb_lasti, tb.tb_lineno)
        context = {"exception": error, "handle": SimpleNamespace(_callback=transport._call_connection_lost)}
        assert recover_connection_reset(context)
        assert not recover_connection_reset(context)  # Idempotent; no second detach.
    sock.close.assert_called_once()
    server._detach.assert_called_once_with(transport)
    protocol.connection_lost.assert_called_once_with(None)
    assert transport._sock is None
    assert transport._called_connection_lost


@pytest.mark.asyncio
async def test_unrelated_errors_preserve_previous_handler_and_restore():
    loop = asyncio.get_running_loop()
    original = loop.get_exception_handler()
    previous = Mock()
    loop.set_exception_handler(previous)
    restore = install_connection_reset_handler()
    try:
        contexts = [
            {"exception": reset_error(), "handle": SimpleNamespace(_callback=lambda: None)},
            {"exception": RuntimeError("Actual failure")},
            {"message": "Something else"},
        ]
        for context in contexts:
            loop.call_exception_handler(context)
        assert previous.call_count == len(contexts)
        restore()
        assert loop.get_exception_handler() is previous
    finally:
        restore()
        loop.set_exception_handler(original)
