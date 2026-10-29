"""素材包：内置默认形象生成 + 完整性校验。

默认形象用参数化 SVG 生成（仓库里不放二进制图片，体积小、可 diff、可手改）。
校验不需要 Pillow：PNG 直接读 IHDR 头拿宽高与是否有 alpha 通道。
"""

from __future__ import annotations

import json
import struct
import zipfile
from pathlib import Path

from .. import paths

SLOTS = ["front", "front45", "side", "back45", "back", "side_down", "happy", "shy", "sad"]
SLOT_LABELS = {
    "front": "正面",
    "front45": "45°侧前",
    "side": "侧面",
    "back45": "背侧",
    "back": "背面",
    "side_down": "低头侧脸",
    "happy": "开心",
    "shy": "害羞",
    "sad": "委屈",
}
DEFAULT_PACK_ID = "pack_default"


# ── PNG 头解析 ──────────────────────────────────────────────────


def png_info(path: Path) -> dict | None:
    """读取 PNG IHDR：宽、高、是否有 alpha。无需第三方库。"""
    try:
        with path.open("rb") as f:
            head = f.read(26)
        if len(head) < 26 or head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        w, h = struct.unpack(">II", head[16:24])
        depth, color = head[24], head[25]
        alpha = color in (4, 6)
        return {"width": w, "height": h, "alpha": alpha, "bit_depth": depth, "color_type": color}
    except Exception:
        return None


# ── 默认形象（SVG） ─────────────────────────────────────────────


def _svg(view: str, expr: str) -> str:
    """参数化生成一个 Q 版角色 SVG（同一套配色与比例，保证一致性）。"""
    skin = "#ffe0d0"
    hair = "#8f7bd6"
    dress = "#5b6ee1"
    eye_open = '<ellipse cx="{cx}" cy="150" rx="9" ry="12" fill="#2b2b3a"/>'
    eye_closed = '<path d="M{cx1} 150 q 10 10 20 0" stroke="#2b2b3a" stroke-width="3" fill="none"/>'
    eye_wide = '<ellipse cx="{cx}" cy="150" rx="11" ry="14" fill="#2b2b3a"/>'

    if expr == "happy":
        eyes = eye_closed.format(cx1=170) + eye_closed.format(cx1=210)
        mouth = '<path d="M186 176 q 14 14 28 0" stroke="#c0466a" stroke-width="4" fill="none" stroke-linecap="round"/>'
        blush = '<ellipse cx="158" cy="168" rx="12" ry="7" fill="#ff9db1" opacity="0.75"/><ellipse cx="242" cy="168" rx="12" ry="7" fill="#ff9db1" opacity="0.75"/>'
    elif expr == "shy":
        eyes = eye_open.format(cx=180) + eye_open.format(cx=220)
        mouth = '<path d="M190 180 q 10 -6 20 0" stroke="#c0466a" stroke-width="3" fill="none" stroke-linecap="round"/>'
        blush = '<ellipse cx="156" cy="166" rx="14" ry="8" fill="#ff7f9f" opacity="0.85"/><ellipse cx="244" cy="166" rx="14" ry="8" fill="#ff7f9f" opacity="0.85"/>'
    elif expr == "sad":
        eyes = eye_wide.format(cx=180) + eye_wide.format(cx=220)
        mouth = (
            '<path d="M188 184 q 12 -12 24 0" stroke="#c0466a" stroke-width="4" fill="none" stroke-linecap="round"/>'
        )
        blush = '<ellipse cx="180" cy="186" rx="5" ry="9" fill="#8ec9ff" opacity="0.8"/><ellipse cx="220" cy="186" rx="5" ry="9" fill="#8ec9ff" opacity="0.8"/>'
    else:
        eyes = eye_open.format(cx=180) + eye_open.format(cx=220)
        mouth = '<path d="M192 178 q 8 6 16 0" stroke="#c0466a" stroke-width="3" fill="none" stroke-linecap="round"/>'
        blush = ""

    # 视角：用水平缩放与偏移近似"转身"
    transforms = {
        "front": (1.0, 0),
        "front45": (0.88, 12),
        "side": (0.7, 26),
        "back45": (-0.88, -12),
        "back": (-1.0, 0),
        "side_down": (0.7, 26),
    }
    sx, dx = transforms.get(view, (1.0, 0))
    head_tilt = "rotate(10 200 140)" if view == "side_down" else ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <g transform="translate({dx} 0) scale({sx} 1) translate({(1 - sx) * 200} 0)">
    <g {head_tilt}>
      <path d="M200 78 q 62 0 62 66 q 0 44 -30 58 q -32 14 -64 0 q -30 -14 -30 -58 q 0 -66 62 -66z" fill="{hair}"/>
      <circle cx="200" cy="150" r="58" fill="{skin}"/>
      <path d="M142 140 q 58 -42 116 0 q 4 -46 -58 -48 q -62 2 -58 48z" fill="{hair}"/>
      {eyes}
      {mouth}
      {blush}
    </g>
    <path d="M200 206 q 52 0 66 60 l 14 96 q -80 18 -160 0 l 14 -96 q 14 -60 66 -60z" fill="{dress}"/>
    <path d="M160 250 q 40 -16 80 0" stroke="#ffffff" stroke-width="8" fill="none" opacity="0.65"/>
    <rect x="150" y="352" width="34" height="26" rx="10" fill="#2b2b3a"/>
    <rect x="216" y="352" width="34" height="26" rx="10" fill="#2b2b3a"/>
  </g>
</svg>"""


def ensure_default_pack() -> Path:
    """生成内置默认素材包（幂等）。"""
    d = paths.ASSET_DIR / DEFAULT_PACK_ID
    d.mkdir(parents=True, exist_ok=True)
    slots = {}
    for slot in SLOTS:
        view = slot if slot in ("front", "front45", "side", "back45", "back", "side_down") else "front"
        expr = slot if slot in ("happy", "shy", "sad") else "neutral"
        p = d / f"{slot}.svg"
        p.write_text(_svg(view, expr), encoding="utf-8")
        slots[slot] = {"file": f"{slot}.svg", "note": "内置默认形象（SVG）"}

    actions = [
        {
            "id": "idle",
            "type": "procedural",
            "base": "front",
            "curve": {"scale": [1.0, 1.02], "dy": [0, -3], "dur_ms": 2400, "loop": "pingpong"},
        },
        {
            "id": "sway",
            "type": "procedural",
            "base": "front",
            "curve": {"rotate": [-3, 3], "dur_ms": 1800, "loop": "pingpong"},
        },
        {
            "id": "wave",
            "type": "procedural",
            "base": "front45",
            "curve": {"rotate": [0, 8], "dur_ms": 900, "loop": "once"},
        },
        {
            "id": "tilt",
            "type": "procedural",
            "base": "front45",
            "curve": {"rotate": [0, 8], "dur_ms": 900, "loop": "once"},
        },
        {
            "id": "blink",
            "type": "frames",
            "frames": ["front", "shy"],
            "dur_ms": 200,
            "loop": "random",
            "interval_ms": [2200, 6000],
        },
        {
            "id": "jump",
            "type": "procedural",
            "base": "happy",
            "curve": {"dy": [0, -40, 0], "scale": [1.0, 1.06, 1.0], "dur_ms": 700, "loop": "once"},
        },
    ]
    manifest = {
        "schema": "soulpet.assetpack/1.0",
        "pack_id": DEFAULT_PACK_ID,
        "created_at": "",
        "source": {"type": "builtin", "backend": "svg"},
        "slots": slots,
        "actions": actions,
    }
    (d / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return d


# ── 校验 ────────────────────────────────────────────────────────


def validate_pack(pack_dir: Path) -> dict:
    missing: list[str] = []
    warnings: list[str] = []
    slots: dict[str, dict] = {}

    mpath = pack_dir / "manifest.json"
    if not mpath.exists():
        return {"complete": False, "missing": SLOTS, "warnings": ["缺少 manifest.json"], "slots": {}}

    try:
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
    except Exception as e:
        return {"complete": False, "missing": SLOTS, "warnings": [f"manifest 解析失败：{e}"], "slots": {}}

    declared = manifest.get("slots", {})
    for slot in SLOTS:
        meta = declared.get(slot)
        if not meta:
            missing.append(slot)
            continue
        f = pack_dir / meta.get("file", "")
        if not f.exists():
            missing.append(slot)
            continue
        info = None
        if f.suffix.lower() == ".png":
            info = png_info(f)
            if not info:
                warnings.append(f"{SLOT_LABELS[slot]}：不是有效的 PNG")
            else:
                if min(info["width"], info["height"]) < 256:
                    warnings.append(f"{SLOT_LABELS[slot]}：尺寸偏小 {info['width']}x{info['height']}")
                if not info["alpha"]:
                    warnings.append(f"{SLOT_LABELS[slot]}：缺少透明通道，桌宠可能有白底")
        slots[slot] = {"file": f.name, "size": f.stat().st_size, **(info or {})}

    return {
        "complete": not missing,
        "missing": missing,
        "missing_labels": [SLOT_LABELS[m] for m in missing],
        "warnings": warnings,
        "slots": slots,
        "actions": manifest.get("actions", []),
    }


def packs() -> list[dict]:
    paths.ensure_dirs()
    out = []
    if paths.ASSET_DIR.exists():
        for d in sorted(paths.ASSET_DIR.iterdir()):
            if d.is_dir() and (d / "manifest.json").exists():
                try:
                    m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
                except Exception:
                    continue
                out.append({"id": d.name, "path": str(d), "source": (m.get("source") or {}).get("type", "unknown")})
    return out


MAX_ENTRIES = 2000
MAX_UNCOMPRESSED = 200 * 1024 * 1024
ALLOWED_SUFFIX = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".json", ".txt", ".md"}


def safe_extract(zip_path: Path, dest: Path) -> None:
    """解压并防 Zip Slip 路径穿越。

    三道闸：路径必须落在 dest 内（用 resolve + is_relative_to，不用字符串前缀 ——
    `pack_10/x` 会以 `pack_1` 为前缀而蒙过检查）、文件数上限、解压后总大小上限
    （20MB 的 zip 可以解出几十 GB，即所谓 zip 炸弹）。
    """
    dest.mkdir(parents=True, exist_ok=True)
    root = dest.resolve()
    with zipfile.ZipFile(zip_path) as z:
        infos = z.infolist()
        if len(infos) > MAX_ENTRIES:
            raise ValueError(f"压缩包内文件过多（上限 {MAX_ENTRIES} 个）")
        total = sum(max(0, i.file_size) for i in infos)
        if total > MAX_UNCOMPRESSED:
            raise ValueError(f"解压后体积过大（{total // (1024 * 1024)}MB，上限 200MB）")
        for entry in infos:
            if entry.is_dir():
                continue
            target = (root / entry.filename).resolve()
            if target != root and not target.is_relative_to(root):
                raise ValueError(f"压缩包内含有非法路径：{entry.filename}")
            if target.suffix.lower() not in ALLOWED_SUFFIX:
                raise ValueError(f"素材包内不允许的文件类型：{entry.filename}")
        z.extractall(root)
