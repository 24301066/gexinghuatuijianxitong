"""Diversity rerank: category cap, purchase filter, monotonic scores."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.config import load_rec_config
from app.rec.engine import Recommender

NOW = datetime(2026, 10, 29, 12, 0, 0)


def _catalog(size: int, categories: list[str]) -> list[dict]:
    return [{"item_id": f"I{index:02d}", "title": f"商品 {index}",
             "category": categories[index % len(categories)], "price": 10.0 * index,
             "tags": "演示"}
            for index in range(size)]


def _events(user: str, item_ids: list[str], event_type: str = "view",
            days: int = 1) -> list[dict]:
    return [{"user_id": user, "item_id": item_id, "type": event_type, "rating": None,
             "event_time": NOW - timedelta(days=days)} for item_id in item_ids]


def test_category_ratio_is_capped():
    config = load_rec_config()
    config["diversity"]["max_category_ratio"] = 0.4
    catalog = _catalog(20, ["甲类", "乙类", "丙类", "丁类", "戊类"])
    events = _events("U1", [item["item_id"] for item in catalog[:6]])
    engine = Recommender(config).fit(catalog, events, now=NOW)

    result = engine.recommend("U1", size=10)
    counts: dict[str, int] = {}
    for item in result["items"]:
        counts[item["category"]] = counts.get(item["category"], 0) + 1
    allowed = max(1, int(0.4 * 10))
    assert counts and max(counts.values()) <= allowed


def test_purchased_items_never_returned():
    catalog = _catalog(10, ["甲类", "乙类"])
    events = _events("U1", [item["item_id"] for item in catalog[:4]]) + \
        _events("U1", ["I00", "I01"], "purchase")
    engine = Recommender(load_rec_config()).fit(catalog, events, now=NOW)
    result = engine.recommend("U1", size=10)
    returned = {item["item_id"] for item in result["items"]}
    assert not returned & {"I00", "I01"}
    assert returned


def test_scores_are_monotonic_and_ranks_sequential():
    catalog = _catalog(12, ["甲类", "乙类", "丙类"])
    events = _events("U1", [item["item_id"] for item in catalog[:5]])
    engine = Recommender(load_rec_config()).fit(catalog, events, now=NOW)
    result = engine.recommend("U1", size=8)
    scores = [item["score"] for item in result["items"]]
    assert scores == sorted(scores, reverse=True)
    assert [item["rank"] for item in result["items"]] == list(range(1, len(scores) + 1))


def test_partial_flag_and_empty_pool():
    catalog = _catalog(3, ["甲类"])
    events = _events("U1", ["I00", "I01", "I02"], "purchase")
    engine = Recommender(load_rec_config()).fit(catalog, events, now=NOW)
    result = engine.recommend("U1", size=5)
    assert result["items"] == []
    assert result["partial"] is True
    assert result["degraded"] is False
