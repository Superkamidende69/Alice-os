from __future__ import annotations

import ipaddress
import json
import os
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psutil


def _lan_ipv4_addresses() -> list[ipaddress.IPv4Address]:
    addresses: list[ipaddress.IPv4Address] = []
    try:
        stats = psutil.net_if_stats()
        candidates = [
            entry.address
            for name, entries in psutil.net_if_addrs().items()
            if name in stats and stats[name].isup
            and not any(part in name.casefold() for part in (
                "vethernet", "loopback", "docker", "vbox", "vmware", "wsl"
            ))
            for entry in entries if entry.family == socket.AF_INET
        ]
    except (OSError, psutil.Error):
        candidates = []
    for candidate in candidates:
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if (isinstance(address, ipaddress.IPv4Address) and not address.is_loopback
                and not address.is_link_local and not address.is_unspecified):
            addresses.append(address)
    return sorted(set(addresses))


def ensure_tls_certificate(data_dir: Path, hostname: str) -> tuple[Path, Path, Path]:
    """Create a private local CA and a server certificate for Alice's LAN name."""
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError as error:
        raise RuntimeError(
            "HTTPS support needs the cryptography package. Run .\\scripts\\setup.cmd, then retry."
        ) from error

    tls_dir = data_dir / "tls"
    tls_dir.mkdir(parents=True, exist_ok=True)
    ca_key_path = tls_dir / "alice-local-ca.key"
    ca_cert_path = tls_dir / "alice-local-ca.crt"
    server_key_path = tls_dir / "alice-server.key"
    server_cert_path = tls_dir / "alice-server.crt"
    metadata_path = tls_dir / "alice-server.json"
    names = sorted({hostname, "localhost"})
    addresses = _lan_ipv4_addresses() + [ipaddress.ip_address("127.0.0.1")]
    metadata = {"hostname": hostname, "names": names, "addresses": [str(ip) for ip in addresses],
                "certificate_version": 2}

    if (
        ca_cert_path.is_file()
        and ca_key_path.is_file()
        and metadata_path.is_file()
        and server_key_path.is_file()
        and server_cert_path.is_file()
    ):
        try:
            if json.loads(metadata_path.read_text(encoding="utf-8")) == metadata:
                existing = x509.load_pem_x509_certificate(server_cert_path.read_bytes())
                if existing.not_valid_after_utc > datetime.now(timezone.utc) + timedelta(days=30):
                    return ca_cert_path, server_cert_path, server_key_path
        except (OSError, ValueError):
            pass

    if ca_key_path.is_file() and ca_cert_path.is_file():
        ca_key = serialization.load_pem_private_key(ca_key_path.read_bytes(), password=None)
        ca_cert = x509.load_pem_x509_certificate(ca_cert_path.read_bytes())
        ca_subject = ca_cert.subject
        try:
            ca_cert.extensions.get_extension_for_class(x509.KeyUsage)
            ca_cert.extensions.get_extension_for_class(x509.SubjectKeyIdentifier)
        except x509.ExtensionNotFound:
            ca_cert = None
    else:
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        ca_subject = x509.Name(
            [
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Alice OS"),
                x509.NameAttribute(NameOID.COMMON_NAME, "Alice OS Local CA"),
            ]
        )
        ca_cert = None
    if ca_cert is None:
        now = datetime.now(timezone.utc)
        ca_cert = (
            x509.CertificateBuilder()
            .subject_name(ca_subject)
            .issuer_name(ca_subject)
            .public_key(ca_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
            .add_extension(x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=True,
                crl_sign=True, encipher_only=False, decipher_only=False,
            ), critical=True)
            .sign(ca_key, hashes.SHA256())
        )
        ca_key_path.write_bytes(
            ca_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )
        ca_cert_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))

    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
    subject_alternative_names = [x509.DNSName(name) for name in names]
    subject_alternative_names.extend(x509.IPAddress(address) for address in addresses)
    now = datetime.now(timezone.utc)
    server_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(
            x509.SubjectAlternativeName(subject_alternative_names), critical=False
        )
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False, key_encipherment=True,
            data_encipherment=False, key_agreement=False, key_cert_sign=False,
            crl_sign=False, encipher_only=False, decipher_only=False,
        ), critical=True)
        .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    server_key_path.write_bytes(
        server_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    server_cert_path.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    for path in (ca_key_path, server_key_path):
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    return ca_cert_path, server_cert_path, server_key_path
