import pytest

from my_dbms.disk_manager import DiskManager
from my_dbms.slotted_page import PAGE_SIZE, HEADER_SIZE, SLOT_SIZE
from my_dbms.table_heap import TableHeap


def test_create_starts_with_one_empty_page(tmp_path):
    dm = DiskManager(str(tmp_path / "t.heap"))
    heap, head = TableHeap.create(dm)
    assert head == 0
    assert list(heap.iter_live()) == []
    dm.close()


def test_insert_and_iter(tmp_path):
    dm = DiskManager(str(tmp_path / "t.heap"))
    heap, head = TableHeap.create(dm)
    r1 = heap.insert(b"hello")
    r2 = heap.insert(b"world")
    assert r1 == (0, 0)
    assert r2 == (0, 1)
    out = list(heap.iter_live())
    assert out == [((0, 0), b"hello"), ((0, 1), b"world")]
    dm.close()


def test_persists_across_reopen(tmp_path):
    p = tmp_path / "t.heap"
    dm = DiskManager(str(p))
    heap, head = TableHeap.create(dm)
    heap.insert(b"a")
    heap.insert(b"b")
    dm.close()

    dm2 = DiskManager(str(p))
    heap2 = TableHeap.open(dm2, head)
    assert [d for _, d in heap2.iter_live()] == [b"a", b"b"]
    dm2.close()


def test_insert_spills_to_new_page_when_full(tmp_path):
    dm = DiskManager(str(tmp_path / "t.heap"))
    heap, _ = TableHeap.create(dm)
    big = b"x" * (PAGE_SIZE - HEADER_SIZE - SLOT_SIZE)
    rid1 = heap.insert(big)
    assert rid1 == (0, 0)
    rid2 = heap.insert(b"small")
    assert rid2[0] == 1
    assert dm.num_pages == 2
    dm.close()


def test_delete_marks_tombstone_and_iter_skips(tmp_path):
    dm = DiskManager(str(tmp_path / "t.heap"))
    heap, _ = TableHeap.create(dm)
    r1 = heap.insert(b"a")
    r2 = heap.insert(b"b")
    assert heap.delete(*r1) is True
    assert list(heap.iter_live()) == [(r2, b"b")]
    with pytest.raises(KeyError):
        heap.get(*r1)
    dm.close()


def test_iter_across_multiple_pages_in_order(tmp_path):
    dm = DiskManager(str(tmp_path / "t.heap"))
    heap, _ = TableHeap.create(dm)
    big = b"x" * (PAGE_SIZE - HEADER_SIZE - SLOT_SIZE)
    heap.insert(big)         # page 0, slot 0
    heap.insert(b"second")   # page 1, slot 0
    heap.insert(b"third")    # page 1, slot 1
    rids = [rid for rid, _ in heap.iter_live()]
    assert rids == [(0, 0), (1, 0), (1, 1)]
    dm.close()
