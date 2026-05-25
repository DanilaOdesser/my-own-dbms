import pytest

from my_dbms.database import Database
from my_dbms.types import DataType


def _users_cols():
    return [
        ("id", DataType.INT),
        ("name", DataType.TEXT),
        ("active", DataType.BOOL),
        ("score", DataType.FLOAT),
    ]


def test_open_close_creates_directory(tmp_path):
    d = tmp_path / "mydb"
    db = Database.open(str(d))
    db.close()
    assert d.is_dir()
    assert (d / "catalog").exists()


def test_create_table_persists(tmp_path):
    d = tmp_path / "mydb"
    db = Database.open(str(d))
    db.create_table("users", _users_cols())
    db.close()

    db2 = Database.open(str(d))
    assert set(db2.table_names()) == {"users"}
    db2.close()


def test_create_table_duplicate_raises(tmp_path):
    db = Database.open(str(tmp_path / "mydb"))
    db.create_table("users", _users_cols())
    with pytest.raises(ValueError):
        db.create_table("users", _users_cols())
    db.close()


def test_create_table_empty_columns_raises(tmp_path):
    db = Database.open(str(tmp_path / "mydb"))
    with pytest.raises(ValueError):
        db.create_table("t", [])
    db.close()


def test_insert_and_select_typed(tmp_path):
    d = tmp_path / "mydb"
    db = Database.open(str(d))
    db.create_table("users", _users_cols())
    db.insert("users", [1, "Alice", True, 9.5])
    db.insert("users", [2, "Bob", False, 4.0])
    assert db.select("users") == [
        [1, "Alice", True, 9.5],
        [2, "Bob", False, 4.0],
    ]
    db.close()

    db2 = Database.open(str(d))
    assert db2.select("users", where={"name": "Alice"}) == [[1, "Alice", True, 9.5]]
    assert db2.select("users", where={"active": False}) == [[2, "Bob", False, 4.0]]
    db2.close()


def test_insert_type_mismatch(tmp_path):
    db = Database.open(str(tmp_path / "mydb"))
    db.create_table("t", [("x", DataType.INT)])
    with pytest.raises(TypeError):
        db.insert("t", ["not-int"])
    db.close()


def test_insert_wrong_arity(tmp_path):
    db = Database.open(str(tmp_path / "mydb"))
    db.create_table("t", [("a", DataType.INT), ("b", DataType.TEXT)])
    with pytest.raises(ValueError):
        db.insert("t", [1])
    db.close()


def test_select_where_unknown_column_raises(tmp_path):
    db = Database.open(str(tmp_path / "mydb"))
    db.create_table("t", [("x", DataType.INT)])
    db.insert("t", [1])
    with pytest.raises(KeyError):
        db.select("t", where={"missing": 1})
    db.close()


def test_update_persists(tmp_path):
    d = tmp_path / "mydb"
    db = Database.open(str(d))
    db.create_table("users", _users_cols())
    db.insert("users", [1, "Alice", True, 9.5])
    db.insert("users", [2, "Alice", True, 4.0])
    db.insert("users", [3, "Bob",   True, 5.0])

    n = db.update("users", where={"name": "Alice"}, set={"name": "Carol", "active": False})
    assert n == 2
    db.close()

    db2 = Database.open(str(d))
    assert db2.select("users") == [
        [1, "Carol", False, 9.5],
        [2, "Carol", False, 4.0],
        [3, "Bob",   True,  5.0],
    ]
    db2.close()


def test_update_type_mismatch(tmp_path):
    db = Database.open(str(tmp_path / "mydb"))
    db.create_table("t", [("x", DataType.INT)])
    db.insert("t", [1])
    with pytest.raises(TypeError):
        db.update("t", where={}, set={"x": "string"})
    db.close()


def test_delete_persists(tmp_path):
    d = tmp_path / "mydb"
    db = Database.open(str(d))
    db.create_table("t", [("x", DataType.INT)])
    db.insert("t", [1])
    db.insert("t", [2])
    db.insert("t", [3])
    assert db.delete("t", where={"x": 2}) == 1
    db.close()

    db2 = Database.open(str(d))
    assert db2.select("t") == [[1], [3]]
    db2.close()


def test_delete_empty_where_clears(tmp_path):
    db = Database.open(str(tmp_path / "mydb"))
    db.create_table("t", [("x", DataType.INT)])
    db.insert("t", [1])
    db.insert("t", [2])
    assert db.delete("t", where={}) == 2
    assert db.select("t") == []
    db.close()


def test_phase2_end_to_end_with_large_inserts(tmp_path):
    """Force multi-page heap to make sure pagination works under the API."""
    d = tmp_path / "mydb"
    db = Database.open(str(d))
    db.create_table("blobs", [("id", DataType.INT), ("body", DataType.TEXT)])

    for i in range(50):
        db.insert("blobs", [i, "x" * 200])

    rows = db.select("blobs")
    assert len(rows) == 50
    assert rows[0] == [0, "x" * 200]
    assert rows[49] == [49, "x" * 200]
    db.close()

    db2 = Database.open(str(d))
    assert len(db2.select("blobs")) == 50
    assert db2.select("blobs", where={"id": 25}) == [[25, "x" * 200]]
    db2.close()
