# src/xsarena/core/state.py
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SessionState:
    history: List[Message] = field(default_factory=list)
    anchors: List[str] = field(default_factory=list)
    continuation_mode: str = "anchor"
    anchor_length: int = 300
    repetition_threshold: float = 0.35
    repetition_ngram: int = 4
    repetition_warn: bool = True
    backend: str = "bridge"
    model: str = "default"
    window_size: int = 100
    settings: Dict = field(default_factory=dict)
    session_mode: Optional[str] = None
    coverage_hammer_on: bool = True
    output_budget_snippet_on: bool = True
    output_push_on: bool = True
    output_min_chars: int = 3000
    output_push_max_passes: int = 3
    # New persisted toggles
    smart_min_enabled: bool = False
    outline_first_enabled: bool = False
    semantic_anchor_enabled: bool = False
    reading_overlay_on: bool = False
    # Prompt configuration (make defaults explicit and persisted)
    active_profile: Optional[str] = None
    overlays_active: List[str] = field(default_factory=list)

    def add_message(self, role: str, content: str):
        self.history.append(Message(role=role, content=content))

    def add_anchor(self, text: str):
        self.anchors.append(text[-self.anchor_length :])

    def to_dict(self) -> dict:
        history_data = []
        for m in self.history:
            if isinstance(m, Message):
                # It's a Message object
                history_data.append(
                    {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.timestamp.isoformat(),
                    }
                )
            elif isinstance(m, dict):
                # It's already a dict, use it as-is
                history_data.append(m)

        return {
            "history": history_data,
            "anchors": self.anchors,
            "continuation_mode": self.continuation_mode,
            "anchor_length": self.anchor_length,
            "repetition_threshold": self.repetition_threshold,
            "repetition_ngram": self.repetition_ngram,
            "repetition_warn": self.repetition_warn,
            "backend": self.backend,
            "model": self.model,
            "window_size": self.window_size,
            "settings": self.settings,
            "session_mode": self.session_mode,
            "coverage_hammer_on": self.coverage_hammer_on,
            "output_budget_snippet_on": self.output_budget_snippet_on,
            "output_push_on": self.output_push_on,
            "output_min_chars": self.output_min_chars,
            "output_push_max_passes": self.output_push_max_passes,
            "smart_min_enabled": self.smart_min_enabled,
            "outline_first_enabled": self.outline_first_enabled,
            "semantic_anchor_enabled": self.semantic_anchor_enabled,
            "active_profile": self.active_profile,
            "overlays_active": self.overlays_active,
        }

    def save_to_file(self, filepath: str):
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> "SessionState":
        if not os.path.exists(filepath):
            return cls()
        with open(filepath, "r") as f:
            state_dict = json.load(f)

        history = []
        for m in state_dict.get("history", []):
            if "timestamp" in m:
                timestamp = datetime.fromisoformat(m["timestamp"])
            else:
                timestamp = datetime.now()  # Default to now if no timestamp
            history.append(
                Message(
                    role=m["role"],
                    content=m["content"],
                    timestamp=timestamp,
                )
            )
        state_dict["history"] = history

        # Filter out keys that are not in the dataclass definition
        known_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in state_dict.items() if k in known_keys}

        return cls(**filtered_dict)
