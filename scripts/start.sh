#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
ENV_FILE="${PROJECT_ROOT}/.env"

load_env_file() {
  local raw line key value first last
  while IFS= read -r raw || [[ -n "$raw" ]]; do
    line="${raw%$'\r'}"
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ ! "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      printf 'Invalid .env entry. Use KEY=VALUE syntax: %s\n' "$raw" >&2
      exit 1
    fi
    key="${BASH_REMATCH[1]}"
    value="${BASH_REMATCH[2]}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    if [[ ${#value} -ge 2 ]]; then
      first="${value:0:1}"
      last="${value: -1}"
      if [[ ( "$first" == '"' && "$last" == '"' ) || ( "$first" == "'" && "$last" == "'" ) ]]; then
        value="${value:1:${#value}-2}"
      fi
    fi
    export "$key=$value"
  done < "$ENV_FILE"
}

if [[ ! -x "$VENV_PYTHON" ]]; then
  printf 'Alice virtual environment is missing. Run: bash scripts/setup.sh\n' >&2
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  load_env_file
fi

"$VENV_PYTHON" -m alice_os --setup
ALICE_HOME="$("$VENV_PYTHON" -c 'from alice_os.config import default_data_dir; print(default_data_dir())')"
export ALICE_HOME
LOCALAI_DISABLED=0
LOCALAI_ENABLED=0
LLAMA_DISABLED=0
NETWORK_ENABLED=0
ALICE_ARGS=()
for arg in "$@"; do
  [[ "$arg" == "--no-localai" ]] && LOCALAI_DISABLED=1
  [[ "$arg" == "--use-localai" ]] && LOCALAI_ENABLED=1
  [[ "$arg" == "--no-llama" ]] && LLAMA_DISABLED=1
  [[ "$arg" == "--network" || "$arg" == "--lan" ]] && NETWORK_ENABLED=1
  [[ "$arg" != "--no-localai" && "$arg" != "--use-localai" && "$arg" != "--no-llama" && "$arg" != "--network" ]] && ALICE_ARGS+=("$arg")
done

if [[ "$NETWORK_ENABLED" -eq 1 ]]; then
  export ALICE_NETWORK_MODE=1
  umask 077
  ALICE_ARGS+=("--lan")
fi

LOG_DIR="${ALICE_HOME}/logs"
mkdir -p "$LOG_DIR"

if [[ "$LOCALAI_ENABLED" -eq 1 && "$LOCALAI_DISABLED" -eq 0 ]]; then
  if curl --silent --fail --max-time 2 http://127.0.0.1:8080/readyz >/dev/null 2>&1; then
    printf 'LocalAI service is already running at http://127.0.0.1:8080\n'
  elif command -v local-ai >/dev/null 2>&1 || command -v localai >/dev/null 2>&1; then
    LOCALAI_BIN="$(command -v local-ai || command -v localai)"
    mkdir -p "${ALICE_HOME}/models/localai"
    nohup "$LOCALAI_BIN" run --address 127.0.0.1:8080 \
      --models-path "${ALICE_HOME}/models/localai" \
      >"${LOG_DIR}/localai.log" 2>"${LOG_DIR}/localai.err.log" &
    printf 'Started native LocalAI at http://127.0.0.1:8080\n'
  elif command -v docker >/dev/null 2>&1; then
    mkdir -p "${ALICE_HOME}/models/localai" "${ALICE_HOME}/localai-data"
    if docker ps -a --format '{{.Names}}' | grep -Fxq 'alice-localai'; then
      if ! docker start alice-localai >/dev/null; then
        printf '%s\n' "Warning: Docker Desktop is not available; LocalAI was not started." >&2
      fi
    else
      if ! docker run -d --name alice-localai --restart unless-stopped \
        -p 127.0.0.1:8080:8080 \
        -v "${ALICE_HOME}/models/localai:/models" \
        -v "${ALICE_HOME}/localai-data:/data" \
        localai/localai:latest >/dev/null; then
        printf '%s\n' "Warning: Docker Desktop is not available; LocalAI was not started." >&2
      fi
    fi
    for _ in {1..30}; do
      sleep 0.5
      curl --silent --fail --max-time 2 http://127.0.0.1:8080/readyz >/dev/null 2>&1 && break
    done
    if curl --silent --fail --max-time 2 http://127.0.0.1:8080/readyz >/dev/null 2>&1; then
      printf 'Started LocalAI service at http://127.0.0.1:8080\n'
    else
      printf '%s\n' "Warning: LocalAI container did not become ready; run 'docker logs alice-localai'." >&2
    fi
  else
    printf '%s\n' 'Warning: LocalAI is not running. Install Docker Desktop or local-ai, then start Alice again.' >&2
  fi
fi

if [[ "$LLAMA_DISABLED" -eq 0 ]] && command -v curl >/dev/null 2>&1; then
  LLAMA_SERVER="${PROJECT_ROOT}/tools/llama.cpp/bin3/llama-server"
  LLAMA_MODEL="${ALICE_HOME}/models/huggingface/empero-ai--Qwen3.8-2B-Distill-GGUF/Qwen3.8-2B-Q4_K_M.gguf"
  if [[ -d "${ALICE_HOME}/models/localai" ]]; then
    MANAGED_MODEL="$(find "${ALICE_HOME}/models/localai" -type f -name '*.gguf' -printf '%T@ %p\n' 2>/dev/null | sort -nr | sed -n '1s/^[^ ]* //p')"
    [[ -n "$MANAGED_MODEL" ]] && LLAMA_MODEL="$MANAGED_MODEL"
  fi
  if [[ -f "${ALICE_HOME}/loaded-model.txt" ]]; then
    SELECTED_MODEL="$(cat "${ALICE_HOME}/loaded-model.txt")"
    [[ -f "$SELECTED_MODEL" ]] && LLAMA_MODEL="$SELECTED_MODEL"
  fi
  if ! curl --silent --fail --max-time 2 http://127.0.0.1:8081/health >/dev/null 2>&1 && [[ -x "$LLAMA_SERVER" && -f "$LLAMA_MODEL" ]]; then
    RPC_TEXT="$("$VENV_PYTHON" -m alice_os.distributed --lines)"
    if [[ "$RPC_TEXT" == "ALICE_MANAGED_GPU_WORKERS" ]]; then
      printf 'GPU workers are selected. Open Models in Alice to load the model.\n'
    else
    RPC_ARGS=()
    while IFS= read -r argument; do
      [[ -n "$argument" ]] && RPC_ARGS+=("$argument")
    done <<< "$RPC_TEXT"
    nohup "$LLAMA_SERVER" -m "$LLAMA_MODEL" -ngl 99 -c 3072 -np 1 -t 6 -tb 8 -fa on -ctk q8_0 -ctv q8_0 --sleep-idle-seconds 300 --host 127.0.0.1 --port 8081 "${RPC_ARGS[@]}" >"${LOG_DIR}/llama.log" 2>"${LOG_DIR}/llama.err.log" &
    printf 'Started bundled llama.cpp provider at http://127.0.0.1:8081\n'
    fi
  fi
fi

# The CLI prints the effective address, including any explicit hostname/port.
printf 'Starting Alice OS. Data directory: %s\n' "$ALICE_HOME"
cd -- "$PROJECT_ROOT"
exec "$VENV_PYTHON" -m alice_os "${ALICE_ARGS[@]}"
