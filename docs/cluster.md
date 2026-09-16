# Alice inference cluster — first release

The same Alice installation can act as a controller, an inference worker, or both.
A controller sends model requests to explicitly paired workers. Conversations,
memory, tool approvals, and tool execution remain on the controller. Select the
worker's model in the existing Chat model picker; dispatch is manual in this release.

## Connect two machines

### Join an existing Alice network (recommended)

On a new worker, start Alice in HTTPS LAN mode and open **Cluster**. Enable GPU
or inference sharing, then choose **Join an existing Alice network**. Enter the
main host's HTTPS address and the username and password already used on that
main host. Give the worker an address reachable by the main host; paste the
main host's public CA certificate if it is not already trusted.

Alice sends the password directly to the main host over HTTPS for that one
request, creates a short-lived pairing code in memory, and immediately pairs
the worker. The password is not saved on the worker or in cluster settings.
Afterward the main host retains only a dedicated, revocable worker credential,
so the worker connects automatically whenever both machines are online.

### Manual pairing

1. Install this version of Alice on both machines. On the worker, start a local
   Ollama, llama.cpp, or other supported model service and confirm that it can
   answer a normal local Alice conversation. Models stay on the worker's disk.
2. Start the worker in Alice's existing HTTPS LAN mode. For example, from the
   repository root on Windows:

   ```powershell
   .\.venv\Scripts\python.exe -m alice_os --lan --hostname alice-worker.local --no-browser
   ```

   On Linux, use `.venv/bin/python` instead. Complete Alice's normal installation
   and administrator setup if prompted. Give each machine a distinct hostname.
   The worker's TCP port (443 by default for HTTPS) must be reachable through its firewall
   from the controller. The model service itself can remain bound to loopback.
3. Open the worker's Alice UI, sign in, and select **Cluster** in the sidebar.
   Choose the local provider to share, enable the inference worker, choose a
   concurrency limit, and save. One concurrent request is a good starting value.
4. Click **Create pairing code**. Expand **Worker CA certificate** and copy its
   public PEM certificate directly from this trusted worker. Codes expire after
   five minutes and are consumed once. Creating a new code invalidates the old one.
5. On the main controller, open **Cluster**. Enter a connection name, the worker's
   HTTPS origin (for example `https://alice-worker.local`), its pairing code,
   and its public CA certificate. Click **Pair worker**. The controller can retain
   its normal local-only browser interface; only the worker needs an inbound LAN
   listener for this connection.
6. Open **Chat** on the controller and choose the worker's model. Model text and
   tool requests stream back through the existing conversation interface.

If `.local` resolution is unavailable, use the worker's LAN IP, provided that IP
is included in its certificate. For publicly trusted certificates, the custom CA
field can be left blank. TLS certificate and hostname verification are always
enabled; no insecure verification bypass is provided. Older Alice certificates
are upgraded on HTTPS startup for strict TLS clients; copy the current public CA
from the worker after restarting it.

## Management and behavior

- **Refresh status** probes paired workers and shows models, logical CPU count,
  available system RAM, active inference requests, and the configured limit.
  These are status observations, not promises of dedicated resources or GPU fit.
- A full worker rejects additional requests with a busy message. Select another
  worker or retry later. Requests are not silently rerouted or replayed.
- Stopping a controller run closes its worker stream and cancels the worker's
  provider request. A native model server may continue computation until it
  notices the closed request; immediate GPU interruption is backend-dependent.
- Changing worker settings cancels existing worker requests. Disabling sharing
  denies future inference and invalidates any outstanding pairing code.
- **Revoke** on the worker invalidates that controller's credential and cancels
  its active requests. Other controllers remain authorized.
- **Remove** on the controller forgets the worker, its saved credential, and its
  provider entry. To revoke authorization at the worker too, use **Revoke** there.
- Pairings and settings survive restarts. Active requests do not resume after a
  restart or disconnect. Historical conversations remain on the controller.

## Implementation and boundaries

`cluster.py` provides versioned worker status, one-time pairing, HTTPS clients,
bounded token buffering, and inference request admission. `agent.py` dispatches
cluster provider turns through that client. The worker uses Alice's existing
provider adapter to call only the explicitly selected loopback provider.

`<ALICE_HOME>/cluster.json` stores settings, node addresses, public CA certificates,
and controller credential hashes. Outbound bearer credentials use Alice's existing
host-local `SecretStore`: Windows DPAPI on Windows; permission-restricted local
files on other platforms. No credentials are exposed in the Cluster overview or
normal provider settings. Worker routes use their own bearer authentication,
separate from the browser session. Management routes require the existing Alice
browser authentication and origin checks.

Workers receive the model context needed for the request, including any memory
or file content the controller has put into that context. Pair only machines you
intend to trust with that information. Worker responses and tool requests still
pass through the controller's existing workspace and approval enforcement.

For experimental single-model GPU splitting, see [distributed GPUs](distributed-gpu.md).

This release does not implement automatic LAN discovery of workers, capability
scheduling, a durable job queue, remote shell/file tools, project transfer, GPU
inventory, general RAM/VRAM pooling, or controller failover. Joining an
existing network creates the secure controller-to-worker connection from an
address supplied by the owner; it does not discover arbitrary machines. SQLite
remains local to each Alice instance.

## Validation

Run `.venv/Scripts/python.exe -m pytest tests/test_cluster.py -q` on Windows.
The tests exercise paired controller-to-worker conversations, streamed tokens and
tool calls, invalid/replayed/expired credentials, revocation, persistence,
concurrency, cancellation, and real loopback HTTPS with generated certificates.
Model inference is stubbed for deterministic tests; physical multi-PC throughput
and a real model backend require a LAN deployment check.
