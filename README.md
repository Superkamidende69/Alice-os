# Alice OS

Alice now includes an initial **Cluster** page for pairing LAN inference workers.
Run models on another trusted PC while keeping conversations and tools on your
controller. See [the cluster setup guide](docs/cluster.md) for HTTPS pairing,
worker limits, and the scope of this first release.

Experimental [distributed GPU mode](docs/distributed-gpu.md) can split one GGUF
model across local and paired remote GPUs. Start sharing and select workers from
the Cluster page; Alice manages authenticated GPU connections automatically.

Alice OS is a local-first, Codex-style AI operator with a browser interface,
workspace tools, streamed responses, durable conversations, and explicit
approval before file writes or process launches. LocalAI is the preferred local
inference base; Alice can also talk to Ollama, bundled llama.cpp, or any service
that implements the OpenAI Chat Completions protocol.

Alice is an independent project. It is inspired by the interaction model of
coding agents and fictional desktop assistants; it is not OpenAI Codex and is
not affiliated with the fictional JARVIS.

## What works

- Local browser UI served only on `127.0.0.1`.
- Built-in LocalAI provider using its OpenAI-compatible API.
- Native Ollama model discovery and streaming chat.
- GGUF installation into LocalAI with a generated `llama-cpp` model definition.
- Hugging Face link inspection, full repository downloads, and one-file GGUF import.
- Local model library for LocalAI models, Ollama-ready models, and downloaded
  Hugging Face files.
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
- LocalAI-shaped `/v1/audio/speech` and `/tts` endpoints backed by Alice's own
  OpenVoice voice queue; no LocalAI service is started for voice.
- A visible voice pipeline status showing VAD, transcription, LLM streaming,
  clause chunking, and TTS readiness.
- A dedicated full-screen Voice Studio page at `/voice` for voice controls,
  previews, interruptions, and reference recordings.
- Voice Studio mood presets and advanced OpenVoice/Melo prosody controls for
  delivery variation and cadence.
- Optional local WebRTC speech detection to interrupt spoken replies and voice
  previews, with cancellation of queued and in-flight speech.

## Agent skills

Choose a skill from the **Skill** menu beside Agent mode before sending a
message. Skills tailor Alice's workflow for that run: **Plan a feature** and
**Review code** are read-only, while **Debug an issue** and **Implement safely**
can request the normal workspace tools. A skill never bypasses Alice's existing
approval prompts for file changes or local processes.

Use **Manage** beside the Skill menu to create local custom skills. Each custom
skill has a name, a short description, detailed workflow instructions, and an
optional read-only lock. They are saved in `<ALICE_HOME>/skills.json`; API keys,
models, and workspace permissions are not stored in a skill.

Alice is currently a text and workspace agent; dictation only fills the message
box. It does not yet provide a general desktop-control layer, wake-word service,
  image input, RAG index, or MCP client. For command isolation it provides an
  optional Docker container runner; host processes remain an explicit, approved
  fallback.

## Requirements

- Python 3.11 or newer.
- LocalAI installed natively in WSL, or Docker Desktop with the LocalAI image
  for the managed LocalAI provider.
- Ollama for the fallback local provider, model pulls, and GGUF import.
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

The launcher starts Alice's native model manager and does not start LocalAI as
a separate service. The manager uses the LocalAI gallery format, downloads
models into `<ALICE_HOME>\models\localai`, verifies checksums, writes compatible
model definitions, and tracks progress inside Alice. It also starts Ollama when it is
installed but its local service is not responding, and starts the bundled
llama.cpp provider on `127.0.0.1:8081` when its server binary and an Alice-managed
GGUF are present. It selects the newest model in `<ALICE_HOME>\models\localai`.
Use `-NoOllama` or `-NoLlama` to skip a runtime.

LocalAI is not required for Alice model management. The legacy LocalAI runtime
can still be started explicitly with `-UseLocalAI` for compatibility, but normal
Alice startup leaves port 8080 unused.

To make Alice available to other devices on your home network, use:

```powershell
.\scripts\start.cmd -Network
```

The launcher binds Alice to the LAN and opens Alice in the main computer's
browser. On first use, create a username and password there. Credentials are
stored as a salted PBKDF2 hash in `.alice-data/network-auth.json`; the password
is never stored. Then open `https://aliceos.local/` from another
device on the same network and sign in with the same account. Use
`-NoBrowser` when you want a headless launch. Do not forward Alice's ports to the
public internet; Alice can run workspace tools and local processes on the host
machine. The single-owner login session is kept in `.alice-data` and browser
sessions last one year, so an approved device stays signed in across Alice
restarts. Provider profiles and the selected provider/model are also shared
from the Alice host; each new device only needs to sign in once.

For LAN HTTPS without a port suffix, use Alice's mDNS hostname `aliceos.local`:

```powershell
.\scripts\setup.cmd
.\scripts\setup-network.cmd  # Once, in PowerShell as Administrator
.\scripts\start-network.cmd
```

Open `https://aliceos.local/`. LAN mode uses HTTPS port 443 and redirects HTTP
port 80 to HTTPS. The first HTTPS launch creates a local CA
and server certificate in `.alice-data\tls`. Install
`.alice-data\tls\alice-local-ca.crt` on each device once so its browser trusts
Alice. If `.local` is not resolved by your network, use your router's local DNS
with a suitable custom `-Hostname`; the certificate will be generated for that name.
See [HTTPS LAN setup](docs/https-lan.md) for client trust and network requirements.

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

The Alice launcher starts `ollama serve` automatically when needed. On Linux
or macOS, this requires `curl` to be installed for the readiness check. You can
also start the service manually when your installation has not configured one:

```bash
ollama serve
```

In Voice settings, enable **Listen for “Hey Alice”** for hands-free dictation.
The browser must support Web Speech Recognition and may require one microphone
permission gesture before the wake listener can remain active. After hearing
“Hey Alice,” Alice captures the next request and submits it automatically.

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

1. Start Alice.
2. Open provider settings and choose **Import a GGUF into Alice**.
3. Enter the absolute path to an existing `.gguf` file and a model name.
4. Alice copies the file into its managed model directory, writes the model
   definition, and refreshes Alice's model list.

Alice validates that the source is a real `.gguf` file, sanitizes the requested
model name, and creates these Alice-managed files under
`<ALICE_HOME>/models/localai`:

```text
<sanitized-name>.gguf
<sanitized-name>.yaml
```

The YAML selects the compatible `llama-cpp` backend and points to the GGUF file. The
original GGUF is not moved or deleted. Alice's Ollama importer remains
available only through the explicit Ollama runtime API for compatibility.
GGUF is not universally compatible merely because its extension is correct: its
architecture and quantization must also be supported by the installed LocalAI
or llama.cpp backend.

## View local models

Select the Alice icon beside the model selector to open the **Models** workspace.
Alice owns that page and presents the LocalAI-compatible gallery and installed
models inside the authenticated Alice interface. Install, progress, checksum,
and delete actions stay inside Alice; the browser never opens a second
model-management site.

## Run a GGUF with llama.cpp

Install a CUDA-enabled llama.cpp build locally under `tools/llama.cpp/bin3`, then
use `scripts/start-llama-qwen.cmd` to start the newest Alice-managed GGUF on
`http://127.0.0.1:8081`. Add a **llama.cpp** provider in Alice with that base URL
to use the server through its OpenAI-compatible API. The runtime and models are
intentionally excluded from this repository.

The launcher uses Alice's balanced profile: one active chat slot, a 3K context,
GPU flash attention, quantized KV cache, and five-minute idle sleep. This keeps
the selected model responsive while reducing background CPU and VRAM pressure.

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
message box. Alice streams each reply through its authenticated local player;
the OpenVoice scratch WAV is deleted as soon as it has been read, and the
playback clip exists only in memory for 15 minutes.

OpenVoice remains warm while you are actively using speech, then stops after
five idle minutes to release its GPU and system memory. The next spoken reply
starts it again automatically.

Only use a reference recording when you have the speaker's permission. OpenVoice
clones tone color; its own documentation notes that accent and emotion still
come from the base TTS speaker.

### Interrupt Alice while she speaks

Open **Voice**, enable **Stop speaking when I speak**, and allow microphone
access. A **Mic on · Turn off** button remains visible in the composer while
detection is enabled. The microphone starts off on every page load; turning it
off, closing the page, or losing the audio connection releases the microphone.

Alice requests browser echo cancellation and noise suppression, then streams
16 kHz mono audio to its authenticated local WebSocket. WebRTC classifies speech
locally; microphone audio is neither saved nor sent to a model provider. Eight
voiced 20 ms frames within a 200 ms window trigger an interruption. A 500 ms
silence interval rearms detection. These are detector settings, not a measured
end-to-end latency guarantee. Headphones help avoid self-interruption; background
voices and imperfect speaker echo cancellation can still trigger it.

An interruption stops playback immediately when the detection event arrives,
clears queued speech, and cancels the active synthesis request. OpenVoice stops
at its next segment/conversion checkpoint; an already-running GPU inference
cannot be preempted mid-segment. Its late audio is discarded and temporary clips
are cleaned up. **Stop speaking** provides a manual alternative, and starting
**Dictate** also interrupts the voice. Voice Studio previews use the same
cancellation mechanism.

Detection only stops speech: it does not cancel approved workspace work, send a
new message, or transcribe the interruption. Use **Dictate** or type to continue.
Browser dictation retains its existing browser-dependent privacy behavior.

Replies are synthesized in bounded phrases, with at most two ready clips
buffered ahead. Longer synthesis requests use punctuation-aware segments and
brief pauses. Mood presets adjust Melo's sampling/prosody parameters; their
names do not imply trained emotional understanding or human-level delivery.
A selected reference recording now takes precedence over the default Alice
female reference. A clean, permitted natural-voice reference is the next useful
input for tuning the tone to your taste.

After updating, rerun setup (or `python -m pip install -e ".[dev]"` inside
Alice's environment) for `webrtcvad-wheels` and `websockets`, then restart Alice
and refresh the page. OpenVoice keeps its separate Python 3.10 environment.
Developer voice checks: `python -m pytest -q tests/test_voice.py` and, with
Node.js installed, `node --test tests/voice-client.test.cjs`.

## Import from Hugging Face

1. Start Alice and open **Provider settings**.
2. Choose **Import from Hugging Face** and paste the model-page link, such as
   `https://huggingface.co/Qwen/Qwen2.5-Omni-3B`, or enter `owner/repository`.
3. Select **Inspect repository**. If it provides GGUF files, choose one and
   select **Install selected GGUF** to install it into LocalAI.
4. For a standard Transformers repository, choose **Download model files** to
   save the complete repository locally.

GGUF imports download exactly the selected file. A repository download retrieves
all of the model files and can be very large. Qwen2.5-Omni-3B is a Transformers
multimodal model, so it is downloaded but cannot be registered as a standard
LocalAI chat model; it needs a compatible Transformers runtime before it can run
in Alice. Public repositories work without an account. For private or gated
files, save the token from the dialog; Alice encrypts it for the current Windows
user and reuses it for future imports. You can also enter a token without saving
it for a single action. Downloads are kept under
`<ALICE_HOME>/models/huggingface/`.

Repository downloads run in the background and show queued, downloading,
complete, or failed status with the final local directory and a sanitized
failure reason.

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
| `workspace_read` | Automatic | Reads UTF-8 text files up to 512,000 bytes and returns a content SHA-256 for review-bound patches. |
| `workspace_search` | Automatic | Searches UTF-8 files with limits and globs. |
| `workspace_write` | Every call | Shows a unified diff, then creates or replaces one text file. |
| `workspace_patch` | Every call | Replaces one exact text fragment in a reviewed UTF-8 file, with a version-bound diff preview and atomic apply. |
| `git_status` | Automatic | Reports the active branch and working-tree changes. |
| `git_diff` | Automatic | Shows staged or unstaged changes for a workspace-relative path. |
| `git_worktree_create` | Every call | Creates a new branch in an Alice-managed isolated checkout and moves the conversation to it. |
| `sandbox_status` | Automatic | Checks whether the local Docker container sandbox is ready. |
| `sandbox_process_run` | Every call | Runs a preinstalled container image with network disabled and only the workspace mounted. |
| `process_run` | Every call | Shows argv and cwd, then runs an explicitly approved, unsandboxed host process. |
| `memory_store` | Automatic | Saves a typed, importance-ranked preference or fact across future conversations. Use a stable key for values that may change. |
| `memory_search` | Automatic | Searches persistent memories using relevance, importance, confidence, and recency. Generic messages do not inject unrelated memories. |
| `memory_forget` | Automatic | Archives a persistent memory when the user asks Alice to forget it. |

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
- `alice.db`: sessions, messages, tool metadata, and persistent memories in SQLite/WAL.
- `imports/*.Modelfile`: generated GGUF import definitions.
- `models/huggingface/`: files downloaded through the Hugging Face dialog,
  with Hugging Face cache metadata alongside them.
- Voice replies are held only in memory for playback and expire after 15
  minutes; Alice does not retain reply WAV files on disk.

Persistent memories are categorized as preferences, profiles, projects, routines,
or facts. Each memory can carry a stable key, importance, confidence, source,
and access history. Alice retrieves only relevant memories for a prompt, while
the Provider settings panel provides local review, editing, and forgetting.

Set `ALICE_HOME` to an absolute directory to move this data. When Alice is
started directly without `ALICE_HOME`, the default is `%LOCALAPPDATA%\AliceOS`
on Windows, `$XDG_DATA_HOME/alice-os` when set, or
`~/.local/share/alice-os` elsewhere.

Messages and memories are not encrypted by Alice. Persistent memories are local
to this Alice data directory and are injected into relevant future chats. A local Ollama conversation
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

The Alice launcher starts `ollama serve` automatically when needed. Confirm:

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

Confirm the path is absolute and the file exists and ends in `.gguf`. Start
LocalAI, then check that its model directory is
`<ALICE_HOME>/models/localai`. Check free space in both the source volume and
Alice's LocalAI model directory.

### Hugging Face model lookup or download fails

Confirm the repository uses a valid model-page link or `owner/repository` form.
Gated and private repositories require a valid saved token or `HF_TOKEN` in
`.env` before Alice starts. Also check available disk space: repository
downloads retain every model file, while GGUF imports copy the selected file
into LocalAI's managed directory.

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


### First-install setup

Run `scripts/setup.cmd` (Windows), `bash scripts/setup.sh` (Linux/macOS), or
`alice --setup` in the activated environment. The terminal asks for an external,
empty storage folder, administrator username, and a password of at least 12
characters with hidden confirmation. Start scripts also check setup before
launching providers. Noninteractive startup requires completing setup first.

For example, keep code in `I:/Alice-os` and choose `I:/Alice-data` for storage.
Managed models go in `models/`, generated workspaces in `workspaces/`, and
settings, the database, memories, skills, and secrets live in the same data tree.
A git-ignored `.alice-install.json` beside the code remembers the chosen folder.
Back up the complete data tree and this pointer. Passwords are salted hashes;
the account is required for localhost and network access.

Existing installs keep their current data and only add an account if missing.
Setup never migrates data or resets existing credentials. To relocate an existing
install, stop Alice and its providers, copy the complete data folder externally,
and set `ALICE_HOME` in `.env` to that absolute path. Keep the original until the
copy is verified. This variable takes precedence over the installation pointer.

Launchers set `OLLAMA_MODELS` to the data folder's `models/ollama` for processes
they start. Already-running Ollama and external services require their own storage
configuration. The optional legacy OpenVoice installer still stores checkpoints
under `tools/OpenVoice`; this wizard does not relocate those files.


### Loading downloaded models

The model library and Installed catalog share a recursive inventory of GGUF files
under the data directory's `models/` folder, including Hugging Face downloads.
Downloaded means the file is present; Loaded means the running llama.cpp server
reports that file. Separate copies remain visible with their own locations.

Click **Load model** to replace the current Alice model and select it for chat.
Alice waits for server health before selecting the model and saves the selected
file for launcher restarts. Switching is refused while an Alice response is active.
The loader only stops the bundled llama.cpp executable on port 8081 when its model
is inside Alice's model storage. Unrelated providers are not stopped.

Unsupported or incomplete GGUF files and models that exceed available memory may
fail to load. The UI reports the failure; details are in `logs/model-loader.log`.
A failed switch leaves the previous server stopped; load another compatible model
to recover. No models are downloaded or copied during switching. **Delete file**
removes only the selected file and is blocked for the loaded model.
