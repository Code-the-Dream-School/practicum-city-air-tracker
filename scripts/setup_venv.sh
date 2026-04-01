#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Error: python3/python not found. Install Python 3.11+ first." >&2
  exit 1
fi

echo "Using Python executable: $PYTHON_BIN"
cd "$ROOT_DIR"

if [[ ! -f "$ROOT_DIR/requirements.txt" ]]; then
  echo "Error: requirements.txt not found in $ROOT_DIR" >&2
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment at $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "Virtual environment already exists at $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install --no-build-isolation -e .

echo
echo "Setup complete."
echo "Activate with: source .venv/bin/activate"
echo "Run pipeline: python -m pipeline.cli --source openweather --history-hours 72"
echo "Run dashboard: streamlit run services/dashboard/app/Home.py"
