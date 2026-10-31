"""Schema and seeding invariants."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import (Dwell, Event, Item, Merchant, Post, Review, Search, User)
from app.db.seed import seed_demo
from app.db.session import init_db, make_engine, make_session_factory


@pytest.fixture()
def session(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'schema.db').as_posix()}")
    init_db(engine)
    factory = make_session_factory(engine)
    with factory() as db:
        yield db


def test_tables_accept_rows(session):
    session.add(Item(item_id="I1", title="测试商品", category="数码配件", price=19.9,
                     tags="新", description=""))
    session.add(User(user_id="U1", username="u1", password_hash="x", role="user"))
    session.add(Event(user_id="U1", item_id="I1", type="view", idempotency_key="k1"))
    session.commit()
    assert session.scalar(select(func.count()).select_from(Item)) == 1


def test_idempotency_key_is_unique(session):
    session.add(Item(item_id="I1", title="测试商品", category="数码配件", price=19.9))
    session.add(User(user_id="U1", username="u1", password_hash="x", role="user"))
    session.add(Event(user_id="U1", item_id="I1", type="view", idempotency_key="dup"))
    session.commit()
    session.add(Event(user_id="U1", item_id="I1", type="view", idempotency_key="dup"))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_seed_is_deterministic(session):
    first = seed_demo(session, seed=7, users=5, items=10, events=40)
    for table in (Review, Merchant, Dwell, Search, Post, Event, Item, User):
        session.query(table).delete()
    session.commit()
    second = seed_demo(session, seed=7, users=5, items=10, events=40)
    assert first["fingerprint"] == second["fingerprint"]
    assert first["items"] == second["items"] == 10
    assert first["events"] == second["events"]
