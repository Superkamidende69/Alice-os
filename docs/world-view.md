# God’s Eye View in Alice

Alice integrates [God’s Eye View by Bilawal Sidhu](https://github.com/bilawalsidhu/gods-eye-view)
as an optional, independently installed local module. The sidebar and command
palette open **World View** (`/world`), which provides authenticated Start, Stop,
and status controls. Say **Open World View** or **Open the globe** to navigate
there through Alice’s voice controls.

## Installation on Windows x64

From the Alice checkout:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup-gods-eye.ps1
```

This downloads upstream commit `a65d9d85f1faa06ae7df235d7fa8a29b026b7a5b` and
Node 24.14.0 into the ignored `tools/` directory. The Node archive is checked
against its official SHA-256 manifest. Dependencies use upstream's lockfile
with installation scripts disabled. Existing modified upstream checkouts are
left alone. Installation requires Git, internet access, and Windows x64.

Restart Alice after updating its source, then open World View and select
**Start globe → Open globe**. The service binds to `127.0.0.1:4173` with strict
port selection. If another service owns that port, Alice reports the conflict
without adopting or terminating it. Alice stops only the process it launched
and its children. Logs are under `ALICE_HOME/logs/gods-eye-view.log`.
An abrupt crash of Alice can leave the Node service running; close that specific
service before starting it again. There is no automatic start or background
download when opening Alice.

For a separately installed checkout, set `ALICE_GODS_EYE_HOME` to its directory
and put a supported Node runtime on PATH. For a packaged Alice EXE, install the
module into a `tools` directory beside that EXE or set the same override.
The third-party checkout and Node installation are not bundled into Alice's EXE.

## What is integrated

The complete upstream application runs in its own tab. Its frame-denial headers
and local-only provider settings remain intact. The local launch controls are
unavailable from other computers; open Alice on its host computer. The host's own
LAN and IPv6 interface addresses are recognized, so using `aliceos.local` or
the PC's own Ethernet address works too. Other authenticated devices receive a
clear host-only status without repeated 403 polling; their Start/Stop calls
remain forbidden.
Alice’s model credentials are not passed to the child process.

The upstream keyless basemap and public feeds can be used immediately. Additional
providers are configured inside the globe's **POWER UP** panel; those credentials
are stored by upstream in its ignored local `.env`. Photorealistic maps, vessels,
fires, and upstream realtime voice have their own provider requirements. Alice’s
local voice navigates to the launch page; it does not yet control the globe’s
camera or expose live scene data to Alice’s model.

Internet access is needed for maps and live data. Traffic and some other overlays
are simulations or estimates as labeled upstream. Availability and refresh rates
depend on public sources, credentials, and quotas.

## Attribution

Source code: Copyright (c) 2026 Bilawal Sidhu, MIT. Upstream's full LICENSE is
preserved in the installed checkout. Data and assets have separate terms, including
noncommercial restrictions for some bundled datasets and imagery. Consult the
[upstream LICENSE](https://github.com/bilawalsidhu/gods-eye-view/blob/a65d9d85f1faa06ae7df235d7fa8a29b026b7a5b/LICENSE)
and DATA_SOURCES.md before redistributing or using those assets commercially.
