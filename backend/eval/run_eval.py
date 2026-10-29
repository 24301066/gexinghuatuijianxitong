"""Offline evaluation: time-based split, strategy comparison, JSON + Markdown report.

    python -m eval.run_eval --data-dir .data --out docs/评估
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from app.config import load_rec_config, load_settings
from app.db.models import Event, Item
from app.db.session import init_db, make_engine, make_session_factory
from app.rec.engine import Recommender

from . import metrics


def split_events(events: list[dict], ratio: float = 0.8) -> tuple[list[dict], list[dict], datetime]:
    """Time-ordered split; the training slice never contains post-cutoff events."""
    ordered = sorted(events, key=lambda event: event["event_time"])
    if not ordered:
        raise ValueError("没有可用于评估的事件")
    ratio = min(max(ratio, 0.1), 0.95)
    cut = max(1, int(len(ordered) * ratio))
    train = ordered[:cut]
    test = ordered[cut:]
    cutoff_time = ordered[cut - 1]["event_time"]
    return train, test, cutoff_time


def ground_truth(test_events: list[dict]) -> dict[str, set[str]]:
    truth: dict[str, set[str]] = {}
    for event in test_events:
        truth.setdefault(event["user_id"], set()).add(event["item_id"])
    return truth


def _strategy_engine(strategy: str, config: dict, model_version: str) -> Recommender:
    strategy_config = copy.deepcopy(config)
    if strategy == "popular":
        strategy_config["weights"] = {"cf": 0.0, "content": 0.0, "popular": 1.0}
    return Recommender(strategy_config, model_version=f"{model_version}-{strategy}")


def evaluate(engines: dict[str, Recommender], test_events: list[dict], items: list[dict],
             cutoffs: list[int]) -> dict:
    k_max = max(cutoffs)
    truth = ground_truth(test_events)
    item_counts = Counter(event["item_id"] for event in test_events)
    total_events = sum(item_counts.values()) or 1
    results: dict[str, dict] = {}

    for name, engine in engines.items():
        per_cutoff = {k: {"recall": 0.0, "ndcg": 0.0, "users": 0} for k in cutoffs}
        recommendations: list[list[str]] = []
        for user_id, relevant in truth.items():
            response = engine.recommend(user_id, size=k_max, page=1)
            recommended = [row["item_id"] for row in response["items"]]
            recommendations.append(recommended)
            for k in cutoffs:
                per_cutoff[k]["recall"] += metrics.recall_at_k(recommended, relevant, k)
                per_cutoff[k]["ndcg"] += metrics.ndcg_at_k(recommended, relevant, k)
                per_cutoff[k]["users"] += 1

        block: dict = {"users": len(truth)}
        for k in cutoffs:
            users = per_cutoff[k]["users"] or 1
            block[f"recall@{k}"] = round(per_cutoff[k]["recall"] / users, 4)
            block[f"ndcg@{k}"] = round(per_cutoff[k]["ndcg"] / users, 4)
        block["coverage"] = round(metrics.coverage(recommendations, len(items)), 4)
        block["novelty"] = round(metrics.novelty(recommendations, dict(item_counts),
                                                 total_events), 4)
        results[name] = block
    return results


def render_markdown(report: dict) -> str:
    cutoffs = report["cutoffs"]
    header = ["策略", "用户数"] + [f"Recall@{k}" for k in cutoffs] + \
             [f"NDCG@{k}" for k in cutoffs] + ["覆盖率", "新颖度"]
    lines = [
        "# 离线评估报告",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 数据集指纹：`{report['dataset']['fingerprint']}`",
        f"- 事件总数：{report['dataset']['events']}（训练 {report['split']['train']} / "
        f"测试 {report['split']['test']}）",
        f"- 切分时间：{report['split']['cutoff']}",
        "- 指标口径：训练集只用切分前事件，测试集按用户去重后的商品集计算",
        f"- 运行耗时：{report['runtime_seconds']}s",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
    ]
    for name, block in report["strategies"].items():
        cells = [name, str(block["users"])]
        cells += [f"{block[f'recall@{k}']:.4f}" for k in cutoffs]
        cells += [f"{block[f'ndcg@{k}']:.4f}" for k in cutoffs]
        cells += [f"{block['coverage']:.4f}", f"{block['novelty']:.4f}"]
        lines.append("| " + " | ".join(cells) + " |")
    lines += [
        "",
        "## 怎么读",
        "",
        "- Recall@K / NDCG@K 越高，说明测试期用户真实交互的商品越容易被推荐到前面。",
        "- 覆盖率越高，推荐越分散；新颖度越高，越不依赖头部热门商品。",
        "- popular 是热门基线，hybrid 是三路召回融合；两者用同一份切分对比。",
        "",
    ]
    return "\n".join(lines)


def run(data_dir: Path | None, out_dir: Path, config_path: Path | None = None) -> dict:
    started = time.time()
    settings = load_settings(data_dir, config_path)
    config = load_rec_config(config_path or settings.rec_config_path)

    engine_db = make_engine(settings.db_url)
    init_db(engine_db)
    factory = make_session_factory(engine_db)
    with factory() as session:
        items = [{"item_id": row.item_id, "title": row.title, "category": row.category,
                  "price": float(row.price), "tags": row.tags or ""}
                 for row in session.query(Item)]
        events = [{"user_id": row.user_id, "item_id": row.item_id, "type": row.type,
                   "rating": row.rating, "event_time": row.event_time}
                  for row in session.query(Event)]

    if not events:
        raise SystemExit("库里没有事件，先运行 tools/seed_demo.py 生成演示数据")

    train, test, cutoff = split_events(events, float(config["eval"]["split_ratio"]))
    cutoffs = sorted(int(value) for value in config["eval"]["cutoffs"])
    strategy_names = list(config["eval"].get("strategies") or ["popular", "hybrid"])

    engines = {name: _strategy_engine(name, config, settings.model_version()).fit(items, train)
               for name in strategy_names}
    results = evaluate(engines, test, items, cutoffs)

    fingerprint = hashlib.sha256(
        ("|".join(item["item_id"] for item in items)
         + f"|events={len(events)}|split={cutoff.isoformat()}").encode("utf-8")
    ).hexdigest()[:16]

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "dataset": {"fingerprint": fingerprint, "events": len(events),
                    "items": len(items),
                    "users": len({event["user_id"] for event in events})},
        "split": {"ratio": float(config["eval"]["split_ratio"]),
                  "train": len(train), "test": len(test),
                  "cutoff": cutoff.isoformat(sep=" ")},
        "cutoffs": cutoffs,
        "strategies": results,
        "config": {"weights": config["weights"], "diversity": config["diversity"]},
        "runtime_seconds": round(time.time() - started, 2),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    (out_dir / "report.md").write_text(render_markdown(report), encoding="utf-8", newline="\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="离线评估推荐策略")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=Path("docs/评估"))
    parser.add_argument("--config", type=Path, default=None)
    args = parser.parse_args(argv)

    report = run(args.data_dir, args.out, args.config)
    print(json.dumps({"strategies": report["strategies"], "split": report["split"]},
                     ensure_ascii=False, indent=2))
    print(f"报告已写入 {args.out}/report.json 与 report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
