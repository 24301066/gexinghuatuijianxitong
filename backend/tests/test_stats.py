"""Statistics: popularity decay, profiles, normalisation."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from app.rec import stats

NOW = datetime(2026, 10, 29, 12, 0, 0)

CATALOG = {
    "I1": {"item_id": "I1", "category": "美妆个护", "price": 100.0},
    "I2": {"item_id": "I2", "category": "数码配件", "price": 300.0},
}


def test_popularity_decays_with_age():
    item_ids = ["I1", "I2"]
    events = [
        {"user_id": "U1", "item_id": "I1", "type": "purchase", "rating": None,
         "event_time": NOW - timedelta(days=1)},
        {"user_id": "U2", "item_id": "I2", "type": "purchase", "rating": None,
         "event_time": NOW - timedelta(days=30)},
    ]
    scores = stats.popularity(item_ids, events, NOW, half_life_days=14.0)
    assert scores[0] > scores[1] > 0


def test_event_weights_rank_purchase_above_view():
    assert stats.event_weight("purchase", None) > stats.event_weight("view", None)
    assert stats.event_weight("rating", 5.0) > stats.event_weight("rating", 1.0)


def test_profiles_normalise_category_affinity():
    events = [
        {"user_id": "U1", "item_id": "I1", "type": "purchase", "rating": None,
         "event_time": NOW - timedelta(days=1)},
        {"user_id": "U1", "item_id": "I2", "type": "view", "rating": None,
         "event_time": NOW - timedelta(days=2)},
    ]
    profiles = stats.profiles(["I1", "I2"], events, CATALOG, NOW, 14.0)
    profile = profiles["U1"]
    assert abs(sum(profile["categories"].values()) - 1.0) < 1e-6
    assert profile["categories"]["美妆个护"] > profile["categories"]["数码配件"]
    assert profile["avg_price"] > 100
    assert 0 < profile["activity_level"] <= 1


def test_normalize_handles_constant_vectors():
    assert list(stats.normalize(np.array([3.0, 3.0]))) == [0.0, 0.0]
    normalised = stats.normalize(np.array([0.0, 5.0, 10.0]))
    assert normalised[0] == 0.0 and normalised[-1] == 1.0


def test_user_history_is_most_recent_first():
    events = [
        {"user_id": "U1", "item_id": "I1", "type": "view", "rating": None,
         "event_time": NOW - timedelta(days=5)},
        {"user_id": "U1", "item_id": "I2", "type": "view", "rating": None,
         "event_time": NOW - timedelta(days=1)},
        {"user_id": "U2", "item_id": "I1", "type": "view", "rating": None,
         "event_time": NOW - timedelta(days=2)},
    ]
    history = stats.user_history(events, "U1", limit=5)
    assert [event["item_id"] for event in history] == ["I2", "I1"]
