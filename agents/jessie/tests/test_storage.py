import json
import pytest

from agents.jessie.src.storage import InMemoryStorage, LocalJSONStorage, StorageError


def test_in_memory_storage_round_trip(tmp_path):
    storage = InMemoryStorage()
    record = {"id": "abc", "status": "new"}
    storage.create_record(record)
    assert storage.get_record("abc") == record
    assert storage.list_records() == [record]


def test_local_json_storage_persists_and_backs_up(tmp_path):
    path = tmp_path / "intakes.json"
    path.write_text(json.dumps([{"id": "one", "status": "new"}]), encoding="utf-8")
    storage = LocalJSONStorage(path)
    storage.create_record({"id": "two", "status": "new"})
    storage.write_records(storage.list_records())
    backup_path = path.with_suffix(path.suffix + ".bak")
    assert backup_path.exists()
    assert json.loads(path.read_text(encoding="utf-8"))[1]["id"] == "two"


def test_corrupted_json_raises_storage_error(tmp_path):
    path = tmp_path / "intakes.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(StorageError, match="corrupted"):
        LocalJSONStorage(path)


def test_duplicate_id_is_rejected(tmp_path):
    storage = LocalJSONStorage(tmp_path / "intakes.json")
    storage.create_record({"id": "dup", "status": "new"})
    with pytest.raises(StorageError, match="duplicate"):
        storage.create_record({"id": "dup", "status": "updated"})


def test_atomic_replacement_is_testable(tmp_path):
    path = tmp_path / "intakes.json"
    storage = LocalJSONStorage(path)
    storage.write_records([{"id": "fresh", "status": "new"}])
    assert json.loads(path.read_text(encoding="utf-8"))[0]["id"] == "fresh"
