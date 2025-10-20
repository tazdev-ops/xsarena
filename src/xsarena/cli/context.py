from __future__ import annotations

import contextlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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
    def load(  # noqa: C901
        cls, cfg: Optional[Config] = None, state_path: Optional[str] = None
    ) -> "CLIContext":
        """
        Load CLI context with clear order of precedence:
        1. Start with hardcoded SessionState() defaults
        2. Load .xsarena/config.yml (project-level defaults)
        3. Load .xsarena/session_state.json (user's last-used
           interactive settings) - OVERRIDES config
        4. Apply CLI flags from cfg object (explicit, one-time
           overrides) - HIGHEST priority
        """
        # Start with hardcoded defaults
        session_state = SessionState()

        # Set up state path
        state_path = Path(state_path or "./.xsarena/session_state.json")
        state_path.parent.mkdir(parents=True, exist_ok=True)

        # 2. Load .xsarena/config.yml (project-level defaults) FIRST
        config_path = Path(".xsarena/config.yml")
        if config_path.exists():
            import yaml

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_content = yaml.safe_load(f) or {}
                persisted_settings = config_content.get("settings", {})

                # Apply config.yml settings, overriding defaults
                for key, value in persisted_settings.items():
                    if hasattr(session_state, key):
                        setattr(session_state, key, value)
            except Exception:
                pass  # If config can't be read, continue with defaults

        # 3. Load .xsarena/session_state.json (user's last-used settings) SECOND - OVERRIDES config
        if state_path.exists():
            try:
                file_session_state = SessionState.load_from_file(str(state_path))
                # Apply ALL session_state values, OVERRIDING config.yml settings
                for field_name in file_session_state.__dict__:
                    if hasattr(session_state, field_name):
                        setattr(
                            session_state,
                            field_name,
                            getattr(file_session_state, field_name),
                        )
            except Exception:
                # Create backup and continue with current state if corrupted
                bak = state_path.with_suffix(f".{int(time.time())}.bak")
                with contextlib.suppress(Exception):
                    state_path.rename(bak)
                # Continue with current state if session file is corrupted

        # Load base configuration for backend settings (config.yml is single source of truth)
        base_cfg = Config.load_from_file(".xsarena/config.yml")

        # 4. Apply CLI flags from cfg object (explicit, one-time overrides)
        # This is the highest priority - CLI flags override everything else including config.yml
        if cfg is not None:
            # Only apply non-default values from CLI to avoid overriding user choices with defaults
            if cfg.backend != "bridge":
                session_state.backend = cfg.backend
            if cfg.model != "default":
                session_state.model = cfg.model
            if cfg.window_size != 100:
                session_state.window_size = cfg.window_size
            if cfg.continuation_mode != "anchor":
                session_state.continuation_mode = cfg.continuation_mode
            if cfg.anchor_length != 300:
                session_state.anchor_length = cfg.anchor_length
            if cfg.repetition_threshold != 0.35:
                session_state.repetition_threshold = cfg.repetition_threshold

        # Base URL normalization is handled by Config model validators only

        # Build engine using the final state
        backend = create_backend(
            session_state.backend,
            base_url=os.getenv("XSA_BRIDGE_URL", base_cfg.base_url),
            api_key=base_cfg.api_key,
            model=session_state.model,
        )
        eng = Engine(backend, session_state)
        if session_state.settings.get("redaction_enabled"):
            eng.set_redaction_filter(redact)
        return cls(
            config=base_cfg, state=session_state, engine=eng, state_path=state_path
        )

    def rebuild_engine(self):
        # Base URL normalization handled centrally in Config model validators

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
        # base_url normalization removed (Config validators are the source of truth)

        # fallback backend if invalid
        if self.state.backend not in ("bridge", "openrouter", "lmarena", "lmarena-ws"):
            self.state.backend = "bridge"
            notes.append("Backend invalid; set to bridge")

        # default base_url if empty
        if not self.config.base_url:
            self.config.base_url = "http://127.0.0.1:5102/v1"
            notes.append("Set default bridge base_url http://127.0.0.1:5102/v1")

        self.rebuild_engine()
        self.save()
        if not notes:
            notes.append("No changes; config/state already consistent")
        return notes
