"""Deterministic SVG covers (no external assets, no image libraries)."""

from __future__ import annotations

import hashlib
from xml.sax.saxutils import escape

PALETTES: dict[str, tuple[str, str, str]] = {
    "美妆个护": ("#fde7ef", "#f7c6d9", "#d6336c"),
    "数码配件": ("#e7f0fd", "#c6dbf7", "#1c64d6"),
    "食品饮料": ("#fdf3e0", "#f7dfb8", "#c2790a"),
    "家居日用": ("#eaf6ee", "#c9e8d5", "#1f7a4d"),
    "运动户外": ("#eef7f0", "#cfe9d8", "#0f766e"),
}
DEFAULT_PALETTE = ("#eef2ff", "#dbe3ff", "#4f46e5")

GLYPHS: dict[str, str] = {
    "美妆个护": "✿",
    "数码配件": "♫",
    "食品饮料": "☕",
    "家居日用": "⌂",
    "运动户外": "⛰",
}


def _palette(key: str) -> tuple[str, str, str]:
    return PALETTES.get(key, DEFAULT_PALETTE)


def _seed(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16)


def _wrap(text: str, per_line: int = 9, max_lines: int = 2) -> list[str]:
    text = (text or "").strip()
    lines: list[str] = []
    while text and len(lines) < max_lines:
        lines.append(text[:per_line])
        text = text[per_line:]
    if text and lines:
        lines[-1] = lines[-1][: per_line - 1] + "…"
    return lines or ["商品"]


def _svg(height: int, width: int, background: str, parts: list[str]) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{background}"/>'
        f'<stop offset="100%" stop-color="#ffffff"/></linearGradient></defs>'
        f'<rect width="{width}" height="{height}" fill="url(#g)"/>'
        + "".join(parts)
        + "</svg>"
    )


def product_cover(item_id: str, title: str, category: str, price: float | None = None,
                  size: int = 480) -> str:
    light, mid, accent = _palette(category)
    seed = _seed(item_id)
    cx = 90 + seed % (size - 180)
    cy = 120 + (seed >> 5) % (size - 240)
    lines = _wrap(title)
    text_parts = [
        f'<text x="{size / 2}" y="{size - 92 + index * 34}" text-anchor="middle" '
        f'font-family="Microsoft YaHei, Segoe UI, sans-serif" font-size="26" '
        f'fill="#1f2430">{escape(line)}</text>'
        for index, line in enumerate(lines)
    ]
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="{size // 3}" fill="{mid}" opacity="0.55"/>',
        f'<circle cx="{size - cx // 2}" cy="{size - cy // 2}" r="{size // 4}" '
        f'fill="{light}" opacity="0.8"/>',
        f'<text x="{size / 2}" y="{size / 2 + 30}" text-anchor="middle" '
        f'font-family="Segoe UI Symbol, Microsoft YaHei, sans-serif" '
        f'font-size="{size // 4}" fill="{accent}" opacity="0.85">'
        f'{GLYPHS.get(category, "◆")}</text>',
        f'<rect x="24" y="24" width="{8 * len(category) + 32}" height="34" rx="17" '
        f'fill="#ffffff" opacity="0.85"/>',
        f'<text x="40" y="47" font-family="Microsoft YaHei, sans-serif" font-size="17" '
        f'fill="{accent}">{escape(category)}</text>',
        *text_parts,
    ]
    if price is not None:
        parts.append(
            f'<text x="{size - 28}" y="{size - 30}" text-anchor="end" '
            f'font-family="Segoe UI, sans-serif" font-size="24" font-weight="700" '
            f'fill="{accent}">¥{price:.0f}</text>'
        )
    return _svg(size, size, light, parts)


def post_cover(post_id: str, title: str, media_type: str = "image", seconds: int = 0,
               theme: str = "生活", size: int = 480) -> str:
    light, mid, accent = _palette(theme)
    seed = _seed(post_id)
    lines = _wrap(title, per_line=8)
    text_parts = [
        f'<text x="36" y="{size - 110 + index * 36}" font-family="Microsoft YaHei, '
        f'sans-serif" font-size="27" font-weight="700" fill="#1f2430">'
        f'{escape(line)}</text>'
        for index, line in enumerate(lines)
    ]
    parts = [
        f'<rect x="0" y="0" width="{size}" height="{size * 0.55}" fill="{mid}" '
        f'opacity="0.65"/>',
        f'<circle cx="{size * 0.72}" cy="{size * 0.24}" r="{size * 0.18}" '
        f'fill="{light}"/>',
        f'<text x="{size * 0.2}" y="{size * 0.38}" font-family="Segoe UI Symbol, '
        f'sans-serif" font-size="{size // 5}" fill="{accent}" opacity="0.9">'
        f'{GLYPHS.get(theme, "✿")}</text>',
        f'<rect x="24" y="24" width="120" height="32" rx="16" fill="{accent}" '
        f'opacity="0.9"/>',
        f'<text x="84" y="46" text-anchor="middle" font-family="Microsoft YaHei, '
        f'sans-serif" font-size="16" fill="#ffffff">买家安利</text>',
        *text_parts,
    ]
    if media_type == "video":
        total = max(1, int(seconds))
        badge = f"▶ 0:{total:02d}"
        parts += [
            f'<circle cx="{size / 2}" cy="{size * 0.28}" r="52" fill="#0f172a" '
            f'opacity="0.55"/>',
            f'<text x="{size / 2}" y="{size * 0.28 + 14}" text-anchor="middle" '
            f'font-size="40" fill="#ffffff">▶</text>',
            f'<rect x="{size - 118}" y="24" width="94" height="30" rx="15" '
            f'fill="#0f172a" opacity="0.7"/>',
            f'<text x="{size - 71}" y="45" text-anchor="middle" '
            f'font-family="Segoe UI, sans-serif" font-size="15" fill="#ffffff">'
            f'{escape(badge)}</text>',
        ]
    return _svg(size, size, light, parts)


def avatar_cover(name: str, size: int = 96) -> str:
    seed = _seed(name)
    hue = seed % 360
    initials = escape((name or "U")[:1].upper())
    return _svg(
        size, size, f"hsl({hue}, 70%, 88%)",
        [f'<text x="{size / 2}" y="{size * 0.66}" text-anchor="middle" '
         f'font-family="Segoe UI, sans-serif" font-size="{size // 2.4}" '
         f'font-weight="700" fill="hsl({hue}, 55%, 35%)">{initials}</text>'],
    )


def post_gallery(post_id: str, title: str, media_type: str, seconds: int, theme: str,
                 index: int, size: int = 480) -> str:
    """帖子多图：同一帖子用不同种子生成多张构图不同的封面。"""
    variant_id = f"{post_id}-{index}"
    theme_cycle = ["美妆个护", "家居日用", "食品饮料", "数码配件", "运动户外"]
    shifted = theme_cycle[(index + 1) % len(theme_cycle)] if index else theme
    svg = post_cover(variant_id, title, media_type, seconds, shifted or theme, size)
    badge = f'<text x="{size - 26}" y="{size - 24}" text-anchor="end" ' \
            f'font-family="Segoe UI, sans-serif" font-size="18" fill="#6b5c4e">' \
            f'{index + 1}/3</text>'
    return svg.replace("</svg>", badge + "</svg>")
