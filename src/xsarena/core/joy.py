"""Joy module stubs with file persistence."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def _get_state_file() -> Path:
    """Get the path to the joy state file."""
    state_dir = Path(".xsarena/joy")
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "state.json"


def get_state() -> Dict[str, Any]:
    """Get the current joy state."""
    state_file = _get_state_file()
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass  # If file is corrupted, return default state

    # Return default state
    return {"streak": 0, "last_day": None, "achievements": [], "events": []}


def _save_state(state: Dict[str, Any]) -> None:
    """Save the joy state to file."""
    state_file = _get_state_file()
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def bump_streak() -> int:
    """Increment the streak counter."""
    state = get_state()

    # Check if it's a new day
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_day") != today:
        state["streak"] += 1
        state["last_day"] = today
    else:
        # If it's the same day, don't increment but return current streak
        pass

    _save_state(state)
    return state["streak"]


def add_achievement(title: str) -> None:
    """Add an achievement to the state."""
    state = get_state()

    if title not in state["achievements"]:
        state["achievements"].append(title)
        _save_state(state)


def log_event(event_type: str, data: Dict[str, Any]) -> None:
    """Log an event."""
    state = get_state()

    event = {"type": event_type, "data": data, "timestamp": datetime.now().isoformat()}

    state["events"].append(event)

    # Keep only the last 100 events to prevent the file from growing too large
    if len(state["events"]) > 100:
        state["events"] = state["events"][-100:]

    _save_state(state)


def sparkline(days: int = 7) -> str:
    """Generate a simple sparkline for the last N days."""
    # For the stub, we'll just return a simple representation
    # In a real implementation, this would track daily activity
    state = get_state()
    streak = state.get("streak", 0)

    # Simple representation: filled circles for streak days, empty for others
    filled = min(streak, days)
    empty = max(0, days - filled)

    return "●" * filled + "○" * empty
