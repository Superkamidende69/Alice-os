# Alice OS

Alice OS is a local-first, Codex-style AI operator with a browser interface,
workspace tools, streamed responses, durable conversations, and explicit
approval before file writes or process launches. It can talk to Ollama, import
local GGUF files through Ollama, or connect to a service that implements the
OpenAI Chat Completions protocol.

Alice is an independent project. It is inspired by the interaction model of
coding agents and fictional desktop assistants; it is not OpenAI Codex and is
not affiliated with the fictional JARVIS.

## What works

- Local browser UI served only on `127.0.0.1`.
- Native Ollama model discovery and streaming chat.
- GGUF registration through `ollama create`.
- Hugging Face link inspection, full repository downloads, and one-file GGUF import.
- Local model library for Ollama-ready models and downloaded Hugging Face files.
- Custom OpenAI-compatible Chat Completions endpoints.
- Conversation history and per-conversation memories in SQLite.
- Codex-style workspace browser with read-only file previews, Git status, and
  one-click file context for a conversation.
- Workspace listing, UTF-8 file reads, and text search.
- Approval-gated UTF-8 file replacement and argv-based process execution.
- Native function calling, with a JSON compatibility mode for servers that
  reject tool definitions.
- Run cancellation, streamed status/tool events, and loop circuit breakers.
- Optional browser speech-to-text dictation when the browser exposes the Web
  Speech Recognition API.
- Optional local OpenVoice/MeloTTS spoken replies, with an isolated runtime.

Alice is currently a text and workspace agent; dictation only fills the message
box. It does not yet provide a general desktop-control layer, wake-word service,
image input, RAG index, MCP client, or an OS-level command sandbox.

## Requirements

- Python 3.11 or newer.
- Ollama for the built-in local provider, model pulls, and GGUF import.
- A modern browser.
- Internet access during setup unless the Python dependencies are already in a
  local package cache.

The audited Windows machine has Python 3.13, Ollama, an RTX 3050 with 8 GiB of
VRAM, 16 GiB of system RAM, and a Ryzen 5 5500. A 3B-8B model in a Q4
quantization is the practical starting range on this hardware. A 7B or 8B
Q4_K_M GGUF usually offers the best capability/speed balance. Larger models may
spill into system RAM, become much slower, or fail at longer context lengths.

## Quick start on Windows

Open PowerShell in `I:\Alice-os`:

```powershell
.\scripts\setup.cmd
.\scripts\start.cmd
```

Setup creates `.venv`, installs Alice and its test dependencies in editable
mode, and checks whether Ollama is available. It deliberately does not download
a model. The start script opens `http://127.0.0.1:7788` and stores Alice data in
`I:\Alice-os\.alice-data` unless `ALICE_HOME` is set.

Useful launch variants:

```powershell
.\scripts\start.cmd -Port 7799
.\scripts\start.cmd -NoBrowser
```

To install runtime dependencies without pytest:

```powershell
.\scripts\setup.cmd -WithoutDev
```

If you prefer to invoke PowerShell directly, use
`powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1`.

## Quick start on Linux or macOS

```bash
bash scripts/setup.sh
bash scripts/start.sh
```

Arguments after `start.sh` go to Alice's CLI:

```bash
bash scripts/start.sh --port 7799 --no-browser
```

## Ollama first run

Alice does not ship a model. First verify that Ollama is installed:

```powershell
ollama --version
```

On Windows, open the Ollama app if its service is not already running. On
Linux or macOS, start the service when your installation has not configured one:

```bash
ollama serve
```

In another terminal, download a tool-capable instruct or coding model from the
Ollama registry and verify it appears:

```powershell
ollama pull <model-name>
ollama list
```

Pulling writes several gigabytes to Ollama's model store. Alice does not choose
or download a model automatically because hardware limits, model licenses, and
download sizes vary. After the pull finishes, start Alice and refresh the model
list beside the provider selector.

For this machine, begin with a 3B-8B Q4 model. Tool calling is important for
Agent mode; a plain completion model may chat but may not reliably request
tools.

## Import an existing GGUF

1. Start Ollama and Alice.
2. Open provider settings and choose **Import a GGUF model**.
3. Enter the absolute path to an existing `.gguf` file and a model name.
4. Wait for `ollama create` to finish, then refresh the Ollama model list.

Alice validates that the source is a real `.gguf` file, sanitizes the requested
model name, writes a small Modelfile under
`<ALICE_HOME>/imports`, sets `num_ctx` to 8192, and invokes:

```text
ollama create <sanitized-name> -f <generated-Modelfile>
```

The original GGUF is not moved or deleted. Ollama may create a managed blob or
cache entry of its own, so allow for additional disk use. Import can take time
and is stopped after 30 minutes. A GGUF is not universally compatible merely
because its extension is correct: its architecture and quantization must also
be supported by the installed Ollama version.

## View local models

Select the Alice icon beside the model selector to open the **Model library**.
It shows Ollama models that are ready to chat and Hugging Face repository files
Alice has downloaded, including their size and whether another runtime is
needed before they can be used.

## Run a GGUF with llama.cpp

Install a CUDA-enabled llama.cpp build locally under `tools/llama.cpp/bin3`, then
use `scripts/start-llama-qwen.cmd` to start a downloaded Q4 Qwen model on
`http://127.0.0.1:8080`. Add a **llama.cpp** provider in Alice with that base URL
to use the server through its OpenAI-compatible API. The runtime and models are
intentionally excluded from this repository.

The launcher uses Alice's balanced profile: one active chat slot, a 3K context,
GPU flash attention, quantized KV cache, and five-minute idle sleep. This keeps
the Q4 2B model responsive while reducing background CPU and VRAM pressure.

## Add local OpenVoice replies

The OpenVoice setup script downloads the official source into `tools/OpenVoice`
and keeps its dependency environment separate from Alice. OpenVoice V2 provides
local speech and can later be extended with a reference recording for voice
cloning. The source checkout, environment, and downloaded checkpoints are
intentionally excluded from this repository.

OpenVoice's dependency pins require **Python 3.10**; Alice's own Python 3.13
environment must not be reused. Install a current 64-bit Python 3.10 release,
then run:

```powershell
.\scripts\setup-openvoice.cmd
```

The installer creates `tools/OpenVoice/.venv`, installs OpenVoice and MeloTTS,
downloads the official `myshell-ai/OpenVoiceV2` checkpoints from Hugging Face,
and verifies the runtime. It may download several gigabytes of packages and
models. After it completes, restart Alice and enable **Speak replies** in the
message box. Generated WAV files stay in `<ALICE_HOME>/audio` and are served
only by Alice's loopback web server.

OpenVoice remains warm while you are actively using speech, then stops after
five idle minutes to release its GPU and system memory. The next spoken reply
starts it again automatically.

Only use a reference recording when you have the speaker's permission. OpenVoice
clones tone color; its own documentation notes that accent and emotion still
come from the base TTS speaker.

## Import from Hugging Face

1. Start Alice and open **Provider settings**.
2. Choose **Import from Hugging Face** and paste the model-page link, such as
   `https://huggingface.co/Qwen/Qwen2.5-Omni-3B`, or enter `owner/repository`.
3. Select **Inspect model**. If it provides GGUF files, choose one and select
   **Download and import** to register it with Ollama.
4. For a standard Transformers repository, choose **Download model files** to
   save the complete repository locally.

GGUF imports download exactly the selected file. A repository download retrieves
all of the model files and can be very large. Qwen2.5-Omni-3B is a Transformers
multimodal model, so it is downloaded but cannot be registered with Ollama; it
needs a compatible Transformers runtime before it can run in Alice. Public
repositories work without an account. For private or gated files, add
`HF_TOKEN=...` to `.env` before starting Alice; the token is read from the launch
environment and is not stored in Alice's settings or database. Downloads are
kept under `<ALICE_HOME>/models/huggingface/`.

You can instead paste a token into the Hugging Face import dialog for the current
browser session. Alice sends it only to its loopback server, clears it when the
dialog closes, and never writes it to disk. Repository downloads run in the
background and show queued, downloading, complete, or failed status with the
final local directory and a sanitized failure reason.

The inspection panel shows the repository download size, each GGUF's
quantization, and estimated RAM/VRAM needs. When `nvidia-smi` is available,
Alice also compares the selected model's estimated full-offload VRAM use with
the largest detected NVIDIA GPU. These are planning estimates, not a guarantee:
context length, GPU layers, and model architecture affect actual use.

## Connect an OpenAI-compatible endpoint

Add a provider profile in settings with these values:

- **Profile name:** Alice derives a safe local ID from this name.
- **Provider type:** choose OpenAI compatible, OpenAI, LM Studio, llama.cpp, or
  Ollama. All except Ollama use the OpenAI-compatible adapter.
- **Base URL:** the server root, with or without a trailing `/v1`.
- **API key environment variable:** the name of an environment variable, not
  the key itself.

If the base URL is `http://127.0.0.1:1234`, Alice calls
`http://127.0.0.1:1234/v1/models` and
`http://127.0.0.1:1234/v1/chat/completions`. If it already ends in `/v1`, Alice
does not add a second `/v1`.

Plain HTTP is accepted only for `localhost` or a loopback IP. Remote providers
must use HTTPS. URLs containing embedded credentials or fragments are rejected,
and redirects are not followed.

For a secret-bearing endpoint, copy `.env.example` to `.env`, add a variable,
and use that variable name in the profile:

```dotenv
MY_LLM_API_KEY=replace-me
```

The launch scripts load `.env` as literal `KEY=VALUE` entries and do not
evaluate commands. The provider sends the value as `Authorization: Bearer ...`.
Alice persists only the variable name in `settings.json`; the `.env` file itself
is still plaintext and must be protected.

### Compatibility contract

"Any model" means any suitable chat model behind one of the supported runtime
contracts, not every model file or inference API:

- Ollama profiles need `GET /api/tags` and streaming `POST /api/chat`.
- OpenAI-compatible profiles need `GET /v1/models` and
  `POST /v1/chat/completions`.
- Chat Completions may stream SSE or return a valid non-streaming response.
- Agent mode works best when both server and model support function tools.
- When a server rejects tool definitions with HTTP 400, 404, or 422, Alice
  retries using a strict one-tool JSON prompting protocol. Model compliance is
  not guaranteed.

Responses-only services, ONNX, old GGML files, embedding-only models, image-only
models, and arbitrary proprietary protocols are not directly supported. Alice
can download raw Hugging Face checkpoints and SafeTensors but only imports GGUF
files into Ollama today. LM Studio and standalone llama.cpp can work when their
OpenAI-compatible server is enabled; Alice does not install or manage those
runtimes.

## Workspaces, tools, and approvals

Each conversation has one existing local directory as its workspace. Relative
and absolute tool paths are resolved and must remain inside that directory.
UNC/network workspaces, symlink escapes, and Windows alternate data-stream
paths are rejected.

Use the folder button in Alice's top bar to browse that workspace, inspect text
files, review a compact Git-change list, and add a selected file to the next
message. The browser is read-only; any file modification remains an
approval-gated agent action.

Agent mode exposes these tools:

| Tool | Approval | Notes |
| --- | --- | --- |
| `workspace_list` | Automatic | Lists within the selected workspace. |
| `workspace_read` | Automatic | Reads UTF-8 text files up to 512,000 bytes. |
| `workspace_search` | Automatic | Searches UTF-8 files with limits and globs. |
| `workspace_write` | Every call | Shows a unified diff, then creates or replaces one text file. |
| `process_run` | Every call | Shows argv and cwd, then runs without a command shell. |
| `memory_store` | Automatic | Saves up to 4,000 characters in the conversation database. |
| `memory_search` | Automatic | Searches memories for the current conversation. |

An approval applies once to the exact pending tool call. Denial returns an error
to the model. Turning off Agent mode sends no tool definitions.

Approval is a user-consent boundary, not an operating-system sandbox. An
approved executable can still modify data outside its cwd if that executable's
arguments or behavior direct it there. Review process previews carefully and
run Alice under an appropriately restricted OS account for untrusted models or
workspaces. See [docs/security.md](docs/security.md) for the full threat model.

## Data and privacy

When started through the supplied scripts, Alice stores the following under
`.alice-data` by default:

- `settings.json`: provider metadata and API-key environment variable names.
- `alice.db`: sessions, messages, tool metadata, and memories in SQLite/WAL.
- `imports/*.Modelfile`: generated GGUF import definitions.
- `models/huggingface/`: files downloaded through the Hugging Face dialog,
  with Hugging Face cache metadata alongside them.

Set `ALICE_HOME` to an absolute directory to move this data. When Alice is
started directly without `ALICE_HOME`, the default is `%LOCALAPPDATA%\AliceOS`
on Windows, `$XDG_DATA_HOME/alice-os` when set, or
`~/.local/share/alice-os` elsewhere.

Messages and memories are not encrypted by Alice. A local Ollama conversation
stays between Alice and the local Ollama service, but a remote provider receives
the system prompt, conversation context, tool definitions, and any tool results
the model requested. Tool results can contain workspace file contents. Review
the remote provider's data policy before using it.

Browser dictation is separate from the Python core. Depending on the browser and
OS, speech recognition may be unavailable or may send microphone audio to the
browser vendor's service. Do not assume the dictation button is offline merely
because Alice and Ollama are local.

## Tests

The default setup installs pytest and pytest-asyncio. The suite covers storage
persistence, API session authentication, origin checks, provider streaming/tool
assembly, fallback tool parsing, approval fingerprints, and workspace escape
defenses.

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Linux or macOS:

```bash
./.venv/bin/python -m pytest -q
```

For a quick syntax check of the Python package:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src
```

## Troubleshooting

### Alice says no model is selected

Run `ollama list`. If it is empty, pull or import a model, then use the refresh
button. A model is never downloaded at setup time.

### Ollama is installed but offline

Open the Ollama app on Windows or run `ollama serve` on Linux/macOS. Confirm:

```powershell
ollama list
```

Alice expects Ollama on `http://127.0.0.1:11434` for runtime status and the
built-in profile.

### The model is slow or runs out of memory

Use a smaller quantization or model, shorten the requested context, and close
other GPU-heavy programs. Check placement with `ollama ps`; on NVIDIA hardware,
`nvidia-smi` shows VRAM use. On this RTX 3050/16 GiB system, start with 3B-8B Q4.

### GGUF import fails

Confirm the path is absolute, the file exists and ends in `.gguf`, Ollama is on
`PATH`, and the installed Ollama supports that GGUF architecture. Check free
space in both the source volume and Ollama's managed model volume.

### Hugging Face model lookup or download fails

Confirm the repository uses a valid model-page link or `owner/repository` form.
Gated and private repositories require a valid `HF_TOKEN` in `.env` before Alice
starts. Also check available disk space: repository downloads retain every model
file, while GGUF imports retain the download before Ollama imports it.

### A custom provider cannot list models

Verify the base URL and `GET /v1/models` response. Use loopback for plaintext
HTTP or HTTPS for remote hosts. Alice does not follow redirects. If the profile
names an API-key environment variable, ensure it is non-empty in `.env` before
starting Alice.

### Chat works but Agent mode does not

Use a model with reliable function calling and a compatible chat template.
Alice's JSON fallback helps servers that reject native tools, but small or
completion-only models may emit malformed JSON or ignore the protocol. Turn off
Agent mode for ordinary chat.

### Port 7788 is already in use

```powershell
.\scripts\start.cmd -Port 7799
```

On Linux/macOS use `bash scripts/start.sh --port 7799`.

### PowerShell blocks the setup script

Run the one-process override shown in the Windows quick start. `start.cmd` also
uses a process-scoped execution-policy bypass when Windows PowerShell is the
only available host; it does not change the machine policy.

### API calls return 401

Open `http://127.0.0.1:<port>/` first. The root response creates a random,
HttpOnly, same-site session cookie for that Alice process. Restarting Alice
invalidates the previous token.

## Project map

```text
src/alice_os/       FastAPI service, agent loop, providers, tools, and storage
web/                Local browser interface
tests/              Unit and API tests
scripts/            Cross-platform setup and launch helpers
docs/architecture.md Runtime and data-flow design
docs/security.md     Trust model, controls, and residual risk
```

## License

MIT. See [LICENSE](LICENSE).
