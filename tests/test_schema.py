import struct

import pytest

from my_dbms.schema import Schema
from my_dbms.types import DataType


def test_serialize_deserialize_roundtrip():
    s = Schema([DataType.INT, DataType.TEXT, DataType.BOOL, DataType.FLOAT])
    raw = s.serialize((42, "hello", True, 3.5))
    assert s.deserialize(raw) == (42, "hello", True, 3.5)


def test_serialize_int_format():
    s = Schema([DataType.INT])
    assert s.serialize((42,)) == struct.pack("<i", 42)


def test_serialize_text_length_prefix():
    s = Schema([DataType.TEXT])
    raw = s.serialize(("hi",))
    assert raw == struct.pack("<H", 2) + b"hi"


def test_serialize_bool_bytes():
    s = Schema([DataType.BOOL])
    assert s.serialize((True,)) == b"\x01"
    assert s.serialize((False,)) == b"\x00"


def test_serialize_float_format():
    s = Schema([DataType.FLOAT])
    assert s.serialize((3.5,)) == struct.pack("<d", 3.5)


def test_serialize_arity_mismatch():
    s = Schema([DataType.INT, DataType.INT])
    with pytest.raises(ValueError):
        s.serialize((1,))


def test_serialize_type_mismatch():
    s = Schema([DataType.INT])
    with pytest.raises(TypeError):
        s.serialize(("not-int",))


def test_deserialize_rejects_trailing_bytes():
    s = Schema([DataType.INT])
    raw = struct.pack("<i", 1) + b"\x00"
    with pytest.raises(ValueError):
        s.deserialize(raw)


def test_deserialize_rejects_truncated():
    s = Schema([DataType.INT])
    with pytest.raises(ValueError):
        s.deserialize(b"\x00\x00\x00")  # only 3 bytes


def test_deserialize_rejects_invalid_bool_byte():
    s = Schema([DataType.BOOL])
    with pytest.raises(ValueError):
        s.deserialize(b"\x02")


def test_empty_text_roundtrip():
    s = Schema([DataType.TEXT])
    raw = s.serialize(("",))
    assert raw == struct.pack("<H", 0)
    assert s.deserialize(raw) == ("",)
