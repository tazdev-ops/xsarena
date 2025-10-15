# src/xsarena/core/config.py
import os
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

class Config(BaseModel):
    backend: str = "bridge"
    model: str = "default"
    window_size: int = 100
    anchor_length: int = 300
    continuation_mode: str = "anchor"
    repetition_threshold: float = 0.8
    max_retries: int = 3
    api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    base_url: str = "http://127.0.0.1:8080/v1" # This will be corrected by the fix command
    timeout: int = 300
    redaction_enabled: bool = False

    def save_to_file(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump()
        p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    @classmethod
    def load_from_file(cls, path: str) -> "Config":
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            return cls(**data)
        except Exception:
            return cls()
