import ipaddress
from unittest.mock import Mock

import pytest
import zeroconf

from alice_os import cli, installation, tls


@pytest.fixture(autouse=True)
def isolate_network_environment(monkeypatch):
    monkeypatch.setenv("ALICE_NETWORK_MODE", "")
    monkeypatch.setenv("ALICE_HTTPS", "")


@pytest.mark.parametrize("failure", [None, zeroconf.NonUniqueNameException(), OSError("adapter unavailable")])
def test_discovery_conflicts_do_not_prevent_server_start(monkeypatch, tmp_path, failure):
    monkeypatch.setattr("sys.argv", ["alice", "--host", "0.0.0.0", "--no-browser"])
    monkeypatch.setattr(installation, "ensure_installation", lambda: tmp_path)
    app = object()
    monkeypatch.setattr(cli, "create_app", lambda: app)
    monkeypatch.setattr(cli.socket, "gethostbyname_ex", lambda _: ("host", [], ["10.0.0.252"]))
    monkeypatch.setattr(tls, "_lan_ipv4_addresses", lambda: [ipaddress.ip_address("10.0.0.252")])
    discovery = Mock()
    discovery.register_service.side_effect = failure
    monkeypatch.setattr(zeroconf, "Zeroconf", lambda: discovery)
    run = Mock()
    monkeypatch.setattr(cli.uvicorn, "run", run)

    cli.main()

    assert discovery.register_service.call_args.kwargs == {"allow_name_change": True}
    run.assert_called_once_with(app, host="0.0.0.0", port=7788, log_level="info")
    discovery.close.assert_called_once()


def test_explicit_setup_reports_existing_location(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("sys.argv", ["alice", "--setup"])
    monkeypatch.setattr(installation, "ensure_installation", lambda: tmp_path)
    cli.main()
    assert str(tmp_path) in capsys.readouterr().out


@pytest.mark.parametrize("port, expected", [(None, 443), (8443, 8443)])
def test_lan_uses_https_standard_port_and_requested_hostname(monkeypatch, tmp_path, port, expected):
    from alice_os import network, tls
    argv = ["alice", "--lan", "--no-browser"]
    if port:
        argv += ["--port", str(port)]
    monkeypatch.setattr("sys.argv", argv)
    monkeypatch.setattr(installation, "ensure_installation", lambda: tmp_path)
    monkeypatch.setenv("ALICE_HOME", str(tmp_path))
    monkeypatch.setattr(tls, "ensure_tls_certificate", lambda *args: (tmp_path / "ca", tmp_path / "cert", tmp_path / "key"))
    monkeypatch.setattr(cli, "create_app", lambda: "app")
    monkeypatch.setattr(cli.socket, "gethostbyname_ex", lambda _: ("host", [], ["10.0.0.252"]))
    monkeypatch.setattr(tls, "_lan_ipv4_addresses", lambda: [ipaddress.ip_address("10.0.0.252")])
    discovery = Mock()
    monkeypatch.setattr(zeroconf, "Zeroconf", lambda: discovery)
    redirect = Mock()
    redirect_start = Mock(return_value=redirect)
    monkeypatch.setattr(network, "start_http_redirect", redirect_start)
    run = Mock()
    monkeypatch.setattr(cli.uvicorn, "run", run)
    cli.main()
    run.assert_called_once_with("app", host="0.0.0.0", port=expected, log_level="info",
                                ssl_certfile=str(tmp_path / "cert"), ssl_keyfile=str(tmp_path / "key"))
    redirect_start.assert_called_once_with("0.0.0.0", f"https://aliceos.local{':8443' if port else ''}")
    service = discovery.register_service.call_args.args[0]
    assert service.server == "aliceos.local."
    assert service.port == expected
    redirect.close.assert_called_once()
