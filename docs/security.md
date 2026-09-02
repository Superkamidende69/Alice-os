# Alice OS security and privacy

Alice lets a probabilistic model inspect a workspace and propose local actions.
Its controls reduce accidental or model-driven harm, but they do not turn the
model or an approved process into trusted code.

## Threat model

Alice assumes:

- The person at the local browser is authorized to use the selected workspace.
- Model output can be mistaken, adversarial, or manipulated by prompt injection.
- Workspace files, attached or quoted text, search results, terminal output,
  provider output, and tool output are untrusted data, not instructions.
- Remote model providers and local inference servers are separate trust domains.
- Other processes running as the same OS user may be able to read Alice's
  plaintext data files or interact with local services.

Alice does not defend against a fully compromised OS account, malicious code
the user explicitly approves and runs, kernel attacks, or physical access to an
unlocked machine.

## Network boundary

The CLI accepts only `127.0.0.1` or `localhost` and Uvicorn binds to
`127.0.0.1`. `TrustedHostMiddleware` permits only `127.0.0.1`, `localhost`, and
the test host. Do not work around this to expose Alice on a LAN: the session
cookie is intentionally non-secure because transport is loopback HTTP, and the
application has no multi-user authentication or TLS termination.

Opening `/` creates a random 256-bit-style URL-safe process token and returns it
as an HttpOnly, SameSite=Strict cookie with a one-day maximum age. Protected
routes accept that cookie or an `X-Alice-Token` header. If a browser supplies an
`Origin`, its hostname must be loopback. Restarting Alice rotates the token.

`GET /api/health`, `/`, and static assets are intentionally unauthenticated.
FastAPI's interactive documentation routes are disabled.

Provider URLs must be HTTP(S), cannot contain embedded credentials or URL
fragments, and do not follow redirects. Plain HTTP is accepted only for a
loopback provider; remote profiles require HTTPS. This prevents an accidental
cleartext remote connection, but Alice does not validate the operator's trust
in a remote certificate authority or provider.

## Instruction hierarchy and prompt injection

The system prompt tells the model that only system policy and direct user chat
requests are instructions. Files and tool output are untrusted evidence. This is
an important behavioral defense, not a mathematical guarantee. A sufficiently
capable prompt injection may still influence a model.

Keep Agent mode off when reviewing unknown repositories if ordinary chat is
enough. Inspect every mutating preview. Avoid placing secrets in a workspace a
model is allowed to read, because reads do not require approval.

## Workspace confinement

Sessions accept only existing local directories. UNC/network paths are
rejected. Every filesystem tool resolves its target and requires it to remain
under the resolved workspace root. This blocks `..` traversal, absolute paths
outside the workspace, and symlink escapes. Relative Windows paths containing a
colon are rejected to prevent alternate data stream access.

Additional bounds include:

- File reads are UTF-8 text only and limited to 512,000 bytes.
- Searches skip oversized or non-UTF-8 files and cap match counts.
- List/search skip `.git`, `.venv`, `node_modules`, `__pycache__`, and
  `.alice-data`.
- Direct reads can still access a named file in one of those directories if it
  is inside the workspace and within the size limit.
- Write tools create or replace one UTF-8 text file; there is no direct delete
  tool.

Confinement is implemented in Alice's tools. It is not a kernel-enforced sandbox
for arbitrary executables.

## Approval model

| Action | Default | Preview/control |
| --- | --- | --- |
| List, read, or search workspace text | Automatic | Path and size/count bounds. |
| Store or search conversation memory | Automatic | Memory length is capped at 4,000 characters. |
| Create or replace a text file | Ask every time | Unified diff and resolved relative path. |
| Launch a local process | Ask every time | Structured argv and workspace cwd. |
| Pull an Ollama model | Direct authenticated UI/API action | No agent tool; may download large files. |
| Import a GGUF | Direct authenticated UI/API action | No agent tool; runs `ollama create`. |

Approval is one-shot. It is associated with the pending call ID; a fingerprint
also binds tool name, full arguments, and workspace for display/audit purposes.
Denial is returned to the model as a tool error. Repeated identical calls are
blocked after the second execution within one run.

### Important process limitation

`process_run` avoids a command shell and passes an argv array, reducing shell
injection risk. It constrains cwd to the workspace, limits runtime to five
minutes, truncates captured output, and gives the child only a small environment
allowlist.

It does **not** sandbox the executable. Once approved, a program can use absolute
paths, network access, inherited OS permissions, subprocesses, or its own config
to affect resources outside the workspace. A preview proves what Alice asked to
launch, not what that program will do.

For stronger isolation, run Alice under a dedicated OS account, use a disposable
VM/container with deliberately mounted workspace paths, or add a reviewed OS
sandbox layer before enabling process tools. Do not expose an approval-bypass
mode.

## Secrets

Provider profiles contain `api_key_env`, the name of an environment variable.
They do not persist the key value in `settings.json`. At request time the value
is read from Alice's process environment and sent as a bearer token.

The supplied start scripts can load a project `.env` file. They accept only
literal `KEY=VALUE` records and do not execute substitutions or shell commands.
Nevertheless, `.env` is plaintext:

- Never commit or share it.
- Restrict its filesystem permissions.
- Prefer a narrowly scoped provider token.
- Rotate a key after suspected exposure.
- Do not put secrets directly in a provider URL; such URLs are rejected.

Process tools receive only `PATH`, `PATHEXT`, `SYSTEMROOT`, `WINDIR`, `COMSPEC`,
`TEMP`, `TMP`, and `LANG` when present, plus `PYTHONIOENCODING=utf-8`. Provider
API-key variables are therefore not intentionally forwarded to approved child
processes. A process running as the same OS user may still obtain secrets by
other operating-system mechanisms, so this is defense in depth rather than a
complete secret sandbox.

## Data privacy

When launched with the supplied scripts, `.alice-data` contains:

- `settings.json` with provider metadata and environment variable names.
- `alice.db` with conversation text, message/tool metadata, and memories.
- SQLite `-wal`/`-shm` files while the database is active.
- Generated GGUF import Modelfiles.

Alice does not encrypt these files. Backups, filesystem indexing, antivirus,
and other same-user processes may copy or inspect them. Remove the data directory
only after Alice is stopped and only when conversation loss is intended.

### What leaves the machine

With the built-in loopback Ollama profile, prompts and responses travel only
between Alice and the local Ollama service. Ollama's own update checks, model
pulls, logging, and telemetry behavior are governed by Ollama, not Alice.

With a remote OpenAI-compatible profile, Alice can send:

- The system prompt.
- Up to 80 recent stored messages.
- Tool definitions.
- Model-selected file/search/process results, which may contain workspace data.
- Error text returned by tools.

Treat the remote provider as a recipient of conversation and selected workspace
content. Review its retention, training, residency, and access policies.

The current app has no web-search tool, analytics client, or automatic cloud
sync in its Python core.

The browser UI can use the Web Speech Recognition API for dictation. Some
browsers implement recognition through a vendor-hosted service, so microphone
audio may leave the machine even when the selected LLM is local. Browser
permission and vendor privacy controls apply; Alice's Python service never
receives the audio stream.

## Model and runtime risk

"Local" does not mean "safe." A local model may hallucinate destructive
commands, mishandle instructions, or be packaged with a vulnerable runtime.
Only use model files and inference software from sources you trust. Keep Ollama,
Python dependencies, the browser, and GPU drivers patched through their normal
distribution channels.

GGUF import passes an absolute source path to a generated Ollama Modelfile and
runs `ollama create`. The original file remains, while Ollama may create another
managed copy. Alice validates the extension but cannot establish model quality,
license, provenance, architecture support, or absence of runtime parser bugs.

## Operational checklist

Before enabling Agent mode:

1. Select the narrowest practical workspace.
2. Remove credentials and private data the model does not need.
3. Confirm the provider is the intended local or HTTPS endpoint.
4. Use a model known to follow tool schemas reliably.
5. Back up or commit important workspace changes.
6. Read every write diff and process argv before approving.
7. Stop the run if calls repeat, expand scope, or diverge from the request.

For higher-risk work, use read-only Agent mode by denying all mutations, or run
Alice inside a disposable, restricted environment.

## Security tests

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The current suite exercises cookie/header authentication, foreign-origin
rejection, path traversal and symlink escape prevention, Windows alternate data
stream rejection, bounded reads/searches, write previews, stable approval
fingerprints, provider tool-call streaming, and strict fallback JSON parsing.

Tests demonstrate intended behavior for covered cases; they are not a formal
security proof. Re-run them after changing URL validation, path resolution,
process execution, authentication, provider parsing, or approval logic.
