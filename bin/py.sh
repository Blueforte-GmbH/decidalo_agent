#!/usr/bin/env bash
# Robuster Python-Launcher für die gebündelten Skill-Skripte.
#
# Warum: ein blankes `python3` löst je nach Kontext (Main-Thread vs. Subagent,
# lokale CLI vs. Cowork-Cloud) auf einen anderen Interpreter auf — oft auf ein
# PEP-668-gesperrtes System-/Homebrew-Python ohne lxml/click/requests, in dem
# `pip install` verweigert wird. Dieser Launcher erzwingt einen deterministischen
# Interpreter MIT den Deps aus requirements.txt:
#
#   1. ist `uv` vorhanden (typisch lokale CLI) -> ephemere, gecachte uv-Umgebung.
#   2. sonst (typisch Cloud/kein uv) -> projektlokales .venv bootstrappen.
#      Ein frisch erzeugtes venv ist NICHT "externally-managed", daher läuft
#      `pip` darin trotz PEP 668.
#
# Aufruf (relativ zum Repo-/Plugin-Root, wie die Skill-Pfade selbst):
#   bin/py.sh skills/fetch-blob/scripts/download_url.py --url … --output …
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REQ="$ROOT/requirements.txt"

# 1. uv-Pfad: schnell, gecacht, PEP-668-immun.
if command -v uv >/dev/null 2>&1; then
  exec uv run --no-project --with-requirements "$REQ" python "$@"
fi

# 2. Fallback: projektlokales venv bootstrappen.
VENV="$ROOT/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
if ! "$VENV/bin/python" -c "import lxml, click, requests" >/dev/null 2>&1; then
  "$VENV/bin/python" -m pip install -q --disable-pip-version-check -r "$REQ"
fi
exec "$VENV/bin/python" "$@"
