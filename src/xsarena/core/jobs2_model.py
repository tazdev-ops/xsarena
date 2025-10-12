from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict


@dataclass
class Job:
    id: str
    name: str
    playbook: Dict[str, Any]
    params: Dict[str, Any]
    backend: str
    state: str = "PENDING"  # PENDING/RUNNING/STALLED/RETRYING/DONE/FAILED/CANCELLED
    retries: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    artifacts: Dict[str, str] = field(
        default_factory=dict
    )  # "outline": path, "plan": path, ...
    meta: Dict[str, Any] = field(default_factory=dict)
