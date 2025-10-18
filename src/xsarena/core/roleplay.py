"""Roleplay module stubs with file persistence."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class Rating(Enum):
    SFW = "sfw"
    NSFW = "nsfw"


@dataclass
class Boundaries:
    rating: str = "sfw"
    safeword: str = "PAUSE"


@dataclass
class RoleplaySession:
    id: str
    name: str
    persona: str
    system_overlay: str
    backend: str = "openrouter"
    model: Optional[str] = None
    boundaries: Boundaries = None
    memory: List[str] = None
    turns: List[Dict[str, str]] = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if self.boundaries is None:
            self.boundaries = Boundaries()
        if self.memory is None:
            self.memory = []
        if self.turns is None:
            self.turns = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()


def _get_sessions_dir() -> Path:
    """Get the path to the roleplay sessions directory."""
    sessions_dir = Path(".xsarena/roleplay/sessions")
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def _session_file_path(session_id: str) -> Path:
    """Get the path to a specific session file."""
    return _get_sessions_dir() / f"{session_id}.json"


def new_session(
    name: str,
    persona: str,
    overlay: str,
    backend: str = "openrouter",
    model: Optional[str] = None,
    rating: str = "sfw",
    safeword: str = "PAUSE",
) -> RoleplaySession:
    """Create a new roleplay session."""
    import uuid

    session_id = str(uuid.uuid4())
    session = RoleplaySession(
        id=session_id,
        name=name,
        persona=persona,
        system_overlay=overlay,
        backend=backend,
        model=model,
        boundaries=Boundaries(rating=rating, safeword=safeword),
    )

    save_session(session)
    return session


def load_session(session_id: str) -> RoleplaySession:
    """Load a roleplay session by ID."""
    session_file = _session_file_path(session_id)
    if not session_file.exists():
        raise ValueError(f"Session {session_id} not found")

    try:
        with open(session_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle backwards compatibility for boundaries
        boundaries_data = data.get("boundaries", {})
        if isinstance(boundaries_data, dict):
            boundaries = Boundaries(
                rating=boundaries_data.get("rating", "sfw"),
                safeword=boundaries_data.get("safeword", "PAUSE"),
            )
        else:
            boundaries = Boundaries()

        # Create the session object
        session = RoleplaySession(
            id=data["id"],
            name=data["name"],
            persona=data["persona"],
            system_overlay=data["system_overlay"],
            backend=data.get("backend", "openrouter"),
            model=data.get("model"),
            boundaries=boundaries,
            memory=data.get("memory", []),
            turns=data.get("turns", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

        return session
    except Exception as e:
        raise ValueError(f"Failed to load session {session_id}: {e}")


def save_session(session: RoleplaySession) -> None:
    """Save a roleplay session."""
    session.updated_at = datetime.now().isoformat()
    session_file = _session_file_path(session.id)

    # Convert session to dictionary, handling the boundaries properly
    session_dict = asdict(session)
    session_dict["boundaries"] = asdict(session.boundaries)

    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(session_dict, f, indent=2)


def append_turn(session_id: str, role: str, content: str) -> None:
    """Append a turn to a session."""
    session = load_session(session_id)
    session.turns.append(
        {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
    )
    save_session(session)


def export_markdown(session_id: str) -> Optional[str]:
    """Export a session to markdown format."""
    try:
        session = load_session(session_id)
        output_path = _get_sessions_dir() / f"{session.name.replace(' ', '_')}.md"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Roleplay Session: {session.name}\n\n")
            f.write(f"**Persona**: {session.persona}\n")
            f.write(f"**Backend**: {session.backend}\n")
            f.write(f"**Model**: {session.model or 'default'}\n")
            f.write(f"**Created**: {session.created_at}\n\n")

            if session.memory:
                f.write("## Memory\n")
                for i, mem in enumerate(session.memory, 1):
                    f.write(f"{i}. {mem}\n")
                f.write("\n")

            f.write("## Transcript\n\n")
            for turn in session.turns:
                role = turn["role"].upper()
                content = turn["content"]
                f.write(f"**{role}**: {content}\n\n")

        return str(output_path)
    except Exception:
        return None


def redact_boundary_violations(boundaries: Boundaries, text: str) -> str:
    """Redact boundary violations from text (stub implementation)."""
    # For the stub, just return the text as is
    # In a real implementation, this would check for violations
    return text
