"""Catalog for Phase 2: typed columns and on-disk persistence."""

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Tuple

from my_dbms.types import DataType

CATALOG_MAGIC = b"MYDBMS02"


@dataclass(frozen=True)
class ColumnDef:
    name: str
    dtype: DataType


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: Tuple[ColumnDef, ...]
    head_page_id: int

    def __init__(self, name: str, columns: Iterable[ColumnDef], head_page_id: int) -> None:
        cols = tuple(columns)
        if not cols:
            raise ValueError("table must have at least one column")
        names = [c.name for c in cols]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate column names in {names}")
        for i, c in enumerate(cols):
            if not isinstance(c, ColumnDef):
                raise TypeError(f"column {i}: expected ColumnDef, got {type(c).__name__}")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "columns", cols)
        object.__setattr__(self, "head_page_id", head_page_id)


class Catalog:
    def __init__(self) -> None:
        self._tables: dict[str, TableSchema] = {}

    def add(self, schema: TableSchema) -> None:
        if schema.name in self._tables:
            raise ValueError(f"table {schema.name!r} already exists")
        self._tables[schema.name] = schema

    def get(self, name: str) -> TableSchema:
        if name not in self._tables:
            raise KeyError(f"unknown table {name!r}")
        return self._tables[name]

    def table_names(self) -> Iterator[str]:
        return iter(self._tables.keys())

    def save(self, path: str) -> None:
        parts: List[bytes] = [CATALOG_MAGIC]
        names = list(self._tables.keys())
        parts.append(struct.pack("<I", len(names)))
        for name in names:
            schema = self._tables[name]
            nb = name.encode("utf-8")
            parts.append(struct.pack("<H", len(nb)) + nb)
            parts.append(struct.pack("<H", len(schema.columns)))
            for col in schema.columns:
                cb = col.name.encode("utf-8")
                parts.append(struct.pack("<H", len(cb)) + cb)
                parts.append(struct.pack("<B", int(col.dtype)))
            parts.append(struct.pack("<I", schema.head_page_id))
        Path(path).write_bytes(b"".join(parts))

    @classmethod
    def load(cls, path: str) -> "Catalog":
        p = Path(path)
        if not p.exists() or p.stat().st_size == 0:
            return cls()
        data = p.read_bytes()
        if data[: len(CATALOG_MAGIC)] != CATALOG_MAGIC:
            raise ValueError(f"bad magic in catalog file {path!r}")
        off = len(CATALOG_MAGIC)
        (num_tables,) = struct.unpack_from("<I", data, off); off += 4
        c = cls()
        for _ in range(num_tables):
            (nlen,) = struct.unpack_from("<H", data, off); off += 2
            name = data[off : off + nlen].decode("utf-8"); off += nlen
            (ncols,) = struct.unpack_from("<H", data, off); off += 2
            cols: List[ColumnDef] = []
            for _ in range(ncols):
                (clen,) = struct.unpack_from("<H", data, off); off += 2
                cname = data[off : off + clen].decode("utf-8"); off += clen
                (tbyte,) = struct.unpack_from("<B", data, off); off += 1
                cols.append(ColumnDef(name=cname, dtype=DataType(tbyte)))
            (head,) = struct.unpack_from("<I", data, off); off += 4
            c.add(TableSchema(name=name, columns=cols, head_page_id=head))
        return c
