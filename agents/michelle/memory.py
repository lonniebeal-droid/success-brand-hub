import json
from pathlib import Path


class MemoryStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.data = {"tasks": [], "activity_log": []}
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
