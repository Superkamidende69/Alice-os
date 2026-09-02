#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_ROOT="${PROJECT_ROOT}/.venv"
VENV_PYTHON="${VENV_ROOT}/bin/python"
INSTALL_TARGET="${PROJECT_ROOT}[dev]"

if [[ "${1:-}" == "--without-dev" ]]; then
  INSTALL_TARGET="${PROJECT_ROOT}"
elif [[ $# -gt 0 ]]; then
  printf 'Unknown option: %s\n' "$1" >&2
  printf 'Usage: bash scripts/setup.sh [--without-dev]\n' >&2
  exit 2
fi

find_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && \
      "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

printf 'Alice OS setup\nProject: %s\n' "$PROJECT_ROOT"

if [[ ! -x "$VENV_PYTHON" ]]; then
  if ! PYTHON_EXE="$(find_python)"; then
    printf 'Python 3.11 or newer was not found. Install it, then rerun this script.\n' >&2
    exit 1
  fi
  printf 'Creating .venv with %s...\n' "$PYTHON_EXE"
  "$PYTHON_EXE" -m venv "$VENV_ROOT"
else
  printf 'Reusing existing .venv.\n'
fi

printf 'Updating packaging tools...\n'
"$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel

printf 'Installing Alice OS in editable mode...\n'
"$VENV_PYTHON" -m pip install --editable "$INSTALL_TARGET"
"$VENV_PYTHON" -c "import alice_os; print('Alice OS package import: OK')"

if command -v ollama >/dev/null 2>&1; then
  printf 'Ollama executable: %s\n' "$(command -v ollama)"
else
  printf '%s\n' 'Warning: Ollama was not found. Local model pull/GGUF import needs Ollama.' >&2
fi

printf '\nSetup complete. Start Alice with:\n  bash scripts/start.sh\n\n'
printf '%s\n' 'No model is downloaded automatically. See README.md for Ollama first-run steps.'
