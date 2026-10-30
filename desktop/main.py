"""Desktop entry point: starts the bundled API, then hosts the UI in a native window.

CLI:
    python desktop/main.py                 # normal desktop window
    python desktop/main.py --no-window     # headless: start server, print URL, exit 0
    python desktop/main.py --data-dir DIR  # override the data directory

Design notes (see openspec/changes/ecommerce-recommender-mvp/design.md, D8):
- uvicorn runs in a background thread with workers=1;
- the window uses wx.html2's Edge backend (system WebView2), no bundled browser;
- if the WebView cannot render, the same URL is opened in the system browser;
- if no writable data directory exists, show a readable dialog instead of a traceback.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
if BACKEND.is_dir() and str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import app_core  # noqa: E402

WEBVIEW_TIMEOUT_SECONDS = 8.0
MB_ICONERROR = 0x10
MB_ICONWARNING = 0x30


def show_message(text: str, caption: str = app_core.APP_TITLE, flags: int = MB_ICONERROR) -> None:
    """Native message box without importing wx (works before any GUI setup)."""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, caption, flags)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - headless fallback
        say(f"{caption}: {text}")


def _log_targets() -> list[Path]:
    """Crash logs go next to the exe first, then TEMP (both are usually writable)."""
    targets: list[Path] = []
    try:
        targets.append(Path(sys.executable).resolve().parent / "GexingTuijian-crash.log")
    except OSError:
        pass
    temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if temp:
        targets.append(Path(temp) / "GexingTuijian-crash.log")
    try:
        targets.append(Path.home() / "GexingTuijian-crash.log")
    except OSError:
        pass
    return targets


def log_lines(lines: list[str], target: Path | None = None) -> list[Path]:
    """Append a log block; returns the paths that were actually written."""
    block = time.strftime("[%Y-%m-%d %H:%M:%S] ") + "\n".join(lines) + "\n"
    written: list[Path] = []
    for path in ([target] if target else []) + _log_targets():
        if path is None:
            continue
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(block)
            written.append(path)
        except OSError:
            continue
    return written


def log_fatal(detail: str) -> list[Path]:
    return log_lines(["fatal error", detail], None)


def say(message: str) -> None:
    """print() without crashing when the process has no console (windowed exe)."""
    if sys.stdout is not None:
        try:
            print(message)
        except (OSError, ValueError):
            pass


def ensure_std_streams() -> None:
    """A GUI-subsystem exe / pythonw has no std handles; libraries expect strings."""
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115


def build_log_config(log_file: Path) -> dict:
    """uvicorn's default logging writes to sys.stderr; point it at a file instead."""
    loggers = {
        "uvicorn": {"handlers": ["file"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["file"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["file"], "level": "WARNING", "propagate": False},
    }
    handlers: dict = {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_file),
            "maxBytes": 2_000_000,
            "backupCount": 2,
            "encoding": "utf-8",
            "formatter": "plain",
        }
    }
    if sys.stderr is not None and getattr(sys.stderr, "isatty", None) and sys.stderr.isatty():
        handlers["console"] = {"class": "logging.StreamHandler", "stream": "ext://sys.stderr",
                               "formatter": "plain"}
        for logger in loggers.values():
            logger["handlers"].append("console")
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
            "access": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
        },
        "handlers": handlers,
        "loggers": loggers,
    }


def start_server(data_directory: Path, port: int) -> tuple[object, threading.Thread]:
    import uvicorn

    from app import create_app
    from app.config import load_settings

    settings = load_settings(data_directory)
    application = create_app(settings)
    log_file = data_directory / "logs" / "uvicorn.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    config = uvicorn.Config(application, host="127.0.0.1", port=port, log_level="info",
                            workers=1, access_log=False,
                            log_config=build_log_config(log_file))
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True, name="uvicorn")
    thread.start()
    return server, thread


def start_server_with_fallback(port: int, explicit: Path | None = None,
                               portable_first: bool = False
                               ) -> tuple[object, threading.Thread, Path]:
    """Try every usable data directory until the app actually starts.

    The probe in ``is_writable`` covers most cases, but a directory can still fail
    at the first commit (e.g. its ACL denies deleting the SQLite journal). Walking
    the candidate list here turns that into a fallback instead of a crash dialog.
    """
    from sqlalchemy.exc import DatabaseError, OperationalError

    from app.config import data_dir_candidates, is_writable

    last_error: Exception | None = None
    for candidate in data_dir_candidates(explicit, portable_first):
        if not is_writable(candidate):
            log_lines([f"data dir not usable, skipped: {candidate}"])
            continue
        try:
            server, thread = start_server(candidate, port)
            log_lines([f"data dir in use: {candidate}"])
            return server, thread, candidate
        except (OperationalError, DatabaseError) as exc:
            last_error = exc
            log_lines([f"data dir failed at startup, trying next: {candidate}",
                       str(exc)[:500]])
            continue
    raise last_error or RuntimeError("没有可用的数据目录")


def stop_server(server, thread: threading.Thread, timeout: float = 5.0) -> None:
    server.should_exit = True
    thread.join(timeout=timeout)


def webview2_available() -> bool:
    if os.name != "nt":
        return False
    try:
        import winreg

        keys = [
            (winreg.HKEY_LOCAL_MACHINE,
             r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients"
             r"\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
            (winreg.HKEY_CURRENT_USER,
             r"SOFTWARE\Microsoft\EdgeUpdate\Clients"
             r"\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
        ]
        for root, path in keys:
            try:
                with winreg.OpenKey(root, path) as key:
                    value, _ = winreg.QueryValueEx(key, "pv")
                    if value:
                        return True
            except OSError:
                continue
    except Exception:  # noqa: BLE001 - detection is best effort
        return False
    return False


def run_window(url: str, data_directory: Path, server, thread) -> int:
    import wx
    import wx.html2

    os.environ.setdefault("WEBVIEW2_USER_DATA_FOLDER", str(data_directory / "webview2"))
    state = {"loaded": False, "fallback": False}

    class Frame(wx.Frame):
        def __init__(self) -> None:
            super().__init__(None, title=app_core.APP_TITLE, size=(1180, 800))
            self.SetMinSize((900, 600))
            self.panel = wx.Panel(self)
            self.sizer = wx.BoxSizer(wx.VERTICAL)
            self.panel.SetSizer(self.sizer)
            self.view = None
            self.message = wx.StaticText(
                self.panel, label="正在启动内置服务并加载界面…",
                style=wx.ALIGN_CENTRE_HORIZONTAL)
            self.sizer.Add(self.message, 1, wx.EXPAND | wx.ALL, 24)
            self.Bind(wx.EVT_CLOSE, self.on_close)
            wx.CallLater(int(WEBVIEW_TIMEOUT_SECONDS * 1000), self.check_loaded)

        def mount_webview(self) -> None:
            import wx.html2  # noqa: F811 - local import keeps headless mode light

            self.sizer.Clear(delete_windows=True)
            self.view = wx.html2.WebView.New(self.panel,
                                             backend=wx.html2.WebViewBackendEdge)
            self.view.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.on_loaded)
            self.view.Bind(wx.html2.EVT_WEBVIEW_ERROR, self.on_error)
            self.sizer.Add(self.view, 1, wx.EXPAND)
            self.panel.Layout()
            self.view.LoadURL(url)

        def on_loaded(self, event) -> None:
            state["loaded"] = True

        def on_error(self, event) -> None:
            self.use_browser(str(event.GetString() or "WebView 加载失败"))

        def use_browser(self, reason: str) -> None:
            if state["fallback"]:
                return
            state["fallback"] = True
            log_lines([f"webview fallback: {reason}"], data_directory / "logs" / "app.log")
            app_core.open_in_browser(url)
            wx.MessageBox(
                f"内嵌窗口渲染不可用（{reason}）。\n已改用系统浏览器打开：{url}\n"
                "内置服务仍在运行，关闭本窗口才会退出。",
                app_core.APP_TITLE, wx.OK | wx.ICON_WARNING, self)

        def check_loaded(self) -> None:
            if state["loaded"] or state["fallback"]:
                return
            self.use_browser("8 秒内未完成首屏加载")

        def on_close(self, event) -> None:
            stop_server(server, thread)
            event.Skip()
            self.Destroy()

    app = wx.App(False)
    frame = Frame()
    frame.Show()
    try:
        frame.mount_webview()
    except Exception as exc:  # noqa: BLE001 - any WebView failure degrades to browser
        frame.use_browser(str(exc))
    app.MainLoop()
    return 0 if not state["fallback"] else 3


def _resolve_dir(explicit: Path | None, portable_first: bool = False) -> Path | None:
    from app.config import DataDirError, resolve_data_dir

    try:
        return resolve_data_dir(explicit, portable_first=portable_first)
    except DataDirError as exc:
        tried = "\n".join(f"  · {path}" for path in exc.tried)
        log_lines(["no writable data directory"] + [str(path) for path in exc.tried])
        show_message(
            "无法创建数据目录，程序无法启动。\n\n"
            f"尝试过的位置：\n{tried}\n\n"
            "可以这样做：\n"
            "1. 在命令提示符里运行：GexingTuijian.exe --data-dir D:\\GexingTuijian\n"
            "2. 或者设置环境变量 APP_DATA_DIR 指向一个可写目录\n"
            "3. 检查是否被安全软件/权限策略拦截了该目录",
            caption=f"{app_core.APP_TITLE} · 启动失败",
        )
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="个性化推荐系统桌面版")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--no-window", action="store_true",
                        help="只启动内置服务并打印地址（用于冒烟）")
    parser.add_argument("--browser", action="store_true",
                        help="强制用系统浏览器打开")
    parser.add_argument("--portable", action="store_true",
                        help="把数据放在 exe 目录下的 data/（默认放 %LOCALAPPDATA%）")
    args = parser.parse_args(argv)
    ensure_std_streams()

    preferred = _resolve_dir(args.data_dir, args.portable)
    if preferred is None:
        return 4
    preferred.mkdir(parents=True, exist_ok=True)
    log_file = preferred / "logs" / "app.log"
    log_lines([f"start data_dir={preferred} args={argv or sys.argv[1:]}"], log_file)

    port = args.port or app_core.pick_port()
    url = f"http://127.0.0.1:{port}/"

    instance = app_core.SingleInstance()
    if not instance.acquire():
        app_core.activate_existing_window()
        say("已有实例在运行，已尝试把窗口置前。")
        return 0

    started = time.monotonic()
    server, thread, data_directory = start_server_with_fallback(port, args.data_dir,
                                                             args.portable)
    log_file = data_directory / "logs" / "app.log"
    try:
        ready = app_core.wait_for_health(app_core.health_url(port), timeout=25.0)
        if not ready:
            log_lines(["health check timed out"], log_file)
            show_message(f"内置服务启动失败：健康检查超时。\n日志：{log_file}")
            stop_server(server, thread)
            return 2
        elapsed = time.monotonic() - started
        say(f"服务已就绪：{url}（耗时 {elapsed:.1f}s）")
        log_lines([f"ready in {elapsed:.1f}s url={url}"], log_file)
        app_core.write_runtime_info(data_directory, {
            "url": url, "port": port, "data_dir": str(data_directory),
            "version": app_core.read_version(),
        })

        if args.no_window:
            return 0
        if args.browser or not webview2_available():
            app_core.open_in_browser(url)
            say("已用系统浏览器打开；按 Ctrl+C 退出。")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                return 0
        return run_window(url, data_directory, server, thread)
    finally:
        instance.release()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001 - last resort: readable dialog + log
        detail = traceback.format_exc()
        written = log_fatal(detail)
        where = "\n".join(str(path) for path in written) or "（无法写入日志文件）"
        tail = [line.strip() for line in detail.strip().splitlines() if line.strip()][-3:]
        show_message(
            "程序遇到未处理的错误。\n\n"
            f"详细信息：\n{chr(10).join(tail)}\n\n"
            f"日志：\n{where}\n\n"
            "如果是数据库/权限相关，可换一个可写目录重试：\n"
            "GexingTuijian.exe --data-dir D:\\GexingTuijian",
            caption=f"{app_core.APP_TITLE} · 启动失败",
        )
        raise SystemExit(5)
