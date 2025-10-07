#!/usr/bin/env python3
from __future__ import annotations

import datetime
import json
import pathlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

RP_DIR = pathlib.Path(".xsarena") / "rp"
RP_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class RPBoundaries:
    rating: str = "sfw"  # sfw | pg13
    safeword: str = "PAUSE"  # user can change
    disallow: list[str] = None  # extra disallow keywords

    def __post_init__(self):
        if self.disallow is None:
            self.disallow = ["graphic sexual content", "minors", "illegal instructions", "doxxing", "hate speech"]


@dataclass
class RPSession:
    id: str
    name: str
    persona: str
    system_overlay: str
    model: Optional[str] = None  # e.g. "openrouter/auto" or "openrouter/your-uncensored-model"
    backend: str = "openrouter"  # "openrouter" | "bridge" | "ollama"
    boundaries: RPBoundaries = field(default_factory=RPBoundaries)
    created_at: str = ""
    updated_at: str = ""
    turns: list[Dict[str, Any]] = field(
        default_factory=list
    )  # [{"role":"user"|"assistant", "content": "...", "ts": "..."}]
    memory: list[str] = field(default_factory=list)  # short "facts" for persona continuity

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


def _now():
    return datetime.datetime.utcnow().isoformat()


def _rp_path(sess_id: str) -> pathlib.Path:
    return RP_DIR / sess_id


def new_session(
    name: str,
    persona: str,
    overlay: str,
    backend: str = "openrouter",
    model: Optional[str] = None,
    rating: str = "sfw",
    safeword: str = "PAUSE",
) -> RPSession:
    sess_id = f"rp_{int(datetime.datetime.utcnow().timestamp())}"
    path = _rp_path(sess_id)
    path.mkdir(parents=True, exist_ok=True)
    s = RPSession(
        id=sess_id,
        name=name,
        persona=persona,
        system_overlay=overlay,
        backend=backend,
        model=model,
        boundaries=RPBoundaries(rating=rating, safeword=safeword),
        created_at=_now(),
        updated_at=_now(),
    )
    save_session(s)
    return s


def load_session(sess_id: str) -> RPSession:
    j = json.loads((_rp_path(sess_id) / "session.json").read_text(encoding="utf-8"))
    b = j.get("boundaries", {})
    j["boundaries"] = RPBoundaries(**b)
    j["turns"] = j.get("turns", [])
    j["memory"] = j.get("memory", [])
    return RPSession(**j)


def save_session(s: RPSession):
    s.updated_at = _now()
    j = asdict(s)
    # dataclass boundaries to dict
    j["boundaries"] = asdict(s.boundaries)
    (_rp_path(s.id) / "session.json").write_text(json.dumps(j, indent=2), encoding="utf-8")


def append_turn(sess_id: str, role: str, content: str):
    s = load_session(sess_id)
    s.turns.append({"role": role, "content": content, "ts": _now()})
    save_session(s)
    # also append to transcript file
    with (_rp_path(sess_id) / "transcript.md").open("a", encoding="utf-8") as f:
        f.write(f"\n\n[{role.upper()} {datetime.datetime.utcnow().isoformat()}]\n{content}\n")


def redact_boundary_violations(boundaries: RPBoundaries, text: str) -> str:
    # very light guard: replace disallowed keywords with [redacted]
    out = text
    for w in boundaries.disallow or []:
        out = re.sub(w, "[redacted]", out, flags=re.IGNORECASE)
    return out


def export_markdown(sess_id: str) -> pathlib.Path:
    p = _rp_path(sess_id) / "transcript.md"
    return p if p.exists() else None
