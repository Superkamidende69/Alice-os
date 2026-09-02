# Alice OS architecture

This document describes Alice OS 0.1.0 as implemented. It is an architectural
reference, not an instruction source for the agent: workspace files and tool
output are treated as untrusted data by the system prompt.

## Design goals

- Local-first operation with a loopback-only web service.
- Model portability through Ollama and the OpenAI Chat Completions shape.
- A Codex-style observe/act/verify loop without tying the core to one model.
- Explicit approval for mutating tools.
- A hard path boundary around the user-selected workspace.
- Small, inspectable Python components and no required frontend build step.

## Component map

```text
Browser on 127.0.0.1
        |
        | cookie-authenticated JSON + SSE
        v
FastAPI application (api.py)
   |          |            |                 |
   |          |            |                 +--> Runtime helpers (runtimes.py)
   |          |            |                       ollama pull / create
   |          |            |
   |          |            +--> ConfigStore (config.py)
   |          |                    settings.json
   |          |
   |          +--> Storage (storage.py)
   |                   alice.db (SQLite/WAL)
   |
   +--> RunManager (agent.py)
           |                         |
           |                         +--> ToolRegistry (tools.py)
           |                              workspace + process + memory tools
           |
           +--> providers.py
                    |--> Ollama /api/chat
                    +--> OpenAI-compatible /v1/chat/completions
```

The browser optionally uses `SpeechRecognition`/`webkitSpeechRecognition` to
place dictated text in the composer. This is a browser facility, not an Alice
backend endpoint, and its local/remote processing behavior depends on the
browser and operating system.

## Startup and configuration

The `alice` console entry point and `python -m alice_os` both call
`alice_os.cli:main`. The CLI accepts:

- `--host`, limited to `127.0.0.1` or `localhost`.
- `--port`, default `7788`.
- `--no-browser`.

Regardless of the accepted host spelling, Uvicorn binds to `127.0.0.1`. The
supplied start scripts set `ALICE_HOME` to `<project>/.alice-data` unless the
caller already supplied it, load literal variables from `.env`, and invoke the
module from the repository root.

Without an override, `default_data_dir()` uses:

1. `ALICE_HOME`, when set.
2. `%LOCALAPPDATA%\AliceOS` on Windows.
3. `$XDG_DATA_HOME/alice-os`, when set.
4. `~/.local/share/alice-os`.

`ConfigStore` creates the directory and an initial `settings.json`. The default
provider is:

```json
{
  "id": "ollama",
  "name": "Ollama (local)",
  "kind": "ollama",
  "base_url": "http://127.0.0.1:11434",
  "default_model": "",
  "api_key_env": ""
}
```

Configuration saves use a temporary file followed by replacement. The built-in
Ollama profile can be updated but cannot be deleted.

## HTTP surface

FastAPI's Swagger and ReDoc routes are disabled. The root page establishes the
session cookie; `/api/health` remains unauthenticated for local health checks.
Every other API route below requires the random process token through the
`alice_session` cookie or `X-Alice-Token` header.

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/` | Serve the UI and set the session cookie. |
| `GET` | `/api/health` | Return status and application version. |
| `GET` | `/api/state` | Return providers, sessions, runtime state, and privacy summary. |
| `POST` | `/api/providers` | Create or replace a provider profile. |
| `DELETE` | `/api/providers/{provider_id}` | Delete a non-built-in profile. |
| `POST` | `/api/providers/active` | Select the active provider. |
| `GET` | `/api/providers/{provider_id}/models` | Discover provider models. |
| `POST` | `/api/sessions` | Create a conversation with a resolved workspace. |
| `GET` | `/api/sessions/{session_id}` | Read a conversation and its messages. |
| `PATCH` | `/api/sessions/{session_id}` | Update title, workspace, provider, or model. |
| `DELETE` | `/api/sessions/{session_id}` | Delete a conversation and related rows. |
| `POST` | `/api/runs` | Start one background model/agent run. |
| `GET` | `/api/runs/{run_id}/events` | Stream ordered Server-Sent Events. |
| `POST` | `/api/runs/{run_id}/approval` | Approve or deny a pending tool call. |
| `POST` | `/api/runs/{run_id}/cancel` | Cancel a live run. |
| `GET` | `/api/runtime/status` | Check local Ollama installation/service/models. |
| `POST` | `/api/gguf/import` | Generate a Modelfile and run `ollama create`. |
| `POST` | `/api/models/pull` | Run `ollama pull`. |

Static files are mounted under `/static` and still pass through the trusted-host
middleware.

## Conversation and run flow

1. The client creates or selects a session. The workspace must already exist
   and resolve to a local directory.
2. `POST /api/runs` validates the provider and session, creates an in-memory
   `AgentRun`, and starts an asyncio task.
3. The user message is persisted. A new conversation's default title becomes
   the first 64 normalized characters of that message.
4. The run emits a `status` event and asks the selected provider for a streamed
   turn.
5. With Agent mode disabled, the first completed assistant response ends the
   run. With Agent mode enabled, tool calls enter the approval/execution loop.
6. Tool messages are persisted and supplied on the next model step.
7. The loop ends on an assistant answer, cancellation, error, or 12 steps.

The provider context contains the Alice system prompt followed by at most the
last 80 stored messages. Alice does not currently perform token counting or
semantic compaction.

SSE events have increasing sequence numbers. The endpoint accepts `after=<n>`
to replay events after a known sequence. Event names include `status`, `token`,
`tool_call`, `approval_required`, `tool_result`, `message`, `done`, `error`, and
`cancelled`. Live runs and their event buffers are process memory only; durable
messages remain in SQLite after restart.

## Provider adapters

### Ollama

Model discovery calls `GET <base_url>/api/tags`. Chat calls streaming
`POST <base_url>/api/chat` using Ollama message/tool shapes. Each newline is
parsed as one JSON chunk. An empty model is rejected before the request.

The runtime status endpoint is deliberately fixed to local Ollama at
`127.0.0.1:11434`, independent of custom provider profiles.

### OpenAI-compatible

The provider kind is named `openai`, but it is a protocol adapter rather than a
restriction to one vendor. It calls `GET /v1/models` and
`POST /v1/chat/completions`, adding `/v1` only when the configured base URL does
not already end with it.

Streaming responses must use SSE `data:` records with Chat Completions deltas.
Fragmented tool-call names and arguments are aggregated by tool-call index. A
valid non-streaming Chat Completions response is also accepted. If
`api_key_env` is configured, its environment value is sent as a bearer token.

HTTP clients use finite connect/write/pool timeouts, a 300-second chat read
timeout, and no redirects.

### Tool compatibility fallback

If a provider returns 400, 404, or 422 after receiving native tool definitions,
`RunManager` retries without definitions and adds a prompt describing a strict
single-tool JSON envelope. The fallback parser accepts only an object with a
`tool` name and object-valued `arguments`, optionally enclosed in a code fence.
Normal workspace checks and approvals still apply.

This broadens compatibility but cannot make a model follow tools reliably. A
server may reject tools with a different status, and a model may return invalid
or ambiguous JSON.

## Agent loop and tools

`ToolRegistry` exposes seven functions:

- Automatic: `workspace_list`, `workspace_read`, `workspace_search`,
  `memory_store`, and `memory_search`.
- Approval-gated: `workspace_write` and `process_run`.

The run emits a preview before waiting on a one-shot approval future. Write
previews are bounded unified diffs. Process previews contain structured argv and
the relative cwd. Every tool result becomes a stored `tool` message.

A SHA-256 fingerprint binds the tool name, complete arguments, and resolved
workspace for audit display. It does not grant standing approval. More than two
identical calls in one run are blocked by a loop circuit breaker.

Workspace paths resolve through the filesystem and must remain relative to the
resolved workspace root, which also blocks symlink escapes. The list and search
tools skip `.git`, `.venv`, `node_modules`, `__pycache__`, and `.alice-data`.
Direct file reads remain possible when the model names an in-workspace path.

`process_run` uses `asyncio.create_subprocess_exec`, not a shell string. Its cwd
must be in the workspace, runtime is limited to 1-300 seconds, output is capped
at 60,000 characters per stream result, and the child receives a small
allowlist of environment variables. It is not contained by an OS sandbox.

## Persistence

SQLite uses WAL mode, foreign keys, and a process-local reentrant lock. Tables:

- `sessions`: title, workspace, provider, model, and timestamps.
- `messages`: ordered role/content records plus JSON metadata.
- `memories`: concise conversation-scoped durable facts.

Deleting a session cascades to messages and memories. Database content and
settings are plaintext. Generated import Modelfiles live next to the database;
model weights remain managed by Ollama and/or their original source location.

## Runtime operations

`runtime_status()` checks whether `ollama` is on `PATH`, then probes the fixed
local version and tags endpoints with a two-second timeout.

Model pull invokes `ollama pull <sanitized-model>` and permits up to one hour.
GGUF import verifies a real `.gguf`, creates a Modelfile with an absolute source
path and `num_ctx 8192`, then permits `ollama create` up to 30 minutes. Captured
subprocess output is truncated to the last 8,000 characters before it is
returned.

## Extension points

- Add a provider kind in `models.py` and an adapter in `providers.py`.
- Add a tool through `ToolRegistry`, explicitly choosing whether it requires
  approval and supplying a non-mutating preview for gated actions.
- Add migrations before changing the SQLite schema; the current initializer
  only creates missing tables.
- Keep browser/API changes synchronized because OpenAPI discovery is disabled
  and the UI uses the application routes directly.

See [security.md](security.md) before adding network listeners, desktop control,
secret storage, or tools with broader filesystem authority.
