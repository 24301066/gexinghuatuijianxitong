"""Config loading: defaults merge, validation, model version stability."""

from __future__ import annotations

import pytest

from app.config import load_rec_config, load_settings


def test_defaults_are_merged(tmp_path):
    config_file = tmp_path / "rec.yaml"
    config_file.write_text("weights:\n  cf: 1\n", encoding="utf-8")
    config = load_rec_config(config_file)
    assert config["weights"]["cf"] == 1
    assert config["diversity"]["max_category_ratio"] == 0.4
    assert config["eval"]["cutoffs"] == [5, 10]
    assert config["recall"]["max_results"] == 50


def test_zero_weights_are_rejected(tmp_path):
    config_file = tmp_path / "rec.yaml"
    config_file.write_text("weights:\n  cf: 0\n  content: 0\n  popular: 0\n  keyword: 0\n  dwell: 0\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_rec_config(config_file)


def test_bad_diversity_ratio_is_rejected(tmp_path):
    config_file = tmp_path / "rec.yaml"
    config_file.write_text("diversity:\n  max_category_ratio: 1.5\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_rec_config(config_file)


def test_model_version_tracks_config(tmp_path):
    settings_a = load_settings(tmp_path / "a")
    settings_b = load_settings(tmp_path / "b")
    assert settings_a.model_version() == settings_b.model_version()

    settings_b.rec["weights"]["cf"] = 0.9
    settings_b.rec["weights"]["content"] = 0.05
    assert settings_a.model_version() != settings_b.model_version()


def test_secret_is_persisted_per_data_dir(tmp_path):
    first = load_settings(tmp_path / "data")
    second = load_settings(tmp_path / "data")
    assert first.secret == second.secret
    assert (tmp_path / "data" / "secret.key").is_file()


def test_is_writable_checks_creation(tmp_path):
    from app.config import is_writable

    assert is_writable(tmp_path / "new-dir") is True
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file", encoding="utf-8")
    assert is_writable(blocker) is False


def test_resolve_data_dir_skips_unwritable_candidates(tmp_path):
    from app.config import resolve_data_dir

    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    good = tmp_path / "good"
    assert resolve_data_dir(candidates=[blocker, good]) == good


def test_resolve_data_dir_reports_every_attempt(tmp_path):
    from app.config import DataDirError, resolve_data_dir

    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(DataDirError) as excinfo:
        resolve_data_dir(candidates=[blocker, blocker / "nested"])
    assert len(excinfo.value.tried) == 2
    assert "可写" in str(excinfo.value)


def test_existing_legacy_dir_wins_over_portable(monkeypatch, tmp_path):
    from app.config import resolve_data_dir

    legacy = tmp_path / "roaming" / "GexingTuijian"
    legacy.mkdir(parents=True)
    (legacy / "app.db").write_text("db", encoding="utf-8")
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.delenv("APP_DATA_DIR", raising=False)
    assert resolve_data_dir() == legacy
