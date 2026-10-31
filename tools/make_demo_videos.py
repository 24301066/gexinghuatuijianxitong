"""批量生成演示视频：给每个视频帖生成一个可播放的 mp4（渐变背景 + 标题动效）。

用法：
    python tools/make_demo_videos.py --ffmpeg <ffmpeg.exe 路径> [--data-dir <数据目录>]

生成的视频写到 <data-dir>/media/posts/<post_id>.mp4，帖子详情页会直接播放。
已有 mp4 的帖子会跳过，可重复执行。
"""

from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

PALETTES = {
    "美妆个护": ("0xF7C6D9", "0xFDE7EF"),
    "数码配件": ("0xC6DBF7", "0xE7F0FD"),
    "食品饮料": ("0xF7DFB8", "0xFDF3E0"),
    "家居日用": ("0xC9E8D5", "0xEAF6EE"),
    "运动户外": ("0xCFE9D8", "0xEEF7F0"),
}
DEFAULT_PALETTE = ("0x4F46E5", "0xDBE3FF")
FONT_CANDIDATES = [
    r"C:/Windows/Fonts/msyh.ttc",
    r"C:/Windows/Fonts/msyhbd.ttc",
    r"C:/Windows/Fonts/simhei.ttf",
]


def find_ffmpeg(explicit: str | None) -> str:
    if explicit:
        return explicit
    for name in ("ffmpeg", "ffmpeg.exe"):
        from shutil import which

        found = which(name)
        if found:
            return found
    raise SystemExit("找不到 ffmpeg，请用 --ffmpeg 指定 ffmpeg.exe 路径")


def pick_font() -> str:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return candidate
    raise SystemExit("找不到中文字体（msyh.ttc），请安装微软雅黑")


def load_posts(db_path: Path) -> list[tuple[str, str, int, str]]:
    connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT p.post_id, p.title, p.video_seconds, i.category "
            "FROM posts p LEFT JOIN items i ON i.item_id = p.product_id "
            "WHERE p.media_type = 'video' ORDER BY p.post_id").fetchall()
    finally:
        connection.close()
    return [(row[0], row[1], int(row[2] or 6), row[3] or "") for row in rows]


def _escape(value: str) -> str:
    return (value.replace("\\", "\\\\").replace(":", "\\:")
            .replace("'", "\\'").replace("%", "\\%"))


def make_video(ffmpeg: str, font: str, post: tuple[str, str, int, str],
               out_dir: Path) -> bool:
    post_id, title, seconds, category = post
    target = out_dir / f"{post_id}.mp4"
    if target.is_file() and target.stat().st_size > 1024:
        print(f"skip {post_id} (exists)")
        return False
    seconds = max(4, min(seconds, 30))
    c0, c1 = PALETTES.get(category, DEFAULT_PALETTE)
    # 老版本 ffmpeg 没有 gradients 滤镜，用纯色背景 + 两个移动色块模拟渐变动效
    source = f"color=c={c0}:s=720x720:d={seconds}"
    filters = (
        f"drawbox=x='-200+120*t':y=0:w=420:h=720:color={c1}@0.55:t=fill,"
        f"drawbox=x='520-90*t':y='220+50*sin(t)':w=220:h=220:color=white@0.18:t=fill,"
        f"drawtext=fontfile='{font}':text='{_escape(title[:40])}':fontsize=42:"
        f"fontcolor=white:borderw=2:bordercolor=black@0.2:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:alpha='min(1\\,t/1.2)'"
    )
    command = [
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", source,
        "-vf", filters,
        "-t", str(seconds), "-r", "24",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(target),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"fail {post_id}: {result.stderr.strip()[:200]}")
        return False
    print(f"ok   {post_id}  {target.stat().st_size // 1024} KB  {seconds}s")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成帖子演示视频")
    parser.add_argument("--ffmpeg", default=None)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args(argv)

    from app.config import load_settings

    settings = load_settings(args.data_dir)
    db_path = settings.db_path
    if not db_path.is_file():
        raise SystemExit(f"数据库不存在：{db_path}")
    out_dir = settings.data_dir / "media" / "posts"
    out_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = find_ffmpeg(args.ffmpeg)
    font = pick_font()
    posts = load_posts(db_path)
    if args.limit:
        posts = posts[: args.limit]
    print(f"ffmpeg: {ffmpeg}")
    print(f"输出目录: {out_dir}")
    print(f"待处理视频帖: {len(posts)}")
    done = sum(make_video(ffmpeg, font, post, out_dir) for post in posts)
    print(f"完成 {done} 个 / 共 {len(posts)} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
