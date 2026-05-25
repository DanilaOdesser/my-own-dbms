import os
from typing import Optional


def _encode(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")


def _decode(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            if i + 1 >= n:
                raise ValueError("trailing backslash in record")
            nxt = s[i + 1]
            if nxt == "\\":
                out.append("\\")
            elif nxt == "t":
                out.append("\t")
            elif nxt == "n":
                out.append("\n")
            else:
                raise ValueError(f"unknown escape: \\{nxt}")
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


class KeyValueStore:
    def __init__(self, path: str) -> None:
        self._path = path
        self._data: dict[str, str] = {}
        self._replay_and_repair()
        self._f = open(path, "a", encoding="utf-8")

    def _replay_and_repair(self) -> None:
        if not os.path.exists(self._path):
            return
        with open(self._path, "rb") as f:
            raw = f.read()
        if not raw:
            return

        last_nl = raw.rfind(b"\n")
        valid_end = last_nl + 1 if last_nl != -1 else 0
        if valid_end < len(raw):
            with open(self._path, "r+b") as f:
                f.truncate(valid_end)
        if valid_end == 0:
            return

        text = raw[:valid_end].decode("utf-8")
        for line in text.split("\n")[:-1]:
            if not line:
                continue
            parts = line.split("\t")
            op = parts[0]
            if op == "SET":
                if len(parts) != 3:
                    raise ValueError(f"corrupt SET record: {line!r}")
                self._data[_decode(parts[1])] = _decode(parts[2])
            elif op == "DEL":
                if len(parts) != 2:
                    raise ValueError(f"corrupt DEL record: {line!r}")
                self._data.pop(_decode(parts[1]), None)
            else:
                raise ValueError(f"unknown op in record: {line!r}")

    def get(self, key: str) -> Optional[str]:
        if not isinstance(key, str):
            raise TypeError(f"key must be str, got {type(key).__name__}")
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        if not isinstance(key, str):
            raise TypeError(f"key must be str, got {type(key).__name__}")
        if not isinstance(value, str):
            raise TypeError(f"value must be str, got {type(value).__name__}")
        self._f.write(f"SET\t{_encode(key)}\t{_encode(value)}\n")
        self._f.flush()
        self._data[key] = value

    def delete(self, key: str) -> bool:
        if not isinstance(key, str):
            raise TypeError(f"key must be str, got {type(key).__name__}")
        existed = key in self._data
        self._f.write(f"DEL\t{_encode(key)}\n")
        self._f.flush()
        self._data.pop(key, None)
        return existed

    def close(self) -> None:
        if self._f is not None and not self._f.closed:
            self._f.close()

    def __enter__(self) -> "KeyValueStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
