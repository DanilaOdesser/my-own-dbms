"""Slotted page (4096 bytes) for Phase 2."""

import struct
from typing import Iterator, Optional, Tuple

PAGE_SIZE = 4096
HEADER_SIZE = 12
SLOT_SIZE = 4
NO_NEXT_PAGE = 0xFFFFFFFF

_HEADER_FMT = "<IIHH"  # page_id, next_page_id, num_slots, free_space_end
_SLOT_FMT = "<HH"      # offset, length


class SlottedPage:
    def __init__(self, buffer: bytearray) -> None:
        if not isinstance(buffer, bytearray):
            raise TypeError("buffer must be a bytearray")
        if len(buffer) != PAGE_SIZE:
            raise ValueError(f"buffer must be {PAGE_SIZE} bytes, got {len(buffer)}")
        self._buf = buffer

    @classmethod
    def new(cls, page_id: int) -> "SlottedPage":
        buf = bytearray(PAGE_SIZE)
        struct.pack_into(_HEADER_FMT, buf, 0, page_id, NO_NEXT_PAGE, 0, PAGE_SIZE)
        return cls(buf)

    @property
    def buffer(self) -> bytearray:
        return self._buf

    @property
    def page_id(self) -> int:
        return struct.unpack_from("<I", self._buf, 0)[0]

    @property
    def next_page_id(self) -> int:
        return struct.unpack_from("<I", self._buf, 4)[0]

    @next_page_id.setter
    def next_page_id(self, value: int) -> None:
        if value < 0 or value > 0xFFFFFFFF:
            raise ValueError(f"next_page_id out of uint32: {value}")
        struct.pack_into("<I", self._buf, 4, value)

    @property
    def num_slots(self) -> int:
        return struct.unpack_from("<H", self._buf, 8)[0]

    def _set_num_slots(self, n: int) -> None:
        struct.pack_into("<H", self._buf, 8, n)

    @property
    def _free_space_end(self) -> int:
        return struct.unpack_from("<H", self._buf, 10)[0]

    def _set_free_space_end(self, v: int) -> None:
        struct.pack_into("<H", self._buf, 10, v)

    def free_space(self) -> int:
        slot_dir_end = HEADER_SIZE + self.num_slots * SLOT_SIZE
        return self._free_space_end - slot_dir_end

    def _slot_offset(self, slot_id: int) -> int:
        return HEADER_SIZE + slot_id * SLOT_SIZE

    def _read_slot(self, slot_id: int) -> Tuple[int, int]:
        return struct.unpack_from(_SLOT_FMT, self._buf, self._slot_offset(slot_id))

    def _write_slot(self, slot_id: int, offset: int, length: int) -> None:
        struct.pack_into(_SLOT_FMT, self._buf, self._slot_offset(slot_id), offset, length)

    def insert(self, data: bytes) -> Optional[int]:
        needed = len(data) + SLOT_SIZE
        if needed > self.free_space():
            return None
        new_offset = self._free_space_end - len(data)
        self._buf[new_offset : new_offset + len(data)] = data
        self._set_free_space_end(new_offset)
        slot_id = self.num_slots
        self._write_slot(slot_id, new_offset, len(data))
        self._set_num_slots(slot_id + 1)
        return slot_id

    def get(self, slot_id: int) -> bytes:
        if slot_id < 0 or slot_id >= self.num_slots:
            raise KeyError(f"slot {slot_id} out of range")
        offset, length = self._read_slot(slot_id)
        if length == 0:
            raise KeyError(f"slot {slot_id} is a tombstone")
        return bytes(self._buf[offset : offset + length])

    def delete(self, slot_id: int) -> bool:
        if slot_id < 0 or slot_id >= self.num_slots:
            raise KeyError(f"slot {slot_id} out of range")
        offset, length = self._read_slot(slot_id)
        if length == 0:
            return False
        self._write_slot(slot_id, offset, 0)
        return True

    def iter_live(self) -> Iterator[Tuple[int, bytes]]:
        for slot_id in range(self.num_slots):
            offset, length = self._read_slot(slot_id)
            if length == 0:
                continue
            yield slot_id, bytes(self._buf[offset : offset + length])
