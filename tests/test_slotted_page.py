import pytest

from my_dbms.slotted_page import (
    SlottedPage,
    PAGE_SIZE,
    HEADER_SIZE,
    SLOT_SIZE,
    NO_NEXT_PAGE,
)


def test_new_page_is_empty():
    p = SlottedPage.new(page_id=7)
    assert p.page_id == 7
    assert p.next_page_id == NO_NEXT_PAGE
    assert p.num_slots == 0
    assert p.free_space() == PAGE_SIZE - HEADER_SIZE


def test_insert_then_get_one_tuple():
    p = SlottedPage.new(page_id=0)
    slot = p.insert(b"hello")
    assert slot == 0
    assert p.num_slots == 1
    assert p.get(0) == b"hello"
    assert p.free_space() == PAGE_SIZE - HEADER_SIZE - 5 - SLOT_SIZE


def test_insert_two_tuples_have_growing_slot_ids():
    p = SlottedPage.new(page_id=0)
    assert p.insert(b"aaa") == 0
    assert p.insert(b"bbbb") == 1
    assert p.get(0) == b"aaa"
    assert p.get(1) == b"bbbb"


def test_insert_returns_none_when_no_space():
    p = SlottedPage.new(page_id=0)
    body = b"x" * (p.free_space() - SLOT_SIZE)
    assert p.insert(body) == 0
    assert p.insert(b"y") is None


def test_delete_marks_tombstone_and_iter_skips_it():
    p = SlottedPage.new(page_id=0)
    p.insert(b"a")
    p.insert(b"b")
    p.insert(b"c")
    assert p.delete(1) is True
    with pytest.raises(KeyError):
        p.get(1)
    assert list(p.iter_live()) == [(0, b"a"), (2, b"c")]
    assert p.num_slots == 3


def test_delete_twice_is_false():
    p = SlottedPage.new(page_id=0)
    p.insert(b"a")
    assert p.delete(0) is True
    assert p.delete(0) is False


def test_get_unknown_slot_raises():
    p = SlottedPage.new(page_id=0)
    with pytest.raises(KeyError):
        p.get(0)


def test_next_page_id_setter():
    p = SlottedPage.new(page_id=0)
    p.next_page_id = 5
    assert p.next_page_id == 5


def test_buffer_roundtrip():
    p = SlottedPage.new(page_id=3)
    p.insert(b"hello")
    p.insert(b"world")
    p.next_page_id = 9
    buf = bytes(p.buffer)
    assert len(buf) == PAGE_SIZE

    p2 = SlottedPage(bytearray(buf))
    assert p2.page_id == 3
    assert p2.next_page_id == 9
    assert p2.get(0) == b"hello"
    assert p2.get(1) == b"world"


def test_rejects_wrong_buffer_size():
    with pytest.raises(ValueError):
        SlottedPage(bytearray(100))
