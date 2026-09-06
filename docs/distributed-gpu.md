# One model across multiple GPUs and machines

## Recommended: use the Alice interface

No SSH commands are required for paired Alice GPU workers.

1. Install/open the Tailscale app on each PC and sign into the same tailnet.
   Keep Tailscale connected and use its device list to copy each worker's IPv4
   address. Start the updated Alice application on each machine in HTTPS LAN mode.
2. On a worker, open **Cluster → Share this machine's GPU**. Select the GPU and
   click **Start GPU sharing**. A full model service need not be running there.
3. On that worker, click **Create pairing code** and expand **Worker CA certificate**.
4. On the controller's Cluster page, choose **Add a worker**, enter its HTTPS
   address using the IP copied from Tailscale, and paste the pairing code and public
   CA certificate. Pair the machine. Existing pairings can be reused.
5. Under **Use multiple GPUs for one model**, select the paired workers, click
   **Check GPUs**, enable distributed loading, and save.
6. Open **Models** and load the GGUF again. The controller includes its local GPU
   and connects to the chosen workers automatically.

If Tailscale was installed after Alice started, restart Alice on that worker so
its certificate includes the new address. Alice's HTTPS port must be reachable
over Tailscale; certificate trust and Windows firewall setup are still required.
Tailscale does not install the Alice application or configure its OS firewall.

The **Stop sharing** button disconnects GPU clients and stops the worker process.
Revoking a controller disconnects its GPU streams. GPU sharing starts off after
restarting Alice; start it again using the UI, then reload the controller's model.
Saved worker selections persist, but live model execution does not automatically
recover from restarting either Alice instance.

Alice carries binary GPU RPC over authenticated, certificate-verified WebSockets
between paired machines. The native GPU worker and controller-side adapters bind
only to loopback. Pairing grants access only to resources the worker has explicitly
enabled. The existing experimental RPC runtime still requires trusted machines.

## Advanced: manually managed SSH tunnels

The remainder of this guide describes the optional manual transport. Use the
graphical workflow above for normal paired Alice workers.

Alice now has an experimental GGUF model-splitting mode. The controller runs one
llama.cpp server; selected model layers execute on remote GPU devices through
RPC. The resulting model appears as the usual Alice-managed provider in Chat.
This is separate from pairing whole inference workers, which execute independent
requests rather than splitting one model.

The bundled Windows runtime was checked: llama.cpp build 10752, commit b96806d96,
with RPC protocol v6.0.0 and CUDA support. Use matching runtime builds on all
machines, with a backend compatible with each GPU. Installed runtime versions
can change, so compare the actual executables before connecting them.

The upstream RPC backend is experimental and unauthenticated. Alice accepts only
loopback endpoints for manually configured tunnels. Keep those RPC servers on loopback and
use authenticated SSH port forwarding between trusted machines. Alice's existing
HTTPS pairing can now carry RPC through Alice's authenticated transport; the manual
transport below uses SSH instead. See the
[upstream RPC documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md).

## 1. Start each GPU worker

On a Windows worker with this Alice runtime installed:

```powershell
.\scripts\start-gpu-worker.cmd
```

This exposes `CUDA0` at `127.0.0.1:50052`, accessible locally only. Keep the
terminal open. To choose multiple devices, pass `-Device CUDA0,CUDA1`. Check
the native runtime's device names first; workers with other GPU backends need
a compatible build and the correct device identifiers.

For Linux or other supported platforms, use the matching native runtime:

```sh
ggml-rpc-server --host 127.0.0.1 --port 50052 --device CUDA0
```

The worker must also have a separately configured SSH server and an account
that allows port forwarding. These scripts do not install SSH, create accounts,
distribute private keys, or expose the RPC port through the firewall.

## 2. Open tunnels from the controller

For the first remote GPU machine, replace `user@worker-one` with its actual SSH
account/address:

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -L 127.0.0.1:50053:127.0.0.1:50052 user@worker-one
```

Use a different local port for a second remote machine:

```powershell
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -L 127.0.0.1:50054:127.0.0.1:50052 user@worker-two
```

Verify each SSH host identity and authenticate normally. Keep the tunnels open
throughout model loading and generation. Do not map the same physical GPU into
the cluster twice, including through both a local device and a loopback RPC server.

## 3. Configure Alice

Open **Cluster → Split a GGUF model across machines** on the controller.

1. Enter `127.0.0.1:50053` and any other tunnel endpoints, one per line.
2. Click **Check GPUs**. Each endpoint must appear as an RPC device alongside the
   controller's local devices.
3. Enable distributed model loading and save.
4. Open **Models** and load the desired GGUF again, even if it is already loaded.
5. Select the Alice-managed model in Chat.

Alice supplies `--rpc` and `--split-mode layer`; allocation across available
devices is handled by llama.cpp. Settings are stored in `distributed.json` in
Alice's data directory. Model loading probes all configured workers before
stopping an existing managed model. Changing settings alone does not interrupt
the running model. Disabling the setting and loading again returns to local
inference. The standard launch scripts also read the saved settings when starting
a model server; establish the tunnels before using those launchers.

## Expectations and limits

- The full GGUF stays on the controller, which also needs enough host memory for
  runtime/model loading. GPU memory must also fit inference working memory and KV
  cache; adding VRAM sizes does not precisely predict the largest usable model.
- Model loading can transfer many gigabytes. Distributed loading allows up to
  30 minutes before timing out. Wired networking is preferable; measure actual
  performance with your machines before relying on it for interactive use.
- Splitting can increase the model size you can run, but is not a guaranteed
  speedup. Slow networks and uneven GPUs can increase latency.
- A lost tunnel or worker can fail the whole inference run. There is no automatic
  failover, checkpoint recovery, or automatic restart of SSH tunnels.
- Stop other GPU workloads when necessary to leave memory for the shared model.
- Ollama and ordinary paired inference providers are unaffected by this mode.

Validation includes settings/authentication tests, native GPU/RPC discovery on
the local RTX 3050, and tests that unreachable workers do not terminate an
existing model. The local RPC check uses the same GPU twice for discovery only;
it does not demonstrate extra VRAM or multi-machine inference. A real split-model
test remains dependent on a second machine, its SSH connection, and a chosen model.
