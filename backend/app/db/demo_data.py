"""Deterministic demo dataset (explicitly synthetic — see docs/数据说明.md)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

import numpy as np

CATALOG: dict[str, dict] = {
    "美妆个护": {
        "bases": ["保湿面膜", "氨基酸洁面乳", "烟酰胺精华", "清透防晒霜", "丝绒口红",
                  "温和卸妆水", "滋养护手霜", "控油洗发水", "香氛沐浴露", "紧致眼霜"],
        "brands": ["简素", "花间", "青柚", "白露", "叙白"],
        "tags": ["温和", "敏感肌可用", "补水", "国货", "礼盒"],
        "price": (29, 399),
    },
    "数码配件": {
        "bases": ["无线蓝牙耳机", "87 键机械键盘", "超大鼠标垫", "20000mAh 充电宝",
                  "编织快充数据线", "磨砂手机壳", "便携蓝牙音箱", "显示器支架",
                  "高清摄像头", "移动固态硬盘"],
        "brands": ["北纬", "拾光", "极昼", "参数", "原点"],
        "tags": ["便携", "快充", "低延迟", "大容量", "新品"],
        "price": (39, 1299),
    },
    "食品饮料": {
        "bases": ["每日坚果礼盒", "挂耳咖啡", "原味燕麦片", "螺蛳粉", "手撕牛肉干",
                  "百花蜂蜜", "明前绿茶", "可可巧克力", "速食浓汤", "无糖气泡水"],
        "brands": ["山野", "鹿鸣", "禾下", "南麓", "小满"],
        "tags": ["有机", "低糖", "独立包装", "进口", "热卖"],
        "price": (15, 199),
    },
    "家居日用": {
        "bases": ["折叠收纳箱", "大豆蜡香薰", "纯棉毛巾套装", "护颈记忆枕", "护眼台灯",
                  "水洗棉床单", "陶瓷砂锅", "免手洗拖把", "加厚垃圾袋", "落地置物架"],
        "brands": ["归野", "木上", "一隅", "净屋", "青禾"],
        "tags": ["大容量", "可折叠", "亲肤", "静音", "高性价比"],
        "price": (9, 499),
    },
    "运动户外": {
        "bases": ["加厚瑜伽垫", "负重跳绳", "运动水壶", "铝合金登山杖", "专业跑步袜",
                  "减震护膝", "可调哑铃", "户外露营灯", "双人帐篷", "软飞盘"],
        "brands": ["野径", "凌峰", "疾风", "远山", "旅人"],
        "tags": ["轻量", "防滑", "速干", "户外", "新品"],
        "price": (25, 899),
    },
}

CITIES = ["上海", "北京", "杭州", "成都", "深圳", "西安", "武汉", "南京"]
EVENT_TYPES = ["view", "cart", "purchase", "rating"]
EVENT_WEIGHTS = [0.72, 0.12, 0.10, 0.06]
DEMO_PASSWORD = "demo1234"


def _money(value: float) -> float:
    return float(round(value + 0.9, 2))


def build_items(rng: np.random.Generator, count: int) -> list[dict]:
    names = list(CATALOG)
    items: list[dict] = []
    for index in range(count):
        category = names[index % len(names)]
        spec = CATALOG[category]
        base = spec["bases"][int(rng.integers(0, len(spec["bases"])))]
        brand = spec["brands"][int(rng.integers(0, len(spec["brands"])))]
        low, high = spec["price"]
        price = _money(float(np.round(rng.uniform(low, high) / 10.0) * 10))
        tag_pool = list(spec["tags"])
        rng.shuffle(tag_pool)
        tags = tag_pool[: 2 + int(rng.integers(0, 2))]
        items.append({
            "item_id": f"I{index + 1:04d}",
            "title": f"{brand} {base}",
            "category": category,
            "price": price,
            "tags": ",".join(tags),
            "description": f"{brand}{base}，{category}类目演示商品，价格 {price:.1f} 元。",
        })
    return items


def build_users(rng: np.random.Generator, count: int, password_hash: str,
                now: datetime) -> list[dict]:
    users = [
        {"user_id": "U0000", "username": "admin", "password_hash": password_hash,
         "role": "admin", "created_at": now - timedelta(days=60)},
        {"user_id": "U0001", "username": "demo", "password_hash": password_hash,
         "role": "user", "created_at": now - timedelta(days=45)},
    ]
    for index in range(2, count + 1):
        users.append({
            "user_id": f"U{index:04d}",
            "username": f"user{index:03d}",
            "password_hash": password_hash,
            "role": "user",
            "created_at": now - timedelta(days=int(rng.integers(5, 120))),
        })
    return users


def build_events(rng: np.random.Generator, users: list[dict], items: list[dict],
                 total_events: int, now: datetime) -> list[dict]:
    by_category: dict[str, list[dict]] = {}
    for item in items:
        by_category.setdefault(item["category"], []).append(item)
    categories = list(by_category)

    events: list[dict] = []
    target_users = [user for user in users if user["role"] != "admin"] or users
    per_user = max(3, int(total_events / max(1, len(target_users))))

    for user in target_users:
        favourites = list(rng.choice(categories, size=min(2, len(categories)), replace=False))
        for _ in range(int(rng.integers(max(3, per_user // 2), per_user + 2))):
            category = favourites[int(rng.integers(0, len(favourites)))] if rng.random() < 0.8 \
                else categories[int(rng.integers(0, len(categories)))]
            pool = by_category[category]
            item = pool[int(rng.integers(0, len(pool)))]
            event_type = str(rng.choice(EVENT_TYPES, p=EVENT_WEIGHTS))
            rating = float(rng.integers(3, 6)) if event_type == "rating" else None
            days_ago = float(rng.uniform(0, 45))
            events.append({
                "user_id": user["user_id"],
                "item_id": item["item_id"],
                "type": event_type,
                "rating": rating,
                "event_time": now - timedelta(days=days_ago,
                                              seconds=float(rng.integers(0, 86400))),
            })

    # 保证每个商品至少有一条行为（否则它永远进不了协同过滤与热门）
    seen = {event["item_id"] for event in events}
    for item in items:
        if item["item_id"] in seen:
            continue
        user = target_users[int(rng.integers(0, len(target_users)))]
        events.append({
            "user_id": user["user_id"],
            "item_id": item["item_id"],
            "type": "view",
            "rating": None,
            "event_time": now - timedelta(days=float(rng.uniform(0, 45))),
        })

    events.sort(key=lambda event: event["event_time"])
    return events


def dataset_fingerprint(items: list[dict], users: list[dict], events: list[dict]) -> str:
    payload = json.dumps({
        "items": [item["item_id"] for item in items],
        "users": [user["username"] for user in users],
        "event_count": len(events),
        "event_types": sorted([event["type"] for event in events]),
    }, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
