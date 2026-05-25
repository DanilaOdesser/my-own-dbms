# my-dbms

A file-based DBMS built for the databases course (HW6 + HW6*).

## What it does

- Multiple named tables with typed columns (INT, TEXT, BOOL, FLOAT)
- `CREATE TABLE`, `INSERT`, `SELECT`, `UPDATE`, `DELETE`
- `WHERE` clause with exact-match equality across columns (AND semantics)
- All data persisted to disk: one catalog file plus one paged file per table
- Storage layer: 4096-byte slotted pages, chained per table (RID = (page_id, slot_id))

## Usage (Python API)

```python
from my_dbms.database import Database
from my_dbms.types import DataType

db = Database.open("./mydb")
db.create_table("users", [("id", DataType.INT), ("name", DataType.TEXT)])
db.insert("users", [1, "Alice"])
db.select("users", where={"id": 1})        # [[1, "Alice"]]
db.update("users", where={"id": 1}, set={"name": "Bob"})
db.delete("users", where={"id": 1})
db.close()
```

## Tests

```
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -v
```
