#!/usr/bin/env bash
# SoulPet 一键启动（macOS / Linux）
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo ""
echo "  SoulPet - 你的私有 AI 宠物"
echo "  ----------------------------------------"

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "  [x] 没检测到 Python，请先安装 Python 3.11+：https://www.python.org/downloads/"
  exit 1
fi

MAJOR=$("$PY" -c 'import sys;print(sys.version_info.major)')
MINOR=$("$PY" -c 'import sys;print(sys.version_info.minor)')
if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]; }; then
  echo "  [x] Python 版本过低（$MAJOR.$MINOR），请升级到 3.11+"
  exit 1
fi
echo "  [1/4] Python 就绪 ($MAJOR.$MINOR)"

if [ ! -d ".venv" ]; then
  echo "  [2/4] 首次运行，正在准备虚拟环境（约 1-3 分钟）..."
  "$PY" -m venv .venv
  ./.venv/bin/pip install -q --disable-pip-version-check -r requirements.txt
else
  echo "  [2/4] 虚拟环境已存在"
fi

echo "  [3/4] 正在拉起服务，浏览器会自动弹出..."
mkdir -p data/logs
echo ""
exec ./.venv/bin/python launcher/launcher.py "$@"
