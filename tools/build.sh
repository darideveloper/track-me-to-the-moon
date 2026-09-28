#!/usr/bin/env bash
set -euo pipefail
# ponytail: onedir (not onefile) = faster start, fewer AV flags
pip install pyinstaller
ICON_ARG=""
[ -f assets/moon-icon.png ] && ICON_ARG="--icon assets/moon-icon.png"
# shellcheck disable=SC2086
pyinstaller --noconsole --onedir --name moon-tracker $ICON_ARG src/moon_tracker/app.py
echo "dist/moon-tracker/moon-tracker ready"
