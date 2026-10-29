"""Offline evaluation: split determinism and metric correctness."""

from __future__ import annotations

from datetime import datetime, timedelta

from app import create_app

from eval import metrics
from eval.run_eval import run, split_events

from .conftest import make_settings


def _synthetic_events(count: int = 100) -> list[dict]:
    base = datetime(2026, 10, 1, 0, 0, 0)
    return [{"user_id": f"U{index % 7}", "item_id": f"I{index % 20:02d}", "type": "view",
             "rating": None, "event_time": base + timedelta(hours=index)}
            for index in range(count)]


def test_split_never_leaks_future_events():
    events = _synthetic_events()
    train, test, cutoff = split_events(events, ratio=0.8)
    assert len(train) == 80
    assert len(test) == 20
    assert max(event["event_time"] for event in train) <= cutoff
    assert min(event["event_time"] for event in test) >= cutoff


def test_metric_hand_computed_values():
    recommended = ["a", "b", "c"]
    relevant = {"a", "c"}
    assert metrics.recall_at_k(recommended, relevant, 2) == 0.5
    assert metrics.recall_at_k(recommended, relevant, 3) == 1.0
    assert metrics.recall_at_k(recommended, set(), 3) == 0.0

    dcg = 1.0 + 1.0 / 2.0  # hits at rank 1 and rank 3 -> log2(2), log2(4)
    idcg = 1.0 + 1.0 / 1.5849625007211562  # ideal: hits at rank 1 and 2 -> log2(2), log2(3)
    assert abs(metrics.ndcg_at_k(recommended, relevant, 3) - dcg / idcg) < 1e-9


def test_coverage_and_novelty():
    assert metrics.coverage([["a", "b"], ["b", "c"]], total_items=4) == 0.75
    value = metrics.novelty([["a", "b"]], {"a": 1, "b": 9}, total_events=10)
    assert value > 0


def test_run_reports_are_reproducible(tmp_path):
    settings = make_settings(tmp_path / "data")
    create_app(settings)  # seeds the demo dataset
    out = tmp_path / "out"

    first = run(settings.data_dir, out, settings.rec_config_path)
    second = run(settings.data_dir, out, settings.rec_config_path)

    assert first["strategies"] == second["strategies"]
    assert first["split"] == second["split"]
    assert "popular" in first["strategies"]
    assert "hybrid" in first["strategies"]
    assert (out / "report.json").is_file()
    assert "Recall@" in (out / "report.md").read_text(encoding="utf-8")
