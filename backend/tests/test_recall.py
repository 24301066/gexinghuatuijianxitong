"""Engine-level recall: collaborative vs content signal, cold start, fallback."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.config import load_rec_config
from app.rec.engine import Recommender

NOW = datetime(2026, 10, 29, 12, 0, 0)

ITEMS = [
    {"item_id": "I1", "title": "简素 保湿面膜", "category": "美妆个护", "price": 59.0,
     "tags": "补水,温和"},
    {"item_id": "I2", "title": "简素 精华液", "category": "美妆个护", "price": 129.0,
     "tags": "补水,敏感肌可用"},
    {"item_id": "I3", "title": "北纬 无线蓝牙耳机", "category": "数码配件", "price": 299.0,
     "tags": "低延迟,便携"},
    {"item_id": "I4", "title": "山野 挂耳咖啡", "category": "食品饮料", "price": 49.0,
     "tags": "进口,热卖"},
]


def _events(rows: list[tuple[str, str, str, int]]) -> list[dict]:
    return [{"user_id": user, "item_id": item, "type": type_, "rating": None,
             "event_time": NOW - timedelta(days=days)}
            for user, item, type_, days in rows]


BASE_EVENTS = [
    ("U1", "I1", "view", 5), ("U1", "I2", "cart", 4),
    ("U2", "I1", "view", 3), ("U2", "I2", "purchase", 2),
    ("U3", "I1", "view", 6), ("U3", "I3", "view", 1),
]


@pytest.fixture()
def engine() -> Recommender:
    return Recommender(load_rec_config()).fit(ITEMS, _events(BASE_EVENTS), now=NOW)


def test_collaborative_similarity_prefers_co_interacted_items(engine: Recommender):
    i1, i2, i3 = (engine.index[item] for item in ("I1", "I2", "I3"))
    assert engine.similarity[i1, i2] > engine.similarity[i1, i3]
    assert engine.similarity[i1, i2] > 0


def test_content_similarity_prefers_same_category(engine: Recommender):
    i1, i2, i3 = (engine.index[item] for item in ("I1", "I2", "I3"))
    content = engine.content @ engine.content[i1]
    assert content[i2] > content[i3]


def test_recommend_excludes_purchases_and_is_deterministic(engine: Recommender):
    first = engine.recommend("U2", size=3)
    second = engine.recommend("U2", size=3)
    assert first["items"] == second["items"]
    assert all(item["item_id"] != "I2" for item in first["items"])
    assert first["cold_start"] is False


def test_cold_start_uses_popularity(engine: Recommender):
    result = engine.recommend("ghost-user", size=3)
    assert result["cold_start"] is True
    assert result["items"]
    assert all(item["reason"] for item in result["items"])


def test_empty_catalog_degrades():
    engine = Recommender(load_rec_config()).fit([], [])
    result = engine.recommend("U1", size=5)
    assert result["degraded"] is True
    assert result["items"] == []
    assert engine.ready is False


def test_weights_change_ordering():
    events = _events(BASE_EVENTS + [("U4", "I4", "purchase", 1), ("U4", "I4", "purchase", 1)])
    hybrid = Recommender(load_rec_config()).fit(ITEMS, events, now=NOW).recommend("U1", size=3)

    popular_config = load_rec_config()
    popular_config["weights"] = {"cf": 0.0, "content": 0.0, "popular": 1.0}
    popular = Recommender(popular_config).fit(ITEMS, events, now=NOW).recommend("U1", size=3)

    assert popular["items"][0]["item_id"] == "I4"
    assert [item["item_id"] for item in popular["items"]] != \
           [item["item_id"] for item in hybrid["items"]]


def test_profile_is_empty_for_users_without_behaviour(engine: Recommender):
    profile = engine.profile("nobody")
    assert profile["categories"] == {}
    assert profile["activity_level"] == 0.0
