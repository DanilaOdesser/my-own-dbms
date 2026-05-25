"""Typed tuple serializer for Phase 2."""

import struct
from typing import List, Sequence, Tuple

from my_dbms.types import DataType, validate_value


class Schema:
    def __init__(self, column_types: Sequence[DataType]) -> None:
        cols = tuple(column_types)
        for i, c in enumerate(cols):
            if not isinstance(c, DataType):
                raise TypeError(f"column {i}: expected DataType, got {type(c).__name__}")
        self._cols: Tuple[DataType, ...] = cols

    @property
    def column_types(self) -> Tuple[DataType, ...]:
        return self._cols

    def serialize(self, values: Sequence) -> bytes:
        if len(values) != len(self._cols):
            raise ValueError(f"expected {len(self._cols)} values, got {len(values)}")
        parts: List[bytes] = []
        for dtype, value in zip(self._cols, values):
            validate_value(dtype, value)
            if dtype is DataType.INT:
                parts.append(struct.pack("<i", value))
            elif dtype is DataType.BOOL:
                parts.append(b"\x01" if value else b"\x00")
            elif dtype is DataType.TEXT:
                vb = value.encode("utf-8")
                parts.append(struct.pack("<H", len(vb)) + vb)
            elif dtype is DataType.FLOAT:
                parts.append(struct.pack("<d", value))
            else:
                raise AssertionError(f"unhandled DataType: {dtype!r}")
        return b"".join(parts)

    def deserialize(self, data: bytes) -> tuple:
        off = 0
        n = len(data)
        out: List = []
        for i, dtype in enumerate(self._cols):
            if dtype is DataType.INT:
                if off + 4 > n:
                    raise ValueError(f"column {i} (INT): truncated at offset {off}")
                (v,) = struct.unpack_from("<i", data, off)
                off += 4
                out.append(v)
            elif dtype is DataType.BOOL:
                if off + 1 > n:
                    raise ValueError(f"column {i} (BOOL): truncated at offset {off}")
                b = data[off]
                off += 1
                if b == 0x00:
                    out.append(False)
                elif b == 0x01:
                    out.append(True)
                else:
                    raise ValueError(f"column {i} (BOOL): invalid byte 0x{b:02x}")
            elif dtype is DataType.TEXT:
                if off + 2 > n:
                    raise ValueError(f"column {i} (TEXT): truncated length at {off}")
                (length,) = struct.unpack_from("<H", data, off)
                off += 2
                if off + length > n:
                    raise ValueError(f"column {i} (TEXT): truncated body at {off}")
                out.append(data[off : off + length].decode("utf-8"))
                off += length
            elif dtype is DataType.FLOAT:
                if off + 8 > n:
                    raise ValueError(f"column {i} (FLOAT): truncated at offset {off}")
                (v,) = struct.unpack_from("<d", data, off)
                off += 8
                out.append(v)
            else:
                raise AssertionError(f"unhandled DataType: {dtype!r}")
        if off != n:
            raise ValueError(f"trailing bytes: consumed {off} of {n}")
        return tuple(out)
