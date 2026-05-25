"""Public DBMS API — Phase 2: typed columns, paged storage, directory layout."""

from pathlib import Path
from typing import Dict, Iterator, List, Sequence, Tuple

from my_dbms.catalog import Catalog, ColumnDef, TableSchema
from my_dbms.disk_manager import DiskManager
from my_dbms.schema import Schema
from my_dbms.table_heap import TableHeap
from my_dbms.types import DataType, validate_value

CATALOG_FILE = "catalog"


class Database:
    def __init__(
        self,
        db_dir: Path,
        catalog: Catalog,
        disks: Dict[str, DiskManager],
        heaps: Dict[str, TableHeap],
        schemas: Dict[str, Schema],
    ) -> None:
        self._dir = db_dir
        self._catalog = catalog
        self._disks = disks
        self._heaps = heaps
        self._schemas = schemas

    @classmethod
    def open(cls, path: str) -> "Database":
        d = Path(path)
        d.mkdir(parents=True, exist_ok=True)

        catalog = Catalog.load(str(d / CATALOG_FILE))
        disks: Dict[str, DiskManager] = {}
        heaps: Dict[str, TableHeap] = {}
        schemas: Dict[str, Schema] = {}

        for tname in list(catalog.table_names()):
            tschema = catalog.get(tname)
            tpath = d / f"{tname}.tbl"
            dm = DiskManager(str(tpath))
            disks[tname] = dm
            heaps[tname] = TableHeap.open(dm, tschema.head_page_id)
            schemas[tname] = Schema([c.dtype for c in tschema.columns])

        return cls(d, catalog, disks, heaps, schemas)

    def close(self) -> None:
        self._catalog.save(str(self._dir / CATALOG_FILE))
        for dm in self._disks.values():
            dm.close()

    def table_names(self) -> Iterator[str]:
        return self._catalog.table_names()

    def create_table(self, name: str, columns: Sequence[Tuple[str, DataType]]) -> None:
        col_defs = [ColumnDef(n, t) for n, t in columns]
        tpath = self._dir / f"{name}.tbl"
        if tpath.exists():
            raise ValueError(f"table file {tpath} already exists on disk")

        dm = DiskManager(str(tpath))
        heap, head = TableHeap.create(dm)

        schema = TableSchema(name=name, columns=col_defs, head_page_id=head)
        try:
            self._catalog.add(schema)
        except Exception:
            dm.close()
            tpath.unlink(missing_ok=True)
            raise

        self._disks[name] = dm
        self._heaps[name] = heap
        self._schemas[name] = Schema([c.dtype for c in col_defs])
        self._catalog.save(str(self._dir / CATALOG_FILE))

    def insert(self, table: str, row: Sequence) -> None:
        tschema = self._catalog.get(table)
        row = list(row)
        if len(row) != len(tschema.columns):
            raise ValueError(
                f"row has {len(row)} values, table {table!r} has {len(tschema.columns)} columns"
            )
        data = self._schemas[table].serialize(tuple(row))
        self._heaps[table].insert(data)

    def select(self, table: str, where: dict | None = None) -> List[List]:
        tschema = self._catalog.get(table)
        heap = self._heaps[table]
        schema = self._schemas[table]

        where = where or {}
        col_index = self._validate_where(tschema, where)

        out: List[List] = []
        for _rid, raw in heap.iter_live():
            row = list(schema.deserialize(raw))
            if self._matches(row, col_index, where):
                out.append(row)
        return out

    def update(self, table: str, where: dict | None, set: dict) -> int:
        tschema = self._catalog.get(table)
        heap = self._heaps[table]
        schema = self._schemas[table]

        set_index: dict[int, object] = {}
        for col_name, value in set.items():
            col = self._find_col(tschema, col_name)
            validate_value(col.dtype, value)
            set_index[tschema.columns.index(col)] = value

        where = where or {}
        col_index = self._validate_where(tschema, where)

        to_change: List[Tuple[Tuple[int, int], List]] = []
        for rid, raw in heap.iter_live():
            row = list(schema.deserialize(raw))
            if not self._matches(row, col_index, where):
                continue
            for idx, val in set_index.items():
                row[idx] = val
            to_change.append((rid, row))

        for rid, new_row in to_change:
            new_raw = schema.serialize(tuple(new_row))
            heap.update(rid[0], rid[1], new_raw)
        return len(to_change)

    def delete(self, table: str, where: dict | None) -> int:
        tschema = self._catalog.get(table)
        heap = self._heaps[table]
        schema = self._schemas[table]

        where = where or {}
        col_index = self._validate_where(tschema, where)

        rids: List[Tuple[int, int]] = []
        for rid, raw in heap.iter_live():
            row = list(schema.deserialize(raw))
            if self._matches(row, col_index, where):
                rids.append(rid)
        for pid, sid in rids:
            heap.delete(pid, sid)
        return len(rids)

    @staticmethod
    def _find_col(tschema: TableSchema, name: str) -> ColumnDef:
        for c in tschema.columns:
            if c.name == name:
                return c
        raise KeyError(f"unknown column {name!r} in table {tschema.name!r}")

    @classmethod
    def _validate_where(cls, tschema: TableSchema, where: dict) -> dict[str, int]:
        idx: dict[str, int] = {}
        for col_name, expected in where.items():
            col = cls._find_col(tschema, col_name)
            validate_value(col.dtype, expected)
            idx[col_name] = next(
                i for i, c in enumerate(tschema.columns) if c.name == col_name
            )
        return idx

    @staticmethod
    def _matches(row: List, col_index: dict[str, int], where: dict) -> bool:
        for col_name, expected in where.items():
            if row[col_index[col_name]] != expected:
                return False
        return True
