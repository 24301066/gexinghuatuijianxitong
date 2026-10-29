"""Application settings and recommendation config loading."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_REC_CONFIG: dict = {
    "seed": 20261029,
    "weights": {"cf": 0.5, "content": 0.3, "popular": 0.2},
    "diversity": {"lambda": 0.7, "max_category_ratio": 0.4},
    "recall": {"max_history": 20, "popular_half_life_days": 14.0,
               "max_results": 50, "viewed_penalty": 0.9},
    "eval": {"cutoffs": [5, 10], "split_ratio": 0.8,
             "strategies": ["popular", "hybrid"]},
    "data": {"demo": {"users": 200, "items": 400, "events": 12000}},
}


def resource_path(*parts: str) -> Path:
    """Resolve a bundled resource in both source and PyInstaller (frozen) mode.

    In source mode paths are relative to ``backend/`` (where config/rec.yaml lives);
    frozen builds put everything under ``sys._MEIPASS``.
    """
    if getattr(os.sys, "frozen", False) and hasattr(os.sys, "_MEIPASS"):
        base = Path(os.sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parents[1]  # backend/
    return base.joinpath(*parts)


def web_dist_path() -> Path:
    """Built frontend directory: repo ``web/dist`` in source mode, bundled otherwise."""
    if getattr(os.sys, "frozen", False) and hasattr(os.sys, "_MEIPASS"):
        return Path(os.sys._MEIPASS) / "web" / "dist"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2] / "web" / "dist"


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


@dataclass
class Settings:
    data_dir: Path
    rec_config_path: Path
    env: str = "dev"
    secret: str = ""
    db_url: str = ""
    rec: dict = field(default_factory=dict)
    web_dist: Path = field(default_factory=web_dist_path)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def model_version(self) -> str:
        payload = json.dumps(self.rec, sort_keys=True, ensure_ascii=False)
        return "rec-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:10]


def default_data_dir() -> Path:
    override = os.environ.get("APP_DATA_DIR")
    if override:
        return Path(override).expanduser()
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "GexingTuijian"
    return Path.home() / ".gextuijian"


def load_rec_config(path: Path | None = None) -> dict:
    config_path = path or Path(os.environ.get("APP_REC_CONFIG")
                               or resource_path("config", "rec.yaml"))
    raw: dict = {}
    if Path(config_path).exists():
        raw = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
    merged = _merge(DEFAULT_REC_CONFIG, raw)

    weights = merged.get("weights") or {}
    total = sum(float(v) for v in weights.values())
    if total <= 0:
        raise ValueError("rec.yaml: weights must sum to a positive number")
    ratio = float(merged["diversity"]["max_category_ratio"])
    if not 0 < ratio <= 1:
        raise ValueError("rec.yaml: diversity.max_category_ratio must be in (0, 1]")
    lam = float(merged["diversity"]["lambda"])
    if not 0 <= lam <= 1:
        raise ValueError("rec.yaml: diversity.lambda must be in [0, 1]")
    return merged


def _secret_for(data_dir: Path) -> str:
    env_secret = os.environ.get("APP_SECRET")
    if env_secret:
        return env_secret
    data_dir.mkdir(parents=True, exist_ok=True)
    key_file = data_dir / "secret.key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    secret = secrets.token_urlsafe(48)
    key_file.write_text(secret, encoding="utf-8")
    return secret


def load_settings(data_dir: Path | None = None, rec_config_path: Path | None = None) -> Settings:
    data = Path(data_dir) if data_dir else default_data_dir()
    data.mkdir(parents=True, exist_ok=True)
    rec = load_rec_config(rec_config_path)
    secret = _secret_for(data)
    return Settings(
        data_dir=data,
        rec_config_path=Path(rec_config_path) if rec_config_path else resource_path("config", "rec.yaml"),
        env=os.environ.get("APP_ENV", "dev"),
        secret=secret,
        db_url=f"sqlite:///{(data / 'app.db').as_posix()}",
        rec=rec,
    )
