"""UGC content, media covers, discovery feed and the two new recommendation signals."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta

import pytest

from app.config import load_rec_config
from app.rec.engine import Recommender

from .conftest import REC_CONFIG_PATH

NOW = datetime(2026, 10, 30, 12, 0, 0)


def _config():
    rec = copy.deepcopy(load_rec_config(REC_CONFIG_PATH))
    rec["data"]["demo"] = {"users": 12, "items": 30, "events": 240, "posts": 24}
    return rec


# --------------------------------------------------------------- posts + feed


def test_posts_list_and_detail(client: "object") -> None:
    page = client.get("/api/v1/posts?page=1&size=5")
    assert page.status_code == 200, page.text
    body = page.json()
    assert body["total"] >= 24
    assert len(body["posts"]) == 5
    post = body["posts"][0]
    for field in ("post_id", "title", "body", "author_name", "media_type", "likes",
                  "cover_url", "product", "created_at"):
        assert field in post
    assert post["cover_url"] == f"/api/v1/media/post/{post['post_id']}"
    assert post["product"]["cover_url"].startswith("/api/v1/media/product/")

    detail = client.get(f"/api/v1/posts/{post['post_id']}")
    assert detail.status_code == 200
    assert detail.json()["post_id"] == post["post_id"]

    missing = client.get("/api/v1/posts/P9999")
    assert missing.status_code == 404


def test_posts_filtered_by_product(client: "object") -> None:
    post = client.get("/api/v1/posts?size=1").json()["posts"][0]
    product_id = post["product"]["item_id"]
    body = client.get(f"/api/v1/posts?product_id={product_id}&size=20").json()
    assert body["posts"]
    assert all(row["product"]["item_id"] == product_id for row in body["posts"])


def test_feed_has_ugc_and_recommendations(client: "object", auth_headers: dict) -> None:
    response = client.get("/api/v1/feed?size=6", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["hero"] is not None
    assert body["posts"]
    assert body["items"]
    assert all(item["cover_url"].startswith("/api/v1/media/product/") for item in body["items"])


# ---------------------------------------------------------------------- media


def test_cover_svg_is_deterministic(client: "object") -> None:
    item = client.get("/api/v1/items?size=1").json()["items"][0]
    url = item["cover_url"]
    first = client.get(url)
    second = client.get(url)
    assert first.status_code == 200
    assert first.headers["content-type"].startswith("image/svg+xml")
    assert first.content == second.content
    assert b"<svg" in first.content


def test_media_prefers_local_image(client: "object", settings) -> None:
    item = client.get("/api/v1/items?size=1").json()["items"][0]
    folder = settings.data_dir / "media" / "products"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{item['item_id']}.jpg").write_bytes(b"\xff\xd8\xff\xe0fake-jpeg")
    response = client.get(item["cover_url"])
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"


def test_post_video_is_404_without_file(client: "object") -> None:
    post = client.get("/api/v1/posts?size=1").json()["posts"][0]
    response = client.get(f"/api/v1/media/post/{post['post_id']}/video")
    assert response.status_code == 404
    assert post["has_video"] is False


def test_search_returns_items_posts_and_recommendations(client: "object",
                                                        auth_headers: dict) -> None:
    item = client.get("/api/v1/items?size=3").json()["items"][0]
    query = item["title"][:2]
    response = client.get(f"/api/v1/search?q={query}", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["query"] == query
    assert body["items"]
    assert all("cover_url" in row for row in body["items"])
    assert isinstance(body["posts"], list)
    assert isinstance(body["recommended"], list)


# ----------------------------------------------------------- events + insights


def test_search_event_is_stored_and_surfaced(client: "object", auth_headers: dict) -> None:
    created = client.post("/api/v1/events", json={"type": "search", "keyword": "咖啡"},
                          headers=auth_headers)
    assert created.status_code == 201, created.text
    assert created.json()["type"] == "search"

    duplicate = client.post("/api/v1/events", json={"type": "search", "keyword": "咖啡"},
                            headers=auth_headers)
    assert duplicate.status_code == 201
    assert duplicate.json()["duplicate"] is True

    missing_keyword = client.post("/api/v1/events", json={"type": "search"},
                                  headers=auth_headers)
    assert missing_keyword.status_code == 422

    insights = client.get("/api/v1/me/insights", headers=auth_headers).json()
    assert any(row["keyword"] == "咖啡" for row in insights["recent_searches"])


def test_dwell_event_is_stored_and_surfaced(client: "object", auth_headers: dict) -> None:
    post = client.get("/api/v1/posts?size=1").json()["posts"][0]
    created = client.post("/api/v1/events",
                          json={"type": "post_dwell", "post_id": post["post_id"],
                                "seconds": 12.5},
                          headers=auth_headers)
    assert created.status_code == 201, created.text
    assert created.json()["type"] == "post_dwell"

    too_short = client.post("/api/v1/events",
                            json={"type": "post_dwell", "post_id": post["post_id"],
                                  "seconds": 0},
                            headers=auth_headers)
    assert too_short.status_code == 201
    assert too_short.json()["event_id"] > 0

    unknown = client.post("/api/v1/events",
                          json={"type": "post_dwell", "post_id": "P9999", "seconds": 5},
                          headers=auth_headers)
    assert unknown.status_code == 404

    insights = client.get("/api/v1/me/insights", headers=auth_headers).json()
    assert any(row["post_id"] == post["post_id"] for row in insights["recent_dwells"])


def test_event_without_item_for_classic_types_is_rejected(client: "object",
                                                          auth_headers: dict) -> None:
    response = client.post("/api/v1/events", json={"type": "view"}, headers=auth_headers)
    assert response.status_code == 422


# ------------------------------------------------------------- engine signals


def _engine_with_signals():
    items = [
        {"item_id": "I1", "title": "云南小粒咖啡豆 500g", "category": "食品饮料",
         "price": 59.0, "tags": "咖啡,烘焙"},
        {"item_id": "I2", "title": "冷萃咖啡液 一盒十袋", "category": "食品饮料",
         "price": 39.0, "tags": "咖啡,冷萃"},
        {"item_id": "I3", "title": "北欧陶瓷砂锅 2.5L", "category": "家居日用",
         "price": 109.0, "tags": "砂锅,厨房"},
        {"item_id": "I4", "title": "静音机械键盘 87 键", "category": "数码配件",
         "price": 399.0, "tags": "键盘,办公"},
    ]
    events = [
        {"user_id": "U1", "item_id": "I3", "type": "view", "rating": None,
         "event_time": NOW - timedelta(hours=2)},
        {"user_id": "U2", "item_id": "I1", "type": "view", "rating": None,
         "event_time": NOW - timedelta(hours=3)},
    ]
    posts = [
        {"post_id": "P1", "title": "咖啡豆开箱", "author_id": "U2", "media_type": "image",
         "video_seconds": 0, "product_id": "I2", "likes": 10, "tags": "咖啡",
         "body": "", "created_at": NOW - timedelta(days=1)},
    ]
    searches = [{"user_id": "U1", "keyword": "咖啡", "created_at": NOW - timedelta(hours=1)}]
    dwells = [{"user_id": "U1", "post_id": "P1", "seconds": 30.0,
               "created_at": NOW - timedelta(minutes=30)}]
    engine = Recommender(_config()).fit(items, events, now=NOW, posts=posts,
                                        dwells=dwells, searches=searches)
    return engine


def test_keyword_signal_prefers_matching_items() -> None:
    engine = _engine_with_signals()
    scores, term = engine._keyword_scores("U1")
    assert term == "咖啡"
    positions = {item_id: engine.index[item_id] for item_id in ("I1", "I2", "I3")}
    assert scores[positions["I1"]] > scores[positions["I3"]]
    assert scores[positions["I2"]] > scores[positions["I3"]]


def test_dwell_signal_prefers_post_product() -> None:
    engine = _engine_with_signals()
    scores, title = engine._dwell_scores("U1")
    assert title == "咖啡豆开箱"
    assert scores[engine.index["I2"]] > 0
    assert scores[engine.index["I3"]] == pytest.approx(0.0)


def test_recommendation_mentions_new_signals() -> None:
    engine = _engine_with_signals()
    result = engine.recommend("U1", size=3)
    reasons = " ".join(row["reason"] for row in result["items"])
    assert ("咖啡" in reasons) or ("安利" in reasons)
    assert set(result["items"][0]["sources"]) == {"cf", "content", "popular",
                                                  "keyword", "dwell"}
