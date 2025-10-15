from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
import json
import os

from ..core.backends import create_backend
from ..core.config import Config
from ..core.engine import Engine
from ..core.redact import redact
from ..core.state import SessionState


@dataclass
class CLIContext:
    config: Config
    state: SessionState
    engine: Engine
    state_path: Path

    @classmethod
    def load(cls, cfg: Optional[Config] = None, state_path: Optional[str] = None) -> "CLIContext":
        cfg = cfg or Config()
        state_path = Path(state_path or "./.xsarena/session_state.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)

        # self-heal: if state file is corrupt, move aside and start fresh
        state = SessionState()
        if state_path.exists():
            try:
                state = SessionState.load_from_file(str(state_path))
            except Exception:
                bak = state_path.with_suffix(".bak")
                # don't overwrite existing bak
                bak = bak if not bak.exists() else state_path.with_name(state_path.stem + ".bak1")
                try:
                    state_path.rename(bak)
                except Exception:
                    pass
                state = SessionState()

        # ensure backend + model from cfg override
        state.backend = cfg.backend or state.backend
        state.model = cfg.model or state.model
        state.window_size = cfg.window_size or state.window_size

        # ensure base_url ends with /v1
        if cfg.base_url and not cfg.base_url.rstrip("/").endswith("/v1"):
            cfg.base_url = cfg.base_url.rstrip("/") + "/v1"

        # build engine
        backend = create_backend(
            state.backend,
            base_url=os.getenv("XSA_BRIDGE_URL", cfg.base_url),
            api_key=cfg.api_key,
            model=state.model,
        )
        eng = Engine(backend, state)

        # Reapply redaction filter if enabled
        if state.settings.get("redaction_enabled"):
            eng.set_redaction_filter(redact)

        return cls(config=cfg, state=state, engine=eng, state_path=state_path)

    def rebuild_engine(self):
        # self-heal base_url shape
        if self.config.base_url and not self.config.base_url.rstrip("/").endswith("/v1"):
            self.config.base_url = self.config.base_url.rstrip("/") + "/v1"

        self.engine = Engine(
            create_backend(
                self.state.backend,
                base_url=os.getenv("XSA_BRIDGE_URL", self.config.base_url),
                api_key=self.config.api_key,
                model=self.state.model,
            ),
            self.state,
        )

        # Reapply redaction filter if enabled
        if self.state.settings.get("redaction_enabled"):
            self.engine.set_redaction_filter(redact)


    def save(self):
        self.state.save_to_file(str(self.state_path))

    def fix(self) -> list[str]:
        """Attempt self-fixes: base_url shape, backend validity, engine rebuild."""
        notes: list[str] = []
        # normalize base_url
        if self.config.base_url and not self.config.base_url.rstrip("/").endswith("/v1"):
            self.config.base_url = self.config.base_url.rstrip("/") + "/v1"
            notes.append("Normalized base_url to end with /v1")

        # fallback backend if invalid
        if self.state.backend not in ("bridge", "openrouter", "lmarena", "lmarena-ws"):
            self.state.backend = "bridge"
            notes.append("Backend invalid; set to bridge")

        # default base_url if empty
        if not self.config.base_url:
            self.config.base_url = "http://127.0.0.1:8080/v1"
            notes.append("Set default bridge base_url http://127.0.0.1:8080/v1")

        self.rebuild_engine()
        self.save()
        if not notes:
            notes.append("No changes; config/state already consistent")
        return notes