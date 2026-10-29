#!/usr/bin/env bash
# SoulPet 停止脚本（macOS / Linux）
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ -f data/backend.pid ]; then
  PID="$(cat data/backend.pid)"
  if [ -n "${PID:-}" ]; then
    echo "正在停止 SoulPet（pid=$PID）..."
    kill "$PID" 2>/dev/null || true
    sleep 2
    kill -9 "$PID" 2>/dev/null || true
    rm -f data/backend.pid
    echo "已停止。"
  fi
else
  echo "未找到 data/backend.pid，可能服务未运行。"
fi
