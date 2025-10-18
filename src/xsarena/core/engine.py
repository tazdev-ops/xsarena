"""New engine implementation for XSArena using the v3 architecture."""

from typing import Callable, Optional

from .backends.transport import BackendTransport
from .state import SessionState
from .v2_orchestrator.orchestrator import Orchestrator


class Engine:
    """New engine that uses the v3 orchestrator architecture."""

    def __init__(self, backend: BackendTransport, state: SessionState):
        self.backend = backend
        self.state = state
        self.orchestrator = Orchestrator(transport=backend)
        self.redaction_filter: Optional[Callable[[str], str]] = None

    async def send_and_collect(
        self, user_prompt: str, system_prompt: Optional[str] = None
    ) -> str:
        """Send a message and collect the response."""
        # Prepare the payload
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "messages": messages,
            "model": getattr(self.state, "model", "default"),
        }

        # Send using the backend transport
        response = await self.backend.send(payload)

        # Extract the content from the response
        choices = response.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            # Apply redaction filter if set
            if self.redaction_filter:
                content = self.redaction_filter(content)
            return content
        else:
            return "No response from backend"

    async def send(self, user_prompt: str, system_prompt: Optional[str] = None):
        """Send a message (async generator for streaming if needed)."""
        return await self.send_and_collect(user_prompt, system_prompt)

    def set_redaction_filter(self, filter_func: Optional[Callable[[str], str]]):
        """Set a redaction filter function."""
        self.redaction_filter = filter_func

    async def autopilot_run(
        self, initial_prompt: str, max_chunks: Optional[int] = None
    ):
        """Run autopilot functionality."""
        # Do not implement a duplicate FSM. Instead, document that autopilot is handled by JobManager
        raise NotImplementedError(
            "Use xsarena run book/continue or interactive cockpit for autopilot functionality"
        )

    async def build_anchor_continue_prompt(self, anchor: str) -> str:
        """Build a continuation prompt based on an anchor."""
        # This would be implemented based on the specific requirements
        return f"Continue writing from this point: {anchor}"
