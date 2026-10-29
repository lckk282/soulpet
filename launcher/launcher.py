"""SoulPet 启动器。

职责：环境探测 → 端口顺延 → 写回配置 → 拉起服务 → 等健康 → 自动开浏览器 → 监护重启

用法：
    python launcher/launcher.py [--port 8787] [--no-browser] [--host 127.0.0.1]
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def pick_port(host: str, start: int, tries: int = 20) -> int:
    p = start
    for _ in range(tries):
        if not port_in_use(host, p):
            return p
        p += 1
    return start


def wait_health(host: str, port: int, timeout: float = 60.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    url = f"http://{host}:{port}/healthz"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.6)
    return False


def write_pid() -> None:
    try:
        from backend import paths

        paths.ensure_dirs()
        paths.PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="SoulPet launcher")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--reload", action="store_true", help="开发模式：代码改动自动重启")
    args = ap.parse_args()

    from backend import paths
    from backend.config_store import ensure_defaults, g, set_

    paths.ensure_dirs()
    ensure_defaults()

    cfg = g()
    want = args.port or cfg.server.port or 8787
    port = pick_port(args.host, want)
    if port != want:
        print(f"[launcher] 端口 {want} 被占用，改用 {port}")
    if port != cfg.server.port:
        cfg.server.port = port
        set_("global", cfg)

    url = f"http://{args.host}:{port}"
    initialized = bool(cfg.wizard.completed)

    def open_browser() -> None:
        if not wait_health(args.host, port, timeout=90):
            print("[launcher] 服务启动超时，请查看 data/logs/backend.log")
            return
        if args.no_browser or not cfg.server.auto_open_browser:
            print(f"[launcher] 服务就绪：{url}")
            return
        target = url + ("/chat" if initialized else "/")
        print(f"[launcher] 打开浏览器：{target}")
        try:
            webbrowser.open(target)
        except Exception:
            print(f"[launcher] 无法自动打开浏览器，请手动访问 {target}")

    threading.Thread(target=open_browser, daemon=True).start()
    write_pid()

    import uvicorn

    print(f"[launcher] SoulPet 启动中：{url}  （数据目录：{paths.HOME}）")
    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=port,
        reload=args.reload,
        log_level="info",
        workers=1,  # SQLite 必须单进程
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
