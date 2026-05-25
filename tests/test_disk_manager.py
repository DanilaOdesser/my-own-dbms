import pytest

from my_dbms.disk_manager import DiskManager
from my_dbms.slotted_page import PAGE_SIZE


def test_open_new_file_has_zero_pages(tmp_path):
    p = tmp_path / "t.heap"
    dm = DiskManager(str(p))
    assert dm.num_pages == 0
    assert p.exists()
    dm.close()


def test_allocate_page_increments_count_and_zero_fills(tmp_path):
    dm = DiskManager(str(tmp_path / "t.heap"))
    pid = dm.allocate_page()
    assert pid == 0
    assert dm.num_pages == 1
    assert dm.read_page(0) == b"\x00" * PAGE_SIZE
    pid2 = dm.allocate_page()
    assert pid2 == 1
    dm.close()


def test_write_and_read_page(tmp_path):
    dm = DiskManager(str(tmp_path / "t.heap"))
    dm.allocate_page()
    data = bytes(range(256)) * (PAGE_SIZE // 256)
    dm.write_page(0, data)
    assert dm.read_page(0) == data
    dm.close()


def test_persists_across_reopen(tmp_path):
    p = tmp_path / "t.heap"
    dm = DiskManager(str(p))
    dm.allocate_page()
    dm.write_page(0, b"A" * PAGE_SIZE)
    dm.close()

    dm2 = DiskManager(str(p))
    assert dm2.num_pages == 1
    assert dm2.read_page(0) == b"A" * PAGE_SIZE
    dm2.close()


def test_read_out_of_range(tmp_path):
    dm = DiskManager(str(tmp_path / "t.heap"))
    with pytest.raises(ValueError):
        dm.read_page(0)
    dm.close()


def test_write_wrong_size(tmp_path):
    dm = DiskManager(str(tmp_path / "t.heap"))
    dm.allocate_page()
    with pytest.raises(ValueError):
        dm.write_page(0, b"\x00" * 10)
    dm.close()


def test_rejects_misaligned_file(tmp_path):
    p = tmp_path / "bad.heap"
    p.write_bytes(b"\x00" * (PAGE_SIZE + 7))
    with pytest.raises(ValueError, match="multiple of"):
        DiskManager(str(p))
