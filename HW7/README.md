# HW7 — Append-only Key-Value Store

A string→string key-value store backed by an append-only log.

## How it works

- Every `set(k, v)` appends one line: `SET<TAB><k><TAB><v><NL>`
- Every `delete(k)` appends one line: `DEL<TAB><k><NL>`
- On open, the log is replayed top-to-bottom into an in-memory dict; the last record for each key wins
- Tabs, newlines, and backslashes in keys/values are backslash-escaped
- A torn trailing record (from a crash mid-write) is detected on open and truncated, so subsequent appends start at a clean boundary

## Usage

```python
from kv_store import KeyValueStore

with KeyValueStore("./mystore.log") as kv:
    kv.set("name", "Alice")
    kv.set("age", "30")
    print(kv.get("name"))     # "Alice"
    kv.delete("age")
    print(kv.get("age"))      # None
```

## Tests

From the repo root, with the existing `.venv`:

```
.venv/bin/pytest HW7/ -v
```

16 tests covering basic CRUD, persistence across reopen, unicode, escape round-tripping, empty key/value, type validation, torn-tail recovery, corrupt-log rejection, and a 1000-key replay.
