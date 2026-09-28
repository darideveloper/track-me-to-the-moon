#!/usr/bin/env bash
set -euo pipefail
# ponytail: onedir (not onefile) = faster start, fewer AV flags
pip install pyinstaller
pyinstaller --noconsole --onedir --name worktracker src/worktracker/app.py
echo "dist/worktracker/worktracker ready"
