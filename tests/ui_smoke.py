"""SoulPet 端到端 UI 冒烟测试。

真开一个浏览器，从欢迎页一路点到最后一步提交，进聊天页发消息，
再回头验证「填错被拦住」的负向路径。

用法：
    python tests/ui_smoke.py              # 自带一个临时实例（独立数据目录 + 随机端口）
    python tests/ui_smoke.py --base-url http://127.0.0.1:8787   # 测已有实例
    python tests/ui_smoke.py --headed     # 看着它跑

依赖：playwright（pip install playwright && playwright install chromium）
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOT_DIR = ROOT / "shots" / "smoke"


# ---------------------------------------------------------------- 基础设施


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_health(base: str, timeout: float = 90.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base}/healthz", timeout=1.5) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    return False


class Server:
    """在临时数据目录里起一个干净的实例。"""

    def __init__(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="soulpet-smoke-"))
        self.port = free_port()
        self.proc: subprocess.Popen | None = None

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self) -> Server:
        env = {**os.environ, "SOULPET_HOME": str(self.home)}
        # 测试环境不碰真钥匙串（否则会往系统凭据管理器里写测试垃圾）
        env["SOULPET_SECRET_BACKEND"] = "file"
        self.proc = subprocess.Popen(
            [sys.executable, str(ROOT / "launcher" / "launcher.py"), "--port", str(self.port), "--no-browser"],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_health(self.base):
            self.__exit__(None, None, None)
            raise RuntimeError(f"服务启动失败，数据目录：{self.home}")
        return self

    def __exit__(self, *exc) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()


class Checker:
    def __init__(self) -> None:
        self.failed: list[str] = []
        self.passed: list[str] = []

    def ok(self, name: str, cond: bool, detail: str = "") -> bool:
        if cond:
            self.passed.append(name)
            print(f"  \033[32mPASS\033[0m {name}")
        else:
            self.failed.append(f"{name} {detail}".strip())
            print(f"  \033[31mFAIL\033[0m {name} {detail}")
        return cond


# ---------------------------------------------------------------- 主流程


def run(base: str, headed: bool) -> int:
    from playwright.sync_api import sync_playwright

    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    c = Checker()
    console_errors: list[str] = []
    page_errors: list[str] = []

    with sync_playwright() as pw:
        browser = None
        for kwargs in ({"channel": "msedge"}, {"channel": "chrome"}, {}):
            try:
                browser = pw.chromium.launch(headless=not headed, **kwargs)
                break
            except Exception:
                continue
        if browser is None:
            return _bail("没有可用的浏览器，请先执行 playwright install chromium")

        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        page.on("console", lambda m: console_errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.set_default_timeout(15000)

        def shot(name: str) -> None:
            page.screenshot(path=str(SHOT_DIR / f"{name}.png"), full_page=True)

        try:
            _walk(page, base, c, shot)
        except Exception as e:  # 任何一步崩了都要留下现场
            shot("zz-crash")
            c.ok("流程未崩溃", False, f"异常：{e!r}")
        finally:
            c.ok("浏览器控制台无 JS 报错", not console_errors, str(console_errors[:3]))
            c.ok("无未捕获异常", not page_errors, str(page_errors[:3]))
            ctx.close()
            browser.close()

    total = len(c.passed) + len(c.failed)
    print(f"\n{'=' * 56}\n{len(c.passed)}/{total} 通过")
    if c.failed:
        print("失败项：")
        for f in c.failed:
            print("  -", f)
        print(f"现场截图：{SHOT_DIR}")
        return 1
    print(f"全部通过，截图在 {SHOT_DIR}")
    return 0


def _bail(msg: str) -> int:
    print(msg)
    return 2


def _walk(page, base: str, c: Checker, shot) -> None:
    print("\n[1] 首页 / 欢迎页")
    page.goto(base, wait_until="networkidle")
    c.ok(
        "页面渲染出内容（非白屏）",
        "create" in page.content().lower() or "SoulPet" in page.title() or page.locator("text=知情").count() > 0,
        f"title={page.title()!r}",
    )
    c.ok(
        "样式已加载（有背景色）",
        page.evaluate("getComputedStyle(document.body).backgroundColor") not in ("", "rgba(0, 0, 0, 0)"),
    )
    c.ok("向导小灵出现", page.locator(".guide__pet").count() == 1)
    shot("01-welcome")

    print("\n[1b] 小屏（390px）向导布局")
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(600)
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    c.ok("390px 向导无横向溢出", overflow <= 1, f"溢出 {overflow}px")
    nav_rows = page.evaluate(
        "(() => { const items=[...document.querySelectorAll('.nav__item')];"
        " return items.length ? new Set(items.map(e => Math.round(e.getBoundingClientRect().top))).size : 0 })()"
    )
    c.ok("顶栏导航保持单行", nav_rows <= 1, f"占 {nav_rows} 行")
    shot("01b-welcome-mobile")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.wait_for_timeout(300)

    # 负向：没勾选就点下一步，必须被拦住
    print("\n[1c] 未捏宠时聊天页不该给输入框")
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(base + "/chat", wait_until="networkidle")
    page.wait_for_timeout(500)
    c.ok("提示还没有宠物", "还没有宠物" in page.inner_text("body"))
    c.ok("有「去创造向导」按钮", page.locator("button:has-text('去创造向导')").count() == 1)
    c.ok("不显示聊天输入框", page.locator(".chat-send textarea").count() == 0)
    page.goto(base, wait_until="networkidle")
    page.wait_for_timeout(400)

    print("\n[2] 负向：未勾选知情确认")
    page.locator(".wizard__actions button.primary").click()
    page.wait_for_timeout(700)
    c.ok("被拦在原地（未进入第 2 步）", page.locator(".inline-error").count() == 1)
    c.ok("小灵切到慌张表情", page.locator(".guide--alert").count() == 1)
    shot("02-blocked")

    print("\n[3] 勾选三项 → 形象页")
    for i in range(3):
        page.locator(".card input[type=checkbox]").nth(i).check()
    page.wait_for_timeout(300)
    c.ok("下一步按钮已可用", page.locator(".wizard__actions button.primary").is_enabled())
    page.locator(".wizard__actions button.primary").click()
    page.wait_for_timeout(500)
    c.ok("进入形象页", page.locator("input[placeholder='例如：小绫']").count() == 1)
    page.locator("input[placeholder='例如：小绫']").fill("测试小喵")
    page.locator("input[placeholder='例如：有点笨手笨脚但很努力']").fill("喜欢在键盘上睡觉")
    shot("03-identity")

    print("\n[4] 性格与作息")
    page.locator(".wizard__actions button.primary").click()
    page.wait_for_timeout(500)
    c.ok("出现活跃开始时间输入框", page.locator("input[placeholder='09:00']").count() == 1)
    # 负向：非法时间
    page.locator("input[placeholder='09:00']").fill("25:99")
    page.locator(".wizard__actions button.primary").click()
    page.wait_for_timeout(700)
    c.ok("非法时间被拦截", page.locator(".inline-error").count() == 1)
    c.ok("拦截时小灵慌张", page.locator(".guide--alert").count() == 1)
    shot("04-blocked-time")
    page.locator("input[placeholder='09:00']").fill("08:30")

    print("\n[5] 部署载体 → 本地")
    page.locator(".wizard__actions button.primary").click()
    page.wait_for_timeout(500)
    c.ok("部署页有两个选项卡", page.locator(".radio-card").count() >= 2)
    shot("05-deploy")

    print("\n[6] 模型与额度（离线体验）")
    page.locator(".wizard__actions button.primary").click()
    page.wait_for_timeout(500)
    offline_btn = page.locator("button:has-text('离线体验')")
    c.ok("有「离线体验」按钮", offline_btn.count() == 1, f"count={offline_btn.count()}")
    c.ok(
        "台词切换成额度相关",
        "额度" in page.locator(".guide__text").inner_text() or "上限" in page.locator(".guide__text").inner_text(),
    )
    # 空 Key 直接下一步只该报一条错，且不该去校验用户没碰过的 API 地址
    page.locator(".wizard__actions button.primary").click()
    page.wait_for_timeout(400)
    err_text = page.locator(".inline-error").inner_text() if page.locator(".inline-error").count() else ""
    c.ok("空 Key 拦截只报一条", len([x for x in err_text.splitlines() if x.strip()]) == 1, f"errors={err_text!r}")
    c.ok("空 Key 提示指向离线体验", "离线体验" in err_text, f"errors={err_text!r}")
    offline_btn.first.click()
    page.wait_for_timeout(400)
    c.ok("离线模式下模型名已填好", bool(page.locator("input[placeholder='以厂商后台显示为准']").input_value()))
    c.ok(
        "离线模式下 API 地址合法", page.locator("input[placeholder='https://.../v1']").input_value().startswith("http")
    )
    c.ok("离线模式选中态有回显", "已选" in offline_btn.first.inner_text(), offline_btn.first.inner_text())
    # 先试离线、再换成真服务商：模型名不能还残留 mock
    page.locator(".chip:has-text('智谱')").first.click()
    page.wait_for_timeout(300)
    mname = page.locator("input[placeholder='以厂商后台显示为准']").input_value()
    c.ok("切到真服务商后模型名不是 mock", mname and mname != "mock", f"model={mname!r}")
    offline_btn.first.click()
    page.wait_for_timeout(300)
    shot("06-model")

    print("\n[7] 功能模块")
    page.locator(".wizard__actions button.primary").click()
    page.wait_for_timeout(500)
    c.ok("模块页有两个开关", page.locator(".radio-card button").count() >= 2)
    shot("07-modules")

    print("\n[8] 确认页 → 提交")
    page.locator(".wizard__actions button.primary").click()
    page.wait_for_timeout(500)
    submit = page.locator("button:has-text('确认生成')")
    c.ok("确认页出现提交按钮", submit.count() == 1, f"count={submit.count()}")
    shot("08-confirm")
    submit.first.click()

    print("\n[9] 落地到聊天页")
    page.wait_for_url("**/chat", timeout=30000)
    c.ok("提交成功并跳到 /chat", "/chat" in page.url, page.url)
    page.wait_for_timeout(800)
    c.ok("聊天页显示宠物名", "测试小喵" in page.content())
    shot("09-chat")

    print("\n[10] 发一条消息")
    box = page.locator(".chat-send textarea")
    box.fill("你好呀，你叫什么名字？")
    page.locator(".chat-send button").click()
    page.wait_for_function("() => document.querySelectorAll('.msg--assistant .bubble').length >= 1", timeout=40000)
    reply = page.locator(".msg--assistant .bubble").last.inner_text()
    c.ok("收到宠物回复", len(reply.strip()) > 0, f"回复={reply[:40]!r}")
    shot("10-reply")

    print("\n[10b] 二次打开首页直接回聊天页")
    page.goto(base, wait_until="networkidle")
    page.wait_for_timeout(900)
    c.ok("落地 /chat 而不是空白向导", "/chat" in page.evaluate("location.pathname"), page.evaluate("location.href"))
    c.ok("聊天记录还在", "你好呀" in page.inner_text("body"))

    print("\n[10c] 设置页可重新进入向导")
    page.goto(base + "/settings", wait_until="networkidle")
    page.wait_for_timeout(500)
    redo = page.locator("button:has-text('重新运行创造向导')")
    c.ok("有重新运行向导入口", redo.count() == 1, f"count={redo.count()}")
    redo.first.click()
    page.wait_for_timeout(1500)
    # 注意：pushState 之后 page.url 有时会滞后，用 location.href 读真实地址
    c.ok("URL 带上 edit=1", "edit=1" in page.evaluate("location.search"), page.evaluate("location.href"))
    c.ok("重进向导不再被踢回聊天", "创造向导" in page.inner_text("body"), page.evaluate("location.href"))
    c.ok("提示会覆盖现有配置", "覆盖" in page.inner_text("body"))

    print("\n[10d] 点 Logo 走客户端跳转（这条曾经挂住不动）")
    page.locator(".brand").click()
    page.wait_for_timeout(1500)
    c.ok("已有宠物时 Logo → 聊天页", "/chat" in page.evaluate("location.pathname"), page.evaluate("location.href"))
    c.ok("切过去真的渲染了聊天页", page.locator(".chat-card").count() == 1)

    print("\n[11] 记忆 / 状态 / 设置页可打开")
    for path, marker in (("/memory", "记忆"), ("/status", "状态"), ("/settings", "设置")):
        page.goto(base + path, wait_until="networkidle")
        page.wait_for_timeout(400)
        c.ok(f"{path} 正常渲染", marker in page.content() and len(page.content()) > 2000)
    shot("11-settings")

    print("\n[12] 移动端 390px 无横向溢出")
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(base + "/chat", wait_until="networkidle")
    page.wait_for_timeout(600)
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    c.ok("390px 无横向滚动", overflow <= 1, f"溢出 {overflow}px")
    shot("12-mobile")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    if args.base_url:
        return run(args.base_url, args.headed)

    print("启动临时实例…")
    with Server() as srv:
        print(f"实例就绪：{srv.base}（数据目录 {srv.home}）")
        rc = run(srv.base, args.headed)
        dump = srv.home / "data" / "logs" / "backend.log"
        if rc and dump.exists():
            print(f"\n后端日志尾部（{dump}）：")
            print("\n".join(dump.read_text(encoding="utf-8", errors="replace").splitlines()[-25:]))
        return rc


if __name__ == "__main__":
    raise SystemExit(main())
