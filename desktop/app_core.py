"""Desktop shell helpers that do not import wxPython (unit-testable)."""

from __future__ import annotations

import ctypes
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Callable
from pathlib import Path

APP_NAME = "GexingTuijian"
APP_TITLE = "个性化推荐系统 · 电商"
DEFAULT_PORT = 8765
HEALTH_PATH = "/api/v1/health"

ERROR_ALREADY_EXISTS = 183


def resource_path(*parts: str) -> Path:
    """Resolve bundled resources in both source mode and PyInstaller mode."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parents[1]
    return base.joinpath(*parts)


def data_dir(override: str | os.PathLike[str] | None = None) -> Path:
    if override:
        return Path(override).expanduser()
    env = os.environ.get("APP_DATA_DIR")
    if env:
        return Path(env).expanduser()
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def health_url(port: int, host: str = "127.0.0.1") -> str:
    return f"http://{host}:{port}{HEALTH_PATH}"


def pick_port(preferred: int = DEFAULT_PORT, host: str = "127.0.0.1") -> int:
    """Return ``preferred`` when it is free, otherwise an OS-assigned free port."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind((host, preferred))
            return preferred
    except OSError:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((host, 0))
            return int(probe.getsockname()[1])


def _probe_http(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def wait_for_health(url: str, timeout: float = 10.0, interval: float = 0.15,
                    probe: Callable[[], bool] | None = None) -> bool:
    """Poll the health endpoint until it answers or ``timeout`` seconds elapse."""
    check = probe or (lambda: _probe_http(url))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(interval)
    return False


def open_in_browser(url: str) -> bool:
    return webbrowser.open(url)


def read_version() -> str:
    try:
        import importlib.util

        spec = importlib.util.find_spec("app")
        if spec is not None:
            module = __import__("app")
            return getattr(module, "__version__", "0.0.0")
    except Exception:  # noqa: BLE001 - version is best effort
        pass
    return "0.0.0"


class SingleInstance:
    """Named mutex based single-instance guard with a file-lock fallback."""

    def __init__(self, name: str = APP_NAME) -> None:
        self.name = name
        self._handle = None
        self._file = None

    def acquire(self) -> bool:
        if os.name == "nt":
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            self._handle = kernel32.CreateMutexW(None, False, f"Global\\{self.name}")
            if not self._handle:
                return True
            return kernel32.GetLastError() != ERROR_ALREADY_EXISTS
        lock_path = data_dir() / f"{self.name}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._file = open(lock_path, "x")
            return True
        except FileExistsError:
            return False

    def release(self) -> None:
        if self._handle and os.name == "nt":
            ctypes.windll.kernel32.CloseHandle(self._handle)  # type: ignore[attr-defined]
            self._handle = None
        if self._file is not None:
            try:
                self._file.close()
                (data_dir() / f"{self.name}.lock").unlink(missing_ok=True)
            except OSError:
                pass
            self._file = None

    def __enter__(self) -> "SingleInstance":
        self.acquired = self.acquire()
        return self

    def __exit__(self, *exc_info) -> None:
        self.release()


def activate_existing_window(title: str = APP_TITLE) -> bool:
    """Best effort: bring an already running window to the front (Windows only)."""
    if os.name != "nt":
        return False
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]
        handle = user32.FindWindowW(None, title)
        if not handle:
            return False
        user32.ShowWindow(handle, 9)  # SW_RESTORE
        user32.SetForegroundWindow(handle)
        return True
    except Exception:  # noqa: BLE001 - activation is best effort
        return False


def write_runtime_info(directory: Path, payload: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "runtime.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
