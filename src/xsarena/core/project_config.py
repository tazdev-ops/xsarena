"""Project configuration for XSArena with concurrency settings."""

from pathlib import Path

import yaml
from pydantic import BaseModel


class ConcurrencySettings(BaseModel):
    """Concurrency settings for different backend types."""

    total: int = 4  # Total concurrent jobs
    bridge: int = 2  # Concurrent bridge jobs
    openrouter: int = 1  # Concurrent OpenRouter jobs
    quiet_hours: bool = False  # Whether to honor quiet hours


class ProjectSettings(BaseModel):
    """Project-level settings for XSArena."""

    concurrency: ConcurrencySettings = ConcurrencySettings()

    def save_to_file(self, path: str) -> None:
        """Save settings to a YAML file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump()
        p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    @classmethod
    def load_from_file(cls, path: str) -> "ProjectSettings":
        """Load settings from a YAML file."""
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            return cls(**data)
        except Exception:
            return cls()


def get_project_settings() -> ProjectSettings:
    """Get project settings from the default location."""
    settings_path = Path(".xsarena/project.yml")
    return ProjectSettings.load_from_file(str(settings_path))
