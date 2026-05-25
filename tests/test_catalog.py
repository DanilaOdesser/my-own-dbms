import pytest

from my_dbms.catalog import Catalog, ColumnDef, TableSchema
from my_dbms.types import DataType


def _users_schema(head: int = 0) -> TableSchema:
    return TableSchema(
        name="users",
        columns=[
            ColumnDef("id", DataType.INT),
            ColumnDef("name", DataType.TEXT),
            ColumnDef("active", DataType.BOOL),
            ColumnDef("score", DataType.FLOAT),
        ],
        head_page_id=head,
    )


def test_table_schema_typed_columns():
    s = _users_schema(head=7)
    assert s.name == "users"
    assert tuple(c.name for c in s.columns) == ("id", "name", "active", "score")
    assert tuple(c.dtype for c in s.columns) == (
        DataType.INT, DataType.TEXT, DataType.BOOL, DataType.FLOAT,
    )
    assert s.head_page_id == 7


def test_table_schema_rejects_duplicate_columns():
    with pytest.raises(ValueError):
        TableSchema(
            name="t",
            columns=[ColumnDef("x", DataType.INT), ColumnDef("x", DataType.TEXT)],
            head_page_id=0,
        )


def test_table_schema_rejects_empty_columns():
    with pytest.raises(ValueError):
        TableSchema(name="t", columns=[], head_page_id=0)


def test_catalog_add_and_get_typed():
    c = Catalog()
    s = _users_schema()
    c.add(s)
    assert c.get("users") is s


def test_catalog_save_load_roundtrip(tmp_path):
    cpath = tmp_path / "catalog"
    c = Catalog()
    c.add(_users_schema(head=3))
    c.add(TableSchema(
        name="orders",
        columns=[ColumnDef("oid", DataType.INT)],
        head_page_id=8,
    ))
    c.save(str(cpath))

    c2 = Catalog.load(str(cpath))
    assert set(c2.table_names()) == {"users", "orders"}
    u = c2.get("users")
    assert tuple(col.dtype for col in u.columns) == (
        DataType.INT, DataType.TEXT, DataType.BOOL, DataType.FLOAT,
    )
    assert u.head_page_id == 3
    assert c2.get("orders").head_page_id == 8


def test_catalog_load_missing_file_returns_empty(tmp_path):
    c = Catalog.load(str(tmp_path / "does_not_exist"))
    assert list(c.table_names()) == []


def test_catalog_load_bad_magic(tmp_path):
    p = tmp_path / "catalog"
    p.write_bytes(b"GARBAGE_")
    with pytest.raises(ValueError, match="magic"):
        Catalog.load(str(p))


def test_catalog_rejects_duplicate_table_name():
    c = Catalog()
    c.add(_users_schema())
    with pytest.raises(ValueError):
        c.add(_users_schema())
