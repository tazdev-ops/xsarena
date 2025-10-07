#!/usr/bin/env python3
from __future__ import annotations

import datetime
import json
import pathlib

JOY_DIR = pathlib.Path(".xsarena") / "joy"
JOY_DIR.mkdir(parents=True, exist_ok=True)
STATE = JOY_DIR / "state.json"

DEFAULT = {"streak": 0, "last_day": None, "achievements": [], "history": []}


def _load():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            return DEFAULT.copy()
    return DEFAULT.copy()


def _save(s):
    STATE.write_text(json.dumps(s, indent=2), encoding="utf-8")


def bump_streak():
    s = _load()
    today = datetime.date.today().isoformat()
    if s["last_day"] == today:
        return s["streak"]
    # if yesterday, +1; else reset to 1
    try:
        last = datetime.date.fromisoformat(s["last_day"]) if s["last_day"] else None
    except Exception:
        last = None
    if last and (datetime.date.today() - last).days == 1:
        s["streak"] += 1
    else:
        s["streak"] = 1
    s["last_day"] = today
    _save(s)
    return s["streak"]


def add_achievement(name: str):
    s = _load()
    if name not in s["achievements"]:
        s["achievements"].append(name)
        _save(s)


def log_event(kind: str, payload: dict | None = None):
    s = _load()
    s["history"].append({"ts": datetime.datetime.utcnow().isoformat(), "type": kind, "data": payload or {}})
    _save(s)


def get_state():
    return _load()


def sparkline(days: int = 7):
    s = _load()
    today = datetime.date.today()
    marks = []
    for i in range(days - 1, -1, -1):
        day = (today - datetime.timedelta(days=i)).isoformat()
        m = (
            "█"
            if day == s.get("last_day") or any(h.get("ts", "").startswith(day) for h in s.get("history", []))
            else "·"
        )
        marks.append(m)
    return "".join(marks)
