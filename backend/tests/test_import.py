"""CSV import: validation, per-row errors, no partial writes."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.db.importer import CsvImportError, import_events, import_items
from app.db.models import Event, Item


@pytest.fixture()
def session(tmp_path):
    from app.db.session import init_db, make_engine, make_session_factory

    engine = make_engine(f"sqlite:///{(tmp_path / 'import.db').as_posix()}")
    init_db(engine)
    factory = make_session_factory(engine)
    with factory() as db:
        yield db


def test_import_items_creates_rows(session):
    text = ("item_id,title,category,price,tags\n"
            "I9001,演示导入商品,数码配件,99.9,新品\n")
    result = import_items(session, text)
    session.commit()
    assert result == {"rows": 1, "created": 1, "updated": 0}
    assert session.get(Item, "I9001").title == "演示导入商品"


def test_import_items_rejects_bad_rows_without_partial_write(session):
    text = ("item_id,title,category,price\n"
            "I9001,合法商品,数码配件,10\n"
            ",缺主键,数码配件,10\n"
            "I9003,价格错误,数码配件,abc\n")
    with pytest.raises(CsvImportError) as excinfo:
        import_items(session, text)
    errors = excinfo.value.errors
    assert [error["line"] for error in errors] == [3, 4]
    assert {error["field"] for error in errors} == {"item_id", "price"}
    session.rollback()
    assert session.scalar(select(func.count()).select_from(Item)) == 0


def test_import_items_rejects_unknown_header(session):
    with pytest.raises(CsvImportError):
        import_items(session, "item_id,title,category,price,oops\nI1,x,y,1,z\n")


def test_import_events_requires_existing_user_and_item(session):
    import_items(session, "item_id,title,category,price\nI9001,商品,数码配件,10\n")
    session.add(__import__("app.db.models", fromlist=["User"]).User(
        user_id="U9001", username="imported", password_hash="x", role="user"))
    session.commit()

    ok = import_events(session, "username,item_id,type\nimported,I9001,view\n")
    assert ok["rows"] == 1

    with pytest.raises(CsvImportError) as excinfo:
        import_events(session, "username,item_id,type\nghost,I9001,view\n")
    assert excinfo.value.errors[0]["field"] == "username"

    with pytest.raises(CsvImportError) as excinfo:
        import_events(session, "username,item_id,type\nimported,I404,view\n")
    assert excinfo.value.errors[0]["field"] == "item_id"

    with pytest.raises(CsvImportError) as excinfo:
        import_events(session, "username,item_id,type\nimported,I9001,like\n")
    assert excinfo.value.errors[0]["field"] == "type"


def test_import_events_rating_range(session):
    import_items(session, "item_id,title,category,price\nI9001,商品,数码配件,10\n")
    session.add(__import__("app.db.models", fromlist=["User"]).User(
        user_id="U9001", username="imported", password_hash="x", role="user"))
    session.commit()
    with pytest.raises(CsvImportError) as excinfo:
        import_events(session, "username,item_id,type,rating\nimported,I9001,rating,9\n")
    assert excinfo.value.errors[0]["field"] == "rating"
    assert session.scalar(select(func.count()).select_from(Event)) == 0
