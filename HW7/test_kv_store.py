import pytest

from kv_store import KeyValueStore


def test_new_store_is_empty(tmp_path):
    s = KeyValueStore(str(tmp_path / "kv.log"))
    assert s.get("anything") is None
    s.close()


def test_set_and_get(tmp_path):
    s = KeyValueStore(str(tmp_path / "kv.log"))
    s.set("foo", "bar")
    assert s.get("foo") == "bar"
    s.close()


def test_overwrite_keeps_latest(tmp_path):
    s = KeyValueStore(str(tmp_path / "kv.log"))
    s.set("k", "v1")
    s.set("k", "v2")
    s.set("k", "v3")
    assert s.get("k") == "v3"
    s.close()


def test_delete_existing_returns_true_and_removes(tmp_path):
    s = KeyValueStore(str(tmp_path / "kv.log"))
    s.set("k", "v")
    assert s.delete("k") is True
    assert s.get("k") is None
    s.close()


def test_delete_nonexistent_returns_false(tmp_path):
    s = KeyValueStore(str(tmp_path / "kv.log"))
    assert s.delete("nope") is False
    s.close()


def test_state_restored_after_close_and_reopen(tmp_path):
    p = tmp_path / "kv.log"
    s = KeyValueStore(str(p))
    s.set("a", "1")
    s.set("b", "2")
    s.set("c", "3")
    s.delete("b")
    s.set("a", "1-updated")
    s.close()

    s2 = KeyValueStore(str(p))
    assert s2.get("a") == "1-updated"
    assert s2.get("b") is None
    assert s2.get("c") == "3"
    s2.close()


def test_unicode_keys_and_values(tmp_path):
    p = tmp_path / "kv.log"
    s = KeyValueStore(str(p))
    s.set("Łódź", "Kraków")
    s.set("普通话", "中文")
    s.close()

    s2 = KeyValueStore(str(p))
    assert s2.get("Łódź") == "Kraków"
    assert s2.get("普通话") == "中文"
    s2.close()


def test_special_characters_are_escaped(tmp_path):
    """Tabs, newlines, and backslashes in keys/values must round-trip."""
    p = tmp_path / "kv.log"
    s = KeyValueStore(str(p))
    weird = "a\tb\nc\\d"
    s.set(weird, weird)
    s.set("key\\with\\backslashes", "value\nwith\tboth")
    s.close()

    s2 = KeyValueStore(str(p))
    assert s2.get(weird) == weird
    assert s2.get("key\\with\\backslashes") == "value\nwith\tboth"
    s2.close()


def test_empty_key_and_value(tmp_path):
    p = tmp_path / "kv.log"
    s = KeyValueStore(str(p))
    s.set("", "empty-key")
    s.set("empty-value", "")
    s.close()

    s2 = KeyValueStore(str(p))
    assert s2.get("") == "empty-key"
    assert s2.get("empty-value") == ""
    s2.close()


def test_non_string_key_raises(tmp_path):
    s = KeyValueStore(str(tmp_path / "kv.log"))
    with pytest.raises(TypeError):
        s.set(123, "v")
    with pytest.raises(TypeError):
        s.get(123)
    with pytest.raises(TypeError):
        s.delete(123)
    s.close()


def test_non_string_value_raises(tmp_path):
    s = KeyValueStore(str(tmp_path / "kv.log"))
    with pytest.raises(TypeError):
        s.set("k", 123)
    s.close()


def test_truncated_last_line_is_dropped(tmp_path):
    """Simulate a crash mid-write: the trailing partial record must be skipped."""
    p = tmp_path / "kv.log"
    s = KeyValueStore(str(p))
    s.set("a", "1")
    s.set("b", "2")
    s.close()

    # Append a partial record (no trailing newline)
    with open(p, "a", encoding="utf-8") as f:
        f.write("SET\tc\t3-partial")

    s2 = KeyValueStore(str(p))
    assert s2.get("a") == "1"
    assert s2.get("b") == "2"
    assert s2.get("c") is None  # partial record dropped
    # The store should be usable after recovery
    s2.set("c", "3")
    assert s2.get("c") == "3"
    s2.close()

    s3 = KeyValueStore(str(p))
    assert s3.get("c") == "3"
    s3.close()


def test_corrupt_log_raises(tmp_path):
    p = tmp_path / "kv.log"
    p.write_bytes(b"GARBAGE\n")
    with pytest.raises(ValueError):
        KeyValueStore(str(p))


def test_context_manager_closes(tmp_path):
    p = tmp_path / "kv.log"
    with KeyValueStore(str(p)) as s:
        s.set("k", "v")
    # After exit, file is closed — reopening should see the write
    s2 = KeyValueStore(str(p))
    assert s2.get("k") == "v"
    s2.close()


def test_writes_are_flushed_per_call(tmp_path):
    """Each set/delete must be on disk before the call returns."""
    p = tmp_path / "kv.log"
    s = KeyValueStore(str(p))
    s.set("k", "v")
    # Open a second handle without closing the first to verify the write is visible
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()
    assert content == "SET\tk\tv\n"
    s.close()


def test_many_writes_replay_correctly(tmp_path):
    p = tmp_path / "kv.log"
    s = KeyValueStore(str(p))
    for i in range(1000):
        s.set(f"key{i}", f"value{i}")
    for i in range(0, 1000, 3):
        s.delete(f"key{i}")
    s.close()

    s2 = KeyValueStore(str(p))
    for i in range(1000):
        if i % 3 == 0:
            assert s2.get(f"key{i}") is None
        else:
            assert s2.get(f"key{i}") == f"value{i}"
    s2.close()
