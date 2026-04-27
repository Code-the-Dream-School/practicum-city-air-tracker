#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORCE=0

if [[ "${1:-}" == "--force" || "${1:-}" == "-f" ]]; then
  FORCE=1
fi

copy_profile() {
  local source_file="$1"
  local target_file="$2"

  if [[ ! -f "$source_file" ]]; then
    echo "Missing template: $source_file" >&2
    exit 1
  fi

  if [[ -e "$target_file" && "$FORCE" -ne 1 ]]; then
    echo "Skipping existing $target_file"
    return
  fi

  cp "$source_file" "$target_file"
  echo "Wrote $target_file"
}

copy_profile "$ROOT_DIR/configs/env/local.template" "$ROOT_DIR/.env.local"
copy_profile "$ROOT_DIR/configs/env/azure.template" "$ROOT_DIR/.env.azure"

echo
echo "Profile generation complete."
echo "Use .env.local by default, or set ENV_FILE=.env.azure for Azure commands."
