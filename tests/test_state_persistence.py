"""Tests for state persistence functionality."""

import os
import tempfile

from xsarena.cli.context import CLIContext
from xsarena.core.config import Config
from xsarena.core.state import SessionState


def test_session_state_save_load():
    """Test saving and loading session state."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        filepath = f.name

    try:
        # Create a state with some data
        state = SessionState()
        state.history = [{"role": "user", "content": "test message"}]
        state.anchors = ["anchor1", "anchor2"]
        state.backend = "test_backend"
        state.model = "test_model"
        state.settings = {"test_setting": True}

        # Save the state
        state.save_to_file(filepath)

        # Load it back
        loaded_state = SessionState.load_from_file(filepath)

        # Verify the data was preserved
        assert loaded_state.backend == "test_backend"
        assert loaded_state.model == "test_model"
        assert loaded_state.settings["test_setting"] is True
        assert len(loaded_state.history) == 1
        assert len(loaded_state.anchors) == 2

    finally:
        # Clean up
        if os.path.exists(filepath):
            os.unlink(filepath)


def test_cli_context_settings_persistence():
    """Test CLI context settings persistence."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        filepath = f.name

    try:
        # Create a config and initial state
        config = Config()
        context = CLIContext.load(cfg=config, state_path=filepath)

        # Modify settings
        context.state.settings["test_key"] = "test_value"
        context.state.backend = "test_backend"
        context.state.model = "test_model"

        # Save the context
        context.save()

        # Reload the context
        reloaded_context = CLIContext.load(cfg=config, state_path=filepath)

        # Verify settings were preserved
        assert reloaded_context.state.settings["test_key"] == "test_value"
        assert reloaded_context.state.backend == "test_backend"
        assert reloaded_context.state.model == "test_model"

    finally:
        # Clean up
        if os.path.exists(filepath):
            os.unlink(filepath)
