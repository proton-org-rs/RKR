#!/usr/bin/env bash
set -e
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"
python3 -c 'import tkinter' || {
  printf 'Install Tkinter first: sudo apt install python3-tk python3-venv\n'
  exit 1
}
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python install_shortcuts.py
printf '\nReady. Use the two SpiRob desktop shortcuts.\n'
