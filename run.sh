#!/usr/bin/env bash
export LOG_PATH="${LOG_PATH:-$HOME/.nexus/logs/nexus.log}"
export PORT="${PORT:-5000}"
python3 app.py
