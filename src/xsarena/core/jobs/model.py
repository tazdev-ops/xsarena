"""Job model for XSArena v0.3."""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel

from ..v2_orchestrator.specs import RunSpecV2


class JobV3(BaseModel):
    """Version 3 job model with typed fields."""

    id: str
    name: str
    run_spec: RunSpecV2
    backend: str
    state: str = "PENDING"  # PENDING/RUNNING/STALLED/RETRYING/DONE/FAILED/CANCELLED
    retries: int = 0
    created_at: str = datetime.now().isoformat()
    updated_at: str = datetime.now().isoformat()
    artifacts: Dict[str, str] = {}
    meta: Dict[str, Any] = {}
    progress: Dict[str, Any] = {}  # Track progress like chunks completed, tokens used


# Re-export for backward compatibility
def __getattr__(name):
    if name == "JobManager":
        from .manager import JobManager

        return JobManager
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
