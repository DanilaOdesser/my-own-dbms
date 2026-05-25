import pytest

from my_dbms.types import DataType, validate_value


def test_datatype_enum_values_stable():
    assert DataType.INT.value == 1
    assert DataType.TEXT.value == 2
    assert DataType.BOOL.value == 3
    assert DataType.FLOAT.value == 4


def test_validate_int_ok():
    validate_value(DataType.INT, 0)
    validate_value(DataType.INT, -2**31)
    validate_value(DataType.INT, 2**31 - 1)


def test_validate_int_rejects_bool_and_non_int():
    with pytest.raises(TypeError):
        validate_value(DataType.INT, True)
    with pytest.raises(TypeError):
        validate_value(DataType.INT, "1")


def test_validate_int_out_of_range():
    with pytest.raises(ValueError):
        validate_value(DataType.INT, 2**31)


def test_validate_text_ok():
    validate_value(DataType.TEXT, "")
    validate_value(DataType.TEXT, "Łódź")


def test_validate_text_rejects_non_str():
    with pytest.raises(TypeError):
        validate_value(DataType.TEXT, 5)


def test_validate_text_max_length():
    validate_value(DataType.TEXT, "x" * 65535)
    with pytest.raises(ValueError):
        validate_value(DataType.TEXT, "x" * 65536)


def test_validate_bool_ok():
    validate_value(DataType.BOOL, True)
    validate_value(DataType.BOOL, False)


def test_validate_bool_rejects_int_and_str():
    with pytest.raises(TypeError):
        validate_value(DataType.BOOL, 1)
    with pytest.raises(TypeError):
        validate_value(DataType.BOOL, "true")


def test_validate_float_ok():
    validate_value(DataType.FLOAT, 0.0)
    validate_value(DataType.FLOAT, -1.5)
    validate_value(DataType.FLOAT, 3.14)


def test_validate_float_rejects_bool_and_non_float():
    with pytest.raises(TypeError):
        validate_value(DataType.FLOAT, True)
    with pytest.raises(TypeError):
        validate_value(DataType.FLOAT, 1)
    with pytest.raises(TypeError):
        validate_value(DataType.FLOAT, "1.0")
