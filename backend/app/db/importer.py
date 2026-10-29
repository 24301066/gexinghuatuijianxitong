"""CSV import for catalog and behaviour events (all-or-nothing, per-row errors)."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Event, Item, User
from .models import utcnow

ITEM_COLUMNS = ["item_id", "title", "category", "price"]
ITEM_OPTIONAL = ["tags", "description"]
EVENT_COLUMNS = ["username", "item_id", "type"]
EVENT_OPTIONAL = ["rating", "event_time"]
EVENT_TYPES = {"view", "cart", "purchase", "rating"}


class CsvImportError(Exception):
    def __init__(self, message: str, errors: list[dict] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


def _parse_csv(text: str, required: list[str], optional: list[str]) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    headers = [header.strip() for header in (reader.fieldnames or [])]
    missing = [column for column in required if column not in headers]
    if missing:
        raise CsvImportError(f"表头缺少字段：{', '.join(missing)}")
    unknown = [header for header in headers
               if header not in required and header not in optional]
    if unknown:
        raise CsvImportError(f"表头含未知字段：{', '.join(unknown)}")
    return [{(key or "").strip(): (value or "").strip() for key, value in row.items()}
            for row in reader]


def _row_errors(rows: list[dict], validate) -> list[dict]:
    errors: list[dict] = []
    for number, row in enumerate(rows, start=2):  # header is line 1
        kind, message = validate(row)
        if kind:
            errors.append({"line": number, "field": kind, "message": message})
    return errors


def import_items(session: Session, text: str) -> dict:
    rows = _parse_csv(text, ITEM_COLUMNS, ITEM_OPTIONAL)

    def validate(row: dict) -> tuple[str, str]:
        for column in ITEM_COLUMNS:
            if not row.get(column):
                return column, "必填字段为空"
        try:
            float(row["price"])
        except ValueError:
            return "price", "价格必须是数字"
        return "", ""

    errors = _row_errors(rows, validate)
    if errors:
        raise CsvImportError("商品 CSV 校验失败", errors)

    created = 0
    for row in rows:
        existing = session.get(Item, row["item_id"])
        payload = {
            "item_id": row["item_id"],
            "title": row["title"],
            "category": row["category"],
            "price": float(row["price"]),
            "tags": row.get("tags", ""),
            "description": row.get("description", ""),
        }
        if existing:
            for key, value in payload.items():
                setattr(existing, key, value)
        else:
            session.add(Item(**payload))
            created += 1
    return {"rows": len(rows), "created": created, "updated": len(rows) - created}


def import_events(session: Session, text: str) -> dict:
    rows = _parse_csv(text, EVENT_COLUMNS, EVENT_OPTIONAL)
    usernames = {username: user_id for user_id, username in
                 session.execute(select(User.user_id, User.username))}
    item_ids = {item_id for (item_id,) in session.execute(select(Item.item_id))}

    def validate(row: dict) -> tuple[str, str]:
        for column in EVENT_COLUMNS:
            if not row.get(column):
                return column, "必填字段为空"
        if row["type"] not in EVENT_TYPES:
            return "type", f"事件类型必须是 {', '.join(sorted(EVENT_TYPES))} 之一"
        if row["username"] not in usernames:
            return "username", f"用户 {row['username']} 不存在"
        if row["item_id"] not in item_ids:
            return "item_id", f"商品 {row['item_id']} 不存在"
        if row.get("rating"):
            try:
                rating = float(row["rating"])
            except ValueError:
                return "rating", "评分必须是数字"
            if not 1 <= rating <= 5:
                return "rating", "评分必须在 1..5 之间"
        return "", ""

    errors = _row_errors(rows, validate)
    if errors:
        raise CsvImportError("行为 CSV 校验失败", errors)

    for row in rows:
        rating = float(row["rating"]) if row.get("rating") else None
        event_time = utcnow()
        if row.get("event_time"):
            from datetime import datetime

            try:
                event_time = datetime.fromisoformat(row["event_time"])
            except ValueError as exc:
                raise CsvImportError("时间格式必须是 ISO8601",
                                     [{"line": 0, "field": "event_time",
                                       "message": str(exc)}]) from exc
        session.add(Event(user_id=usernames[row["username"]], item_id=row["item_id"],
                          type=row["type"], rating=rating, event_time=event_time))
    return {"rows": len(rows)}


def import_file(session: Session, path: Path, kind: str) -> dict:
    text = Path(path).read_text(encoding="utf-8-sig")
    if kind == "items":
        return import_items(session, text)
    if kind == "events":
        return import_events(session, text)
    raise ValueError("kind 只能是 items 或 events")
