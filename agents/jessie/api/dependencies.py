from functools import lru_cache
from pathlib import Path
from typing import Optional

from agents.jessie.src.intake_service import IntakeService


@lru_cache(maxsize=1)
def get_service(data_file: Optional[str] = None) -> IntakeService:
    resolved_path = Path(data_file or "agents/jessie/data/intakes.json")
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return IntakeService(data_file=str(resolved_path))
