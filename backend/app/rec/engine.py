"""Recommendation engine: multi-source recall, weighted fusion, diversity rerank."""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timezone

import numpy as np

from . import stats, text


class Recommender:
    """In-memory recommender built from the catalog plus behaviour events.

    The engine is intentionally free of database imports so it can be unit tested
    with plain dicts and reused by the offline evaluation script.
    """

    def __init__(self, config: dict, model_version: str = "rec-dev") -> None:
        self.config = config
        self.model_version = model_version
        self.ready = False
        self.degraded = False
        self.item_ids: list[str] = []
        self.meta: dict[str, dict] = {}
        self.index: dict[str, int] = {}
        self.content = np.zeros((0, 0), dtype=np.float64)
        self.similarity = np.zeros((0, 0), dtype=np.float64)
        self.popularity = np.zeros(0, dtype=np.float64)
        self.bought: dict[str, set[str]] = {}
        self.seen: dict[str, set[str]] = {}
        self.history: dict[str, list[dict]] = {}
        self.profiles: dict[str, dict] = {}
        self.fitted_at: datetime | None = None

    # ------------------------------------------------------------------ fit

    def fit(self, items: list[dict], events: list[dict], now: datetime | None = None) -> "Recommender":
        cfg = self.config
        half_life = float(cfg["recall"]["popular_half_life_days"])
        max_history = int(cfg["recall"]["max_history"])
        now = now or datetime.now(timezone.utc).replace(tzinfo=None)

        self.item_ids = sorted({item["item_id"] for item in items})
        self.meta = {item["item_id"]: item for item in items}
        self.index = {item_id: position for position, item_id in enumerate(self.item_ids)}

        documents = [text.document_of(item["title"], item["category"], item.get("tags", ""))
                     for item in items if item["item_id"] in self.index]
        ordered_documents = [
            text.document_of(self.meta[item_id]["title"], self.meta[item_id]["category"],
                             self.meta[item_id].get("tags", ""))
            for item_id in self.item_ids
        ]
        self.content = text.build_matrix(ordered_documents or documents)

        user_ids = sorted({event["user_id"] for event in events})
        matrix = stats.user_item_matrix(self.item_ids, events, user_ids)
        self.similarity = stats.item_similarity(matrix)
        self.popularity = stats.popularity(self.item_ids, events, now, half_life)
        self.profiles = stats.profiles(self.item_ids, events, self.meta, now, half_life)

        self.bought = {}
        self.seen = {}
        for event in events:
            target = self.bought if event["type"] in stats.PURCHASE_TYPES else self.seen
            target.setdefault(event["user_id"], set()).add(event["item_id"])

        self.history = {}
        for event in events:
            self.history.setdefault(event["user_id"], []).append(event)
        for user, history in self.history.items():
            history.sort(key=lambda event: event["event_time"], reverse=True)
            del history[max_history:]

        self.ready = len(self.item_ids) > 0
        self.degraded = not self.ready
        self.fitted_at = now
        return self

    # --------------------------------------------------------------- helpers

    def _weights(self) -> dict[str, float]:
        raw = self.config["weights"]
        total = sum(float(value) for value in raw.values()) or 1.0
        return {name: float(value) / total for name, value in raw.items()}

    def _anchor_weights(self, history: list[dict]) -> tuple[list[int], np.ndarray]:
        positions: list[int] = []
        weights: list[float] = []
        for rank, event in enumerate(history):
            position = self.index.get(event["item_id"])
            if position is None:
                continue
            positions.append(position)
            weights.append(stats.event_weight(event["type"], event.get("rating"))
                           * (0.85 ** rank))
        if not positions:
            return [], np.zeros(0, dtype=np.float64)
        return positions, np.asarray(weights, dtype=np.float64)

    def _reason(self, position: int, scores: dict[str, np.ndarray],
                anchors: list[int], anchor_weights: np.ndarray) -> tuple[str, str]:
        item = self.meta[self.item_ids[position]]
        if not anchors:
            return "近期热门，先随便逛逛", "popular"
        contributions = {name: float(values[position]) for name, values in scores.items()}
        source = max(contributions, key=lambda name: contributions[name])
        if source == "cf":
            best = int(np.argmax(self.similarity[anchors, position] * anchor_weights))
            anchor_id = self.item_ids[anchors[best]]
            return f"看过「{self.meta[anchor_id]['title']}」的人也常看", source
        if source == "content":
            profile = self.profiles.get("", {})
            category = item["category"]
            return f"与你偏好的「{category}」类目相近", source
        return f"「{item['category']}」近期热度上升", source

    def _rerank(self, blended: np.ndarray, mask: np.ndarray, limit: int, allowed: int,
                lam: float) -> list[tuple[int, float]]:
        candidates = [int(position) for position in
                      np.lexsort((np.asarray(self.item_ids), -blended)) if mask[position]]
        candidates = [position for position in candidates if blended[position] > -np.inf]
        if not candidates:
            return []

        relations = stats.normalize(blended)
        selected: list[tuple[int, float]] = []
        chosen_positions: list[int] = []
        counts: Counter[str] = Counter()
        pool = list(candidates)

        while pool and len(selected) < limit:
            best_candidate = None
            best_score = -float("inf")
            for position in pool:
                similarity = 0.0
                if chosen_positions:
                    similarity = float(np.max(self.content[chosen_positions]
                                              @ self.content[position]))
                relevance = float(relations[position])
                score = lam * relevance - (1.0 - lam) * similarity
                category = self.meta[self.item_ids[position]]["category"]
                if counts[category] >= allowed:
                    score -= 1.0
                if score > best_score:
                    best_score = score
                    best_candidate = position
            if best_candidate is None:
                break
            pool.remove(best_candidate)
            chosen_positions.append(best_candidate)
            counts[self.meta[self.item_ids[best_candidate]]["category"]] += 1
            # The greedy score is non-increasing by construction: diversity penalties only
            # grow while the pool shrinks, so the reported score stays monotonic.
            selected.append((best_candidate, float(best_score)))
        return selected

    # ----------------------------------------------------------- public API

    def recommend(self, user_id: str, size: int = 10, page: int = 1) -> dict:
        size = max(1, min(int(size), 50))
        page = max(1, int(page))
        if not self.ready:
            return {"items": [], "cold_start": True, "partial": True, "degraded": True,
                    "model_version": self.model_version, "total_candidates": 0}

        weights = self._weights()
        history = self.history.get(user_id, [])
        anchors, anchor_weights = self._anchor_weights(history)
        bought = self.bought.get(user_id, set())
        seen = self.seen.get(user_id, set())

        cf_scores = np.zeros(len(self.item_ids), dtype=np.float64)
        content_scores = np.zeros(len(self.item_ids), dtype=np.float64)
        if anchors:
            weights_sum = float(anchor_weights.sum()) or 1.0
            for position, weight in zip(anchors, anchor_weights):
                cf_scores += self.similarity[position] * weight
            profile_vector = (self.content[anchors] * anchor_weights[:, None]).sum(axis=0)
            content_scores = text.cosine(self.content, profile_vector)
            cf_scores /= weights_sum
            del weights_sum

        raw = {
            "cf": stats.normalize(cf_scores),
            "content": stats.normalize(content_scores),
            "popular": stats.normalize(self.popularity),
        }
        blended = (weights["cf"] * raw["cf"] + weights["content"] * raw["content"]
                   + weights["popular"] * raw["popular"])

        mask = np.ones(len(self.item_ids), dtype=bool)
        penalty = float(self.config["recall"].get("viewed_penalty", 0.9))
        for position, item_id in enumerate(self.item_ids):
            if item_id in bought:
                mask[position] = False
            elif item_id in seen:
                blended[position] *= penalty

        cold_start = not anchors
        if cold_start:
            blended = stats.normalize(self.popularity).copy()

        lam = float(self.config["diversity"]["lambda"])
        ratio = float(self.config["diversity"]["max_category_ratio"])
        # Rerank a fixed-size window so that paging stays stable: page 2 must not
        # recompute a different ordering than page 1.
        window = max(1, min(int(self.config["recall"].get("max_results", 50)),
                            int(mask.sum())))
        allowed = max(1, int(math.floor(ratio * size)))
        ordered = self._rerank(blended, mask, window, allowed, lam)

        start = (page - 1) * size
        window = ordered[start:start + size]
        items = []
        for offset, (position, final_score) in enumerate(window):
            item_id = self.item_ids[position]
            reason, source = self._reason(position, raw, anchors, anchor_weights)
            items.append({
                "item_id": item_id,
                "title": self.meta[item_id]["title"],
                "category": self.meta[item_id]["category"],
                "price": float(self.meta[item_id]["price"]),
                "tags": self.meta[item_id].get("tags", ""),
                "score": round(final_score, 4),
                "rank": start + offset + 1,
                "reason": reason,
                "sources": {name: round(float(values[position]), 4)
                            for name, values in raw.items()},
            })
        partial = len(ordered) < page * size
        return {"items": items, "cold_start": cold_start, "partial": partial,
                "degraded": False, "model_version": self.model_version,
                "total_candidates": int(mask.sum())}

    def similar(self, item_id: str, size: int = 8) -> dict:
        size = max(1, min(int(size), 50))
        position = self.index.get(item_id)
        if position is None or not self.ready:
            return {"items": [], "degraded": True, "model_version": self.model_version}

        content = self.content @ self.content[position]
        collaborative = self.similarity[position]
        blended = 0.6 * stats.normalize(content) + 0.4 * stats.normalize(collaborative)
        blended[position] = -np.inf
        ordered = [int(candidate) for candidate in np.lexsort(
            (np.asarray(self.item_ids), -blended))]
        ordered = [candidate for candidate in ordered if np.isfinite(blended[candidate])][:size]

        anchor = self.meta[item_id]["title"]
        items = []
        for rank, candidate in enumerate(ordered):
            other = self.item_ids[candidate]
            reason = f"与「{anchor}」相似" if blended[candidate] > 0 else "同类目商品"
            items.append({
                "item_id": other,
                "title": self.meta[other]["title"],
                "category": self.meta[other]["category"],
                "price": float(self.meta[other]["price"]),
                "tags": self.meta[other].get("tags", ""),
                "score": round(float(blended[candidate]), 4),
                "rank": rank + 1,
                "reason": reason,
                "sources": {"content": round(float(content[candidate]), 4),
                            "cf": round(float(collaborative[candidate]), 4)},
            })
        return {"items": items, "degraded": False, "model_version": self.model_version}

    def profile(self, user_id: str) -> dict:
        profile = self.profiles.get(user_id)
        if not profile:
            return {"categories": {}, "avg_price": 0.0, "activity_level": 0.0,
                    "history_size": 0}
        result = dict(profile)
        result["history_size"] = len(self.history.get(user_id, []))
        return result
