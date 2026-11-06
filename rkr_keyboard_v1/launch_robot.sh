#!/usr/bin/env bash
# Put this file beside keyboard_control.py and the project's .venv directory.
# One-time permission: chmod +x launch_robot.sh
# Launch: double-click and choose Run, or run ./launch_robot.sh in a terminal.
set -u
PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 1
PYTHON="$PROJECT_DIR/.venv/bin/python"

show_error() {
    printf '%s\n' "$1" >&2
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title='RKR Robot Control' --text="$1" --width=560 2>/dev/null || true
    elif [ -t 0 ]; then
        read -r -p 'Press Enter to close...' _unused || true
    fi
}

if [ ! -x "$PYTHON" ]; then
    show_error "Project Python not found: $PYTHON
Create .venv in the project folder and install requirements.txt first."
    exit 1
fi
if [ ! -f "$PROJECT_DIR/keyboard_control.py" ]; then
    show_error 'Place launch_robot.sh in the folder containing keyboard_control.py.'
    exit 1
fi
cd -- "$PROJECT_DIR" || exit 1
mkdir -p logs || exit 1
# Prevent a second instance through this launcher; manual launches are separate.
if command -v flock >/dev/null 2>&1; then
    exec 9> .robot_launcher.lock
    if ! flock -n 9; then
        show_error 'RKR Robot Control is already running through this launcher.'
        exit 1
    fi
fi
"$PYTHON" keyboard_control.py --port /dev/ttyUSB0 > logs/launcher_startup.log 2>&1
RESULT=$?
if [ "$RESULT" -ne 0 ]; then
    DETAILS="$(tail -c 2500 logs/launcher_startup.log)"
    show_error "Robot control could not start:
$DETAILS

Full log: $PROJECT_DIR/logs/launcher_startup.log"
fi
exit "$RESULT"
