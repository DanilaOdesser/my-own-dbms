"""DataType enum and value validation, shared across schema, catalog, and database."""

from enum import IntEnum


class DataType(IntEnum):
    INT = 1
    TEXT = 2
    BOOL = 3
    FLOAT = 4


INT32_MIN = -(2 ** 31)
INT32_MAX = 2 ** 31 - 1
TEXT_MAX_BYTES = 0xFFFF


def validate_value(dtype: DataType, value) -> None:
    if dtype is DataType.INT:
        # bool is an int subclass — reject it explicitly
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"INT expects int, got {type(value).__name__}")
        if value < INT32_MIN or value > INT32_MAX:
            raise ValueError(f"INT value {value} out of int32 range")
    elif dtype is DataType.BOOL:
        if not isinstance(value, bool):
            raise TypeError(f"BOOL expects bool, got {type(value).__name__}")
    elif dtype is DataType.TEXT:
        if not isinstance(value, str):
            raise TypeError(f"TEXT expects str, got {type(value).__name__}")
        if len(value.encode("utf-8")) > TEXT_MAX_BYTES:
            raise ValueError(f"TEXT length exceeds {TEXT_MAX_BYTES} bytes")
    elif dtype is DataType.FLOAT:
        if isinstance(value, bool) or not isinstance(value, float):
            raise TypeError(f"FLOAT expects float, got {type(value).__name__}")
    else:
        raise AssertionError(f"unhandled DataType: {dtype!r}")
