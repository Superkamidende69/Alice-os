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

: "${ALICE_HOME:=${PROJECT_ROOT}/.alice-data}"
export ALICE_HOME

printf 'Starting Alice OS. Data directory: %s\n' "$ALICE_HOME"
cd -- "$PROJECT_ROOT"
exec "$VENV_PYTHON" -m alice_os "$@"
