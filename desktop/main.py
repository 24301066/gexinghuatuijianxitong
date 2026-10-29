"""Desktop entry point: starts the bundled API, then hosts the UI in a native window.

CLI:
    python desktop/main.py                 # normal desktop window
    python desktop/main.py --no-window     # headless: start server, print URL, exit 0
    python desktop/main.py --data-dir DIR  # override the data directory

Design notes (see openspec/changes/ecommerce-recommender-mvp/design.md, D8):
- uvicorn runs in a background thread with workers=1;
- the window uses wx.html2's Edge backend (system WebView2), no bundled browser;
- if the WebView cannot render, the same URL is opened in the system browser.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
if BACKEND.is_dir() and str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import app_core  # noqa: E402

WEBVIEW_TIMEOUT_SECONDS = 8.0


def start_server(data_directory: Path, port: int) -> tuple[object, threading.Thread]:
    import uvicorn

    from app import create_app
    from app.config import load_settings

    settings = load_settings(data_directory)
    application = create_app(settings)
    config = uvicorn.Config(application, host="127.0.0.1", port=port, log_level="info",
                            workers=1, access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True, name="uvicorn")
    thread.start()
    return server, thread


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="个性化推荐系统桌面版")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--no-window", action="store_true",
                        help="只启动内置服务并打印地址（用于冒烟）")
    parser.add_argument("--browser", action="store_true",
                        help="强制用系统浏览器打开")
    args = parser.parse_args(argv)

    data_directory = app_core.data_dir(args.data_dir)
    data_directory.mkdir(parents=True, exist_ok=True)
    port = args.port or app_core.pick_port()
    url = f"http://127.0.0.1:{port}/"

    instance = app_core.SingleInstance()
    if not instance.acquire():
        app_core.activate_existing_window()
        print("已有实例在运行，已尝试把窗口置前。")
        return 0

    started = time.monotonic()
    server, thread = start_server(data_directory, port)
    try:
        ready = app_core.wait_for_health(app_core.health_url(port), timeout=25.0)
        if not ready:
            print("内置服务启动失败：健康检查超时", file=sys.stderr)
            stop_server(server, thread)
            return 2
        print(f"服务已就绪：{url}（耗时 {time.monotonic() - started:.1f}s）")
        app_core.write_runtime_info(data_directory, {
            "url": url, "port": port, "data_dir": str(data_directory),
            "version": app_core.read_version(),
        })

        if args.no_window:
            return 0
        if args.browser or not webview2_available():
            app_core.open_in_browser(url)
            print("已用系统浏览器打开；按 Ctrl+C 退出。")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                return 0
        return run_window(url, data_directory, server, thread)
    finally:
        instance.release()


if __name__ == "__main__":
    raise SystemExit(main())
