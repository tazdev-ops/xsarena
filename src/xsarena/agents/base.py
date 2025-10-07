"""Base agent class for XSArena multi-agent system."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Agent(ABC):
    """Base class for all agents in the multi-agent system."""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    async def run(self, job_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the agent on a job with the given context.

        Args:
            job_id: The ID of the job to work on
            context: Contextual information for the agent

        Returns:
            Dictionary containing artifacts and suggestions
        """
        pass

    def write_event(self, job_id: str, event: Dict[str, Any]) -> None:
        """Write an event to the job's event log."""
        from ..core.metrics import write_event

        write_event(job_id, event)

    def load_artifact(self, job_id: str, artifact_name: str) -> Optional[str]:
        """Load an artifact from the job directory."""
        import os

        job_dir = os.path.join(".xsarena", "jobs", job_id)
        artifact_path = os.path.join(job_dir, f"{artifact_name}.txt")

        if os.path.exists(artifact_path):
            with open(artifact_path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    def save_artifact(self, job_id: str, artifact_name: str, content: str) -> str:
        """Save an artifact to the job directory."""
        import os

        job_dir = os.path.join(".xsarena", "jobs", job_id)
        artifact_path = os.path.join(job_dir, f"{artifact_name}.txt")

        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(content)

        return artifact_path
