"""Behaviour statistics: popularity, user profiles and item co-occurrence."""

from __future__ import annotations

from datetime import datetime

import numpy as np

TYPE_WEIGHTS = {"view": 1.0, "cart": 3.0, "purchase": 5.0, "rating": 4.0}
PURCHASE_TYPES = {"purchase"}


def decay(age_days: float, half_life_days: float) -> float:
    if half_life_days <= 0:
        return 1.0
    return 0.5 ** (max(0.0, age_days) / half_life_days)


def event_weight(event_type: str, rating: float | None) -> float:
    weight = TYPE_WEIGHTS.get(event_type, 1.0)
    if event_type == "rating" and rating:
        weight *= float(rating) / 5.0
    return weight


def popularity(item_ids: list[str], events: list[dict], now: datetime,
               half_life_days: float) -> np.ndarray:
    index = {item_id: position for position, item_id in enumerate(item_ids)}
    scores = np.zeros(len(item_ids), dtype=np.float64)
    for event in events:
        position = index.get(event["item_id"])
        if position is None:
            continue
        age = (now - event["event_time"]).total_seconds() / 86400.0
        scores[position] += event_weight(event["type"], event.get("rating")) * decay(
            age, half_life_days)
    return scores


def user_item_matrix(item_ids: list[str], events: list[dict], user_ids: list[str]) -> np.ndarray:
    """Weighted user x item interaction matrix (no time decay — used for CF)."""
    item_index = {item_id: position for position, item_id in enumerate(item_ids)}
    user_index = {user_id: position for position, user_id in enumerate(user_ids)}
    matrix = np.zeros((len(user_ids), len(item_ids)), dtype=np.float64)
    for event in events:
        row = user_index.get(event["user_id"])
        column = item_index.get(event["item_id"])
        if row is None or column is None:
            continue
        matrix[row, column] += event_weight(event["type"], event.get("rating"))
    return matrix


def item_similarity(matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity between item columns of the user-item matrix."""
    if matrix.size == 0:
        return np.zeros((matrix.shape[1], matrix.shape[1]), dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=0, keepdims=True)
    norms[norms == 0] = 1.0
    normalised = matrix / norms
    similarity = normalised.T @ normalised
    np.fill_diagonal(similarity, 0.0)
    return similarity


def user_history(events: list[dict], user_id: str, limit: int) -> list[dict]:
    """Most recent interactions first."""
    history = [event for event in events if event["user_id"] == user_id]
    history.sort(key=lambda event: event["event_time"], reverse=True)
    return history[:limit]


def purchased_items(events: list[dict], user_id: str) -> set[str]:
    return {event["item_id"] for event in events
            if event["user_id"] == user_id and event["type"] in PURCHASE_TYPES}


def profiles(item_ids: list[str], events: list[dict], catalog: dict[str, dict],
             now: datetime, half_life_days: float) -> dict[str, dict]:
    """Per-user category affinity, price band and activity level."""
    result: dict[str, dict] = {}
    for event in events:
        meta = catalog.get(event["item_id"])
        if meta is None:
            continue
        profile = result.setdefault(event["user_id"], {
            "categories": {}, "price_sum": 0.0, "price_weight": 0.0, "activity": 0,
        })
        age = (now - event["event_time"]).total_seconds() / 86400.0
        weight = event_weight(event["type"], event.get("rating")) * decay(age, half_life_days)
        profile["categories"][meta["category"]] = profile["categories"].get(
            meta["category"], 0.0) + weight
        profile["price_sum"] += meta["price"] * weight
        profile["price_weight"] += weight
        profile["activity"] += 1

    for profile in result.values():
        total = sum(profile["categories"].values()) or 1.0
        profile["categories"] = {name: round(value / total, 4)
                                 for name, value in sorted(profile["categories"].items(),
                                                           key=lambda pair: -pair[1])}
        profile["avg_price"] = round(profile["price_sum"] / profile["price_weight"], 2) \
            if profile["price_weight"] else 0.0
        profile["activity_level"] = round(min(1.0, profile["activity"] / 60.0), 3)
        del profile["price_sum"]
        del profile["price_weight"]
    return result


def normalize(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    low = float(values.min())
    high = float(values.max())
    if high - low < 1e-12:
        return np.zeros_like(values)
    return (values - low) / (high - low)
