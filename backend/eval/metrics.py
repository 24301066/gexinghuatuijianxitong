"""Offline ranking metrics (no external deps)."""

from __future__ import annotations

import math
from collections.abc import Iterable


def recall_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    hits = len(set(recommended[:k]) & relevant)
    return hits / len(relevant)


def ndcg_at_k(recommended: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    dcg = 0.0
    for position, item_id in enumerate(recommended[:k]):
        if item_id in relevant:
            dcg += 1.0 / math.log2(position + 2)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(position + 2) for position in range(ideal_hits))
    return dcg / idcg if idcg else 0.0


def coverage(recommendations: Iterable[list[str]], total_items: int) -> float:
    if not total_items:
        return 0.0
    seen: set[str] = set()
    for items in recommendations:
        seen.update(items)
    return len(seen) / total_items


def novelty(recommendations: Iterable[list[str]], item_counts: dict[str, int],
            total_events: int) -> float:
    values: list[float] = []
    if not total_events:
        return 0.0
    for items in recommendations:
        for item_id in items:
            frequency = (item_counts.get(item_id, 0) or 1) / total_events
            values.append(-math.log2(frequency))
    return sum(values) / len(values) if values else 0.0
