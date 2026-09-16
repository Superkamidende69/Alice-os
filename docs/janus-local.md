# Janus-Pro-1B local runtime

Model: `deepseek-community/Janus-Pro-1B`

Downloaded revision: `1655280bb75959cc1cb85529a2a8b26e7016072e`.
Repository files: 4,161,753,391 bytes. Weight file: 4,153,396,574 bytes.
Verified weight SHA-256: `9d1a416f95fb58d6e02858623c9c676003d66006d51fb5d5cc93348ba78cb942`.

Files live in `.alice-data/models/huggingface/deepseek-community--Janus-Pro-1B`.
The dedicated environment is `.venv-janus`; Alice's main `.venv` is unchanged.

## Requirements

- Python 3.13 (the host uses 3.13.7).
- CUDA-enabled PyTorch 2.9.1 and torchvision 0.24.1, CUDA 12.8 wheels.
- Transformers 4.57.6, Accelerate, Pillow, Safetensors; see `scripts/requirements-janus.txt`.
- An NVIDIA driver compatible with the wheel's CUDA runtime. A separate CUDA development toolkit is not needed for these prebuilt wheels.
- About 4.16 GB for the model plus the Python environment, CUDA libraries, and installation cache.
- GPU memory beyond the roughly 3.87 GiB of BF16 weights is needed for activations and generation. The smoke test conservatively requires 5 GiB free; that is a test guard, not a guarantee for arbitrary image or batch workloads.

## Recreate / test (PowerShell, repository root)

```powershell
.venv/Scripts/python.exe -m venv .venv-janus
.venv-janus/Scripts/python.exe -m pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu128
.venv-janus/Scripts/python.exe -m pip install -r scripts/requirements-janus.txt
.venv-janus/Scripts/python.exe scripts/janus-smoke.py
```

The test only reads local model files, runs a short text response, and exits.
It does not stop another model server or change Alice's selected provider.
Janus supports text/image understanding and image generation through its Transformers processor.
## Alice chat integration

## Image generation (verified 2026-09-13)

Click **Create image** beside the composer, describe the scene, and choose
**Generate image**. Janus must be running first. The dialog displays the result
and offers **Download PNG**. Outputs are saved in `.alice-data/generated-images`
and served only through authenticated Alice requests. Generation and chat share
one GPU slot; a busy service returns a retry message rather than queuing work.
Keep the browser page open until it completes; the dialog itself can be closed
and reopened during generation.

A real end-to-end test generated a 384×384 PNG (257,871 bytes), retrieved it
through Alice's authenticated image endpoint, and visually verified the result.
Restart Alice after updating its API/UI code. The image-enabled Janus service
was left running. This adds text-to-image generation, not image-input chat.

### Chat details

Verified 2026-09-13: both Alice's provider adapter and a complete RunManager
conversation returned "Hello! How can I assist you today?". The run completed
in one step with workspace tools disabled. The local service was left running.

Restart Alice after updating the source. Under Models → Installed, select
`deepseek-community/Janus-Pro-1B` and choose Load model. Alice starts
`scripts/janus-server.py` with the dedicated environment on loopback port 8082,
waits for readiness, and registers `Janus Pro · local text chat` as a provider.
Select `Janus-Pro-1B` in the composer. Workspace-agent tools are disabled for
this provider. This first adapter supports text chat only, with a 4096-token
input limit and up to 256 new tokens per response. Replies currently arrive as
one completed chunk, not token-by-token.

The Installed model details include Stop Janus to release its GPU memory.
The stop endpoint checks process ownership and refuses while Alice has an
active response. Other model servers are never stopped to make space for Janus.
Initial loading can take several minutes. Startup errors are in
`.alice-data/logs/janus-server.log`. The service remains local-only and can stay
running across an Alice restart; after a PC reboot, load the model again.

## Verified on this host (2026-09-11)

Package check: no broken requirements. Offline text generation passed on the
RTX 3050 (8 GiB) with 7.03 GiB free at startup. Response:
"Hello! How can I assist you today?"

Peak PyTorch GPU allocation: 3.89 GiB. Loading and generation together took
140.0 seconds, excluding the slow initial Python library imports. This is not
a warm inference benchmark. The test exited successfully and released the model.
Image understanding and image generation were not tested.

References: https://huggingface.co/docs/transformers/model_doc/janus and https://pytorch.org/get-started/previous-versions/.
