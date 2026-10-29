"""Desktop shell helpers: port picking, readiness polling, single instance."""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DESKTOP = REPO_ROOT / "desktop"
if str(DESKTOP) not in sys.path:
    sys.path.insert(0, str(DESKTOP))

import app_core  # noqa: E402


def test_pick_port_prefers_requested_port_when_free():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        free_port = int(probe.getsockname()[1])
    assert app_core.pick_port(free_port) == free_port


def test_pick_port_falls_back_when_port_busy():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        busy_port = int(busy.getsockname()[1])
        alternative = app_core.pick_port(busy_port)
    assert alternative != busy_port
    assert 1024 < alternative < 65536


def test_wait_for_health_times_out():
    calls = {"count": 0}

    def never():
        calls["count"] += 1
        return False

    assert app_core.wait_for_health("http://127.0.0.1:1/x", timeout=0.4, interval=0.05,
                                    probe=never) is False
    assert calls["count"] >= 2


def test_wait_for_health_succeeds_after_failures():
    sequence = iter([False, False, True])

    def eventually():
        return next(sequence)

    assert app_core.wait_for_health("http://127.0.0.1:1/x", timeout=1.0, interval=0.01,
                                    probe=eventually) is True


def test_health_url_and_defaults():
    assert app_core.health_url(8765) == "http://127.0.0.1:8765/api/v1/health"
    assert app_core.DEFAULT_PORT == 8765


def test_data_dir_honours_override(tmp_path):
    assert app_core.data_dir(tmp_path) == tmp_path


def test_single_instance_second_acquire_fails():
    first = app_core.SingleInstance(name="DshTestInstanceMutex")
    second = app_core.SingleInstance(name="DshTestInstanceMutex")
    assert first.acquire() is True
    try:
        assert second.acquire() is False
    finally:
        second.release()
        first.release()


def test_resource_path_points_at_repo_in_source_mode():
    path = app_core.resource_path("backend", "config", "rec.yaml")
    assert path.is_file()
    assert path.name == "rec.yaml"


def test_read_version_returns_package_version():
    version = app_core.read_version()
    assert version.count(".") == 2


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_activate_existing_window_returns_false_for_missing_title():
    assert app_core.activate_existing_window("没有这个窗口标题-DSH-probe") is False
