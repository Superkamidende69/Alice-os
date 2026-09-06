# Alice at https://aliceos.local

The main controller advertises `aliceos.local` on the local network. HTTPS uses
port 443, so the address needs no port suffix. In LAN mode, a separate listener
on port 80 redirects browser GET/HEAD requests to the fixed HTTPS address; it
does not accept login submissions. Upper/lowercase in the hostname is equivalent.

## Windows host setup

After configuring the Alice administrator normally, open PowerShell **as
Administrator** and run this once from the Alice repository:

```powershell
.\scripts\setup-network.cmd
```

This prepares the certificate, trusts the public CA on the host, and creates
firewall rules for TCP 80/443 and UDP 5353, restricted to Alice's Python executable
and clients on the local subnet. Rules cover all network profiles, including
Windows Public profiles; the script does not change the network's category.
The CMD launcher sets execution policy only for its PowerShell process, so it
also works when the system's default policy disables direct PS1 execution.

Start Alice using:

```powershell
.\scripts\start-network.cmd
```

The equivalent Python command is `python -m alice_os --lan`. The usual local-only
launch remains available. `--https` defaults to 443; an explicit `--port` overrides
that default. `--lan` additionally binds the LAN interface and enables the HTTP
redirect. The host must remain running for other devices to reach Alice; these
scripts do not install a Windows service or automatically start Alice at boot.

## Trust on client devices

A private `.local` name uses a private CA. Each device must trust Alice's public
CA once; the server cannot install trust remotely. Copy only
`<ALICE_HOME>/tls/alice-local-ca.crt` from this trusted host. Never distribute
`alice-local-ca.key` or `alice-server.key`.

On Windows, import that certificate into **Trusted Root Certification
Authorities** for the current user (or the machine if an administrator manages
it). Restart the browser if needed. On Apple mobile devices, install the public
certificate profile and enable its full trust under Settings → General → About
→ Certificate Trust Settings. Other operating systems/browser stores have their
own CA import procedures.

The host setup script installs trust only on the host. Without the client trust
step, another device may resolve the name and connect but show a certificate
warning. Browser certificate verification should remain enabled.

References: [private CA certificates](https://letsencrypt.org/docs/certificates-for-localhost/)
and [Apple certificate trust](https://support.apple.com/en-us/102390).

## Name resolution and multiple Alice machines

Reserve `aliceos.local` for one main controller. Start other workers with unique
names, such as `--lan --hostname alice-worker-2.local`. Starting several hosts
with the same name does not create automatic controller failover.

mDNS requires clients on the same multicast-capable network segment. Guest Wi-Fi
isolation, VLAN boundaries, and devices without mDNS support can prevent name
resolution. Such networks need a router/network administrator to provide suitable
name resolution or multicast forwarding; changing the Alice server alone cannot
guarantee access from every network. No router port forwarding is needed.

Virtual Hyper-V/WSL, Docker, VMware, and VirtualBox adapters are excluded from
advertised IPv4 addresses. Certificates are regenerated when LAN addresses change
or server-certificate expiry is within 30 days, keeping the same existing CA key.
If ports 80 or 443 are occupied, resolve that conflict; Alice does not terminate
unrelated services. If port 80 is unavailable, use the explicit HTTPS address.
