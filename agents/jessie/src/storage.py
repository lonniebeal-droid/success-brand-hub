import json
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


class StorageError(RuntimeError):
    """Raised when storage operations fail in a safe, explicit way."""


class StorageAdapter(Protocol):
    def load_records(self) -> List[Dict[str, Any]]: ...

    def write_records(self, records: List[Dict[str, Any]]) -> None: ...

    def create_record(self, record: Dict[str, Any]) -> Dict[str, Any]: ...

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]: ...

    def list_records(self) -> List[Dict[str, Any]]: ...

    def update_record(self, record_id: str, updates: Dict[str, Any]) -> Dict[str, Any]: ...


class BaseStorageAdapter(ABC):
    def __init__(self) -> None:
        self._records: List[Dict[str, Any]] = []

    def load_records(self) -> List[Dict[str, Any]]:
        return list(self._records)

    def write_records(self, records: List[Dict[str, Any]]) -> None:
        self._records = [dict(record) for record in records]

    def create_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        if self._has_duplicate_id(record.get("id")):
            raise StorageError("duplicate record id")
        self._records.append(dict(record))
        return dict(record)

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        for record in self._records:
            if record.get("id") == record_id:
                return dict(record)
        return None

    def list_records(self) -> List[Dict[str, Any]]:
        return [dict(record) for record in self._records]

    def update_record(self, record_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        for record in self._records:
            if record.get("id") == record_id:
                record.update(updates)
                return dict(record)
        raise StorageError("record not found")

    def _has_duplicate_id(self, record_id: Optional[str]) -> bool:
        return any(record.get("id") == record_id for record in self._records)


class InMemoryStorage(BaseStorageAdapter):
    """In-memory storage that is isolated per test instance."""


class LocalJSONStorage(BaseStorageAdapter):
    def __init__(self, path: str | os.PathLike[str], backup_before_overwrite: bool = True) -> None:
        super().__init__()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_before_overwrite = backup_before_overwrite
        self._load_from_disk()

    def create_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        if self._has_duplicate_id(record.get("id")):
            raise StorageError("duplicate record id")
        self._records.append(dict(record))
        self._write_atomic(self._records)
        return dict(record)

    def _load_from_disk(self) -> None:
        if not self.path.exists():
            self._records = []
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StorageError("corrupted storage file") from exc
        if not isinstance(payload, list):
            raise StorageError("storage payload must be a list")
        self._records = [dict(record) for record in payload]

    def write_records(self, records: List[Dict[str, Any]]) -> None:
        self._write_atomic(records)
        self._records = [dict(record) for record in records]

    def _write_atomic(self, records: List[Dict[str, Any]]) -> None:
        if self.backup_before_overwrite and self.path.exists():
            backup_path = self.path.with_suffix(self.path.suffix + ".bak")
            backup_path.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(self.path.parent), delete=False) as handle:
            json.dump(records, handle, indent=2)
            temp_path = Path(handle.name)
        os.replace(temp_path, self.path)


class DatabaseStorage(BaseStorageAdapter):
    """Placeholder for future database-backed storage."""

    def __init__(self) -> None:
        super().__init__()
        raise NotImplementedError("database storage is not implemented in this sandbox build")
