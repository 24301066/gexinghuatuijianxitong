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


POST_TEMPLATES = {
    "美妆个护": ["空瓶记录｜{title}真的会回购", "敏感肌实测：{title}用了一个月",
                 "早八人必备，{title}两分钟搞定"],
    "数码配件": ["开箱｜{title}值不值这个价", "用了两周，{title}的优缺点都在这",
                 "{title}配这个桌面，效率翻倍"],
    "食品饮料": ["囤货清单｜{title}好吃到停不下来", "打工人早餐救星：{title}",
                 "{title}测评，配料表我看了三遍"],
    "家居日用": ["小户型收纳｜{title}真的省地方", "居家好物｜{title}用了一个月",
                 "{title}实测：细节做得比想象好"],
    "运动户外": ["周末徒步｜{title}背了一天不累", "减脂期必备：{title}实测",
                 "{title}开箱，做工比价格更惊喜"],
}

POST_BODIES = [
    "买之前纠结了很久，实际用下来比预期好。{category}里这个价位算很能打，细节和手感都在线。",
    "被朋友安利的，用了一周来交作业。日常使用完全够，{tags}这几个点确实做到了。",
    "冲着口碑买的，没踩雷。包装、做工都挺用心，已经推荐给同事了。",
    "对比了三家最后选它，主要是{tags}，实际体验也对得起价格。",
]

KEYWORDS_BY_CATEGORY = {
    "美妆个护": ["面膜", "精华", "防晒", "洁面", "口红"],
    "数码配件": ["耳机", "键盘", "充电宝", "硬盘", "音箱"],
    "食品饮料": ["咖啡", "坚果", "燕麦", "巧克力", "气泡水"],
    "家居日用": ["收纳", "香薰", "台灯", "枕头", "砂锅"],
    "运动户外": ["瑜伽垫", "登山", "跳绳", "哑铃", "露营"],
}


def build_posts(rng: np.random.Generator, items: list[dict], users: list[dict],
                count: int, now: datetime) -> list[dict]:
    authors = [user for user in users if user["role"] != "admin"] or users
    posts: list[dict] = []
    for index in range(count):
        item = items[int(rng.integers(0, len(items)))]
        category = item["category"]
        template = POST_TEMPLATES[category][int(rng.integers(0, 3))]
        tags = item["tags"].split(",") if item["tags"] else []
        tag_text = "、".join(tags[:2]) or "性价比"
        body = POST_BODIES[int(rng.integers(0, len(POST_BODIES)))].format(
            category=category, tags=tag_text)
        is_video = index % 3 == 1
        posts.append({
            "post_id": f"P{index + 1:04d}",
            "author_id": authors[int(rng.integers(0, len(authors)))]["user_id"],
            "title": template.format(title=item["title"]),
            "body": body,
            "media_type": "video" if is_video else "image",
            "video_seconds": int(rng.integers(12, 75)) if is_video else 0,
            "product_id": item["item_id"],
            "likes": int(rng.integers(3, 2600)),
            "tags": item["tags"],
            "created_at": now - timedelta(days=float(rng.uniform(0, 60)),
                                          seconds=float(rng.integers(0, 86400))),
        })
    posts.sort(key=lambda post: post["created_at"], reverse=True)
    return posts


def build_searches(rng: np.random.Generator, users: list[dict], items: list[dict],
                   per_user: int, now: datetime) -> list[dict]:
    categories = sorted({item["category"] for item in items})
    active = [user for user in users if user["role"] != "admin"] or users
    rows: list[dict] = []
    for user in active:
        if rng.random() < 0.55:
            continue
        count = int(rng.integers(1, per_user + 1))
        category = categories[int(rng.integers(0, len(categories)))]
        words = KEYWORDS_BY_CATEGORY[category]
        for _ in range(count):
            rows.append({
                "user_id": user["user_id"],
                "keyword": words[int(rng.integers(0, len(words)))],
                "created_at": now - timedelta(days=float(rng.uniform(0, 20)),
                                              seconds=float(rng.integers(0, 86400))),
            })
    rows.sort(key=lambda row: row["created_at"])
    return rows


def build_dwells(rng: np.random.Generator, users: list[dict], posts: list[dict],
                 per_user: int, now: datetime) -> list[dict]:
    active = [user for user in users if user["role"] != "admin"] or users
    rows: list[dict] = []
    for user in active:
        if rng.random() < 0.5:
            continue
        for _ in range(int(rng.integers(1, per_user + 1))):
            post = posts[int(rng.integers(0, len(posts)))]
            rows.append({
                "user_id": user["user_id"],
                "post_id": post["post_id"],
                "seconds": float(round(rng.uniform(3, 90), 1)),
                "created_at": now - timedelta(days=float(rng.uniform(0, 20)),
                                              seconds=float(rng.integers(0, 86400))),
            })
    rows.sort(key=lambda row: row["created_at"])
    return rows
