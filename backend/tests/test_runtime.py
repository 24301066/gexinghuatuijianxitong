"""Runtime helpers: SQLite retry behaviour."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import OperationalError

from app.runtime import retry_sqlite


def _locked() -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception("database is locked"))


def test_retry_sqlite_retries_transient_failures(monkeypatch):
    monkeypatch.setattr("app.runtime.time.sleep", lambda _seconds: None)
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise _locked()
        return "ok"

    assert retry_sqlite(flaky, attempts=4) == "ok"
    assert calls["count"] == 3


def test_retry_sqlite_gives_up_after_attempts(monkeypatch):
    monkeypatch.setattr("app.runtime.time.sleep", lambda _seconds: None)
    calls = {"count": 0}

    def always_locked():
        calls["count"] += 1
        raise _locked()

    with pytest.raises(OperationalError):
        retry_sqlite(always_locked, attempts=3)
    assert calls["count"] == 3


def test_retry_sqlite_does_not_swallow_other_errors(monkeypatch):
    monkeypatch.setattr("app.runtime.time.sleep", lambda _seconds: None)

    def boom():
        raise ValueError("not a db problem")

    with pytest.raises(ValueError):
        retry_sqlite(boom)


def test_corrupted_database_is_quarantined(tmp_path):
    from app.config import load_settings
    from app.runtime import Runtime

    data = tmp_path / "data"
    data.mkdir()
    (data / "app.db").write_bytes(b"this is definitely not sqlite")

    settings = load_settings(data)
    runtime = Runtime(settings)

    assert runtime.quarantined is not None
    assert runtime.quarantined.name.startswith("app.db.broken-")
    assert runtime.quarantined.read_bytes().startswith(b"this is definitely not sqlite")
    assert runtime.counts()["items"] == 0  # a fresh schema was created

