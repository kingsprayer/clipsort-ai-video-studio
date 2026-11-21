#!/usr/bin/env bash
# ==============================================================================
# ClipSort AI — Studio Launcher Script
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec python3 run_studio.py "$@"
