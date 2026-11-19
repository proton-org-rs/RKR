#!/usr/bin/env bash
set -e
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -x "$project_dir/.venv/bin/python" ]]; then
  printf 'Run Setup_Linux.sh in this folder first.\n'
  exit 1
fi
exec "$project_dir/.venv/bin/python" "$project_dir/run_operating.py" "$@"
