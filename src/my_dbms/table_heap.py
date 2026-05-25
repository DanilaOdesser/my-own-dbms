"""Heap of slotted pages for one table."""

from typing import Iterator, Tuple

from my_dbms.disk_manager import DiskManager
from my_dbms.slotted_page import SlottedPage, NO_NEXT_PAGE, SLOT_SIZE

RID = Tuple[int, int]  # (page_id, slot_id)


class TableHeap:
    def __init__(self, disk: DiskManager, head_page_id: int) -> None:
        self._disk = disk
        self._head = head_page_id

    @classmethod
    def create(cls, disk: DiskManager) -> Tuple["TableHeap", int]:
        head = disk.allocate_page()
        page = SlottedPage.new(page_id=head)
        disk.write_page(head, bytes(page.buffer))
        return cls(disk, head), head

    @classmethod
    def open(cls, disk: DiskManager, head_page_id: int) -> "TableHeap":
        return cls(disk, head_page_id)

    @property
    def head_page_id(self) -> int:
        return self._head

    def _load(self, page_id: int) -> SlottedPage:
        return SlottedPage(bytearray(self._disk.read_page(page_id)))

    def _store(self, page: SlottedPage) -> None:
        self._disk.write_page(page.page_id, bytes(page.buffer))

    def insert(self, data: bytes) -> RID:
        needed = len(data) + SLOT_SIZE
        pid = self._head
        prev_page: SlottedPage | None = None

        while True:
            page = self._load(pid)
            if page.free_space() >= needed:
                slot = page.insert(data)
                assert slot is not None
                self._store(page)
                return (pid, slot)

            if page.next_page_id == NO_NEXT_PAGE:
                prev_page = page
                break
            pid = page.next_page_id

        new_pid = self._disk.allocate_page()
        new_page = SlottedPage.new(page_id=new_pid)
        slot = new_page.insert(data)
        assert slot is not None
        self._store(new_page)

        prev_page.next_page_id = new_pid
        self._store(prev_page)
        return (new_pid, slot)

    def get(self, page_id: int, slot_id: int) -> bytes:
        page = self._load(page_id)
        return page.get(slot_id)

    def delete(self, page_id: int, slot_id: int) -> bool:
        page = self._load(page_id)
        result = page.delete(slot_id)
        if result:
            self._store(page)
        return result

    def update(self, page_id: int, slot_id: int, new_data: bytes) -> RID:
        """In-place if it fits, else delete+reinsert (RID changes)."""
        page = self._load(page_id)
        old = page.get(slot_id)
        if len(new_data) == len(old):
            offset, _ = page._read_slot(slot_id)
            page._buf[offset : offset + len(new_data)] = new_data
            self._store(page)
            return (page_id, slot_id)
        page.delete(slot_id)
        self._store(page)
        return self.insert(new_data)

    def iter_live(self) -> Iterator[Tuple[RID, bytes]]:
        pid = self._head
        while True:
            page = self._load(pid)
            for slot_id, data in page.iter_live():
                yield (pid, slot_id), data
            if page.next_page_id == NO_NEXT_PAGE:
                return
            pid = page.next_page_id
