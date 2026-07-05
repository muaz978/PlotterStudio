#!/usr/bin/env bash
# Plotter Studio launcher for macOS / Linux.
# First run: sets up a private virtualenv, installs deps, ensures potrace.
# Later runs: just launches. Double-click this file (macOS) or run ./run.command
set -e
cd "$(dirname "$0")"

echo "▶ Plotter Studio setup…"

# 1) potrace (the high-quality tracer)
if ! command -v potrace >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "  installing potrace via Homebrew…"
    brew install potrace
  else
    echo "  ⚠ potrace not found and Homebrew is missing."
    echo "    Install Homebrew from https://brew.sh then re-run, or 'sudo apt install potrace' on Linux."
  fi
fi

# 2) private virtualenv + Python deps
if [ ! -d .venv ]; then
  echo "  creating virtual environment…"
  python3 -m venv .venv
fi
./.venv/bin/python -m pip install --quiet --upgrade pip
./.venv/bin/python -m pip install --quiet -r requirements.txt

# 3) launch
echo "▶ starting Plotter Studio"
exec ./.venv/bin/python plotter_studio.py
