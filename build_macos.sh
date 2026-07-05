#!/usr/bin/env bash
# Build a standalone Plotter Studio.app (bundles Python + potrace).
# Result: dist/PlotterStudio.app
set -e
cd "$(dirname "$0")"

command -v potrace >/dev/null 2>&1 || { echo "install potrace first: brew install potrace"; exit 1; }
POTRACE="$(command -v potrace)"

python3 -m venv .buildenv
./.buildenv/bin/python -m pip install --quiet --upgrade pip pyinstaller
./.buildenv/bin/python -m pip install --quiet -r requirements.txt
./.buildenv/bin/pyinstaller --noconfirm --windowed --name PlotterStudio \
  --add-binary "$POTRACE:bin" \
  plotter_studio.py

echo "✔ Built dist/PlotterStudio.app"
