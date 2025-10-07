"""Editor agent for XSArena - edits and improves book sections."""

import os
from typing import Any, Dict

from .base import Agent


class EditorAgent(Agent):
    """Agent responsible for editing and improving book sections."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("editor", config)

    async def run(self, job_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Edit and improve book sections.

        Args:
            job_id: The ID of the job to work on
            context: Context containing sections to edit and other parameters

        Returns:
            Dictionary containing edited sections and improvements
        """
        from ..core.backends import get_backend
        from ..core.engine import Engine
        from ..core.state import SessionState

        # Get parameters from context
        subject = context.get("subject", "Unknown topic")
        written_sections = context.get("written_sections", [])
        style = context.get("style", "comprehensive")

        # Set up the engine
        backend = get_backend(context.get("backend", "openrouter"))
        state = SessionState()
        state.continuation_mode = "normal"  # No continuation needed for editing

        engine = Engine(backend, state)
        engine.state.job_id = job_id  # Enable cost tracking

        edited_sections = {}

        # Process each written section
        for i, section_path in enumerate(written_sections):
            # Load the original section
            with open(section_path, "r", encoding="utf-8") as f:
                original_content = f.read()

            # Create the editing prompt
            editing_prompt = self._create_editing_prompt(subject, original_content, style)

            # Generate the edited version
            edited_content = await engine.send_and_collect(editing_prompt)

            # Save the edited section
            edited_filename = section_path.replace(".txt", "_edited.txt")
            with open(edited_filename, "w", encoding="utf-8") as f:
                f.write(edited_content)

            edited_sections[f"edited_section_{i + 1}"] = edited_filename

            # Write an event to the job log
            self.write_event(
                job_id,
                {
                    "type": "section_edited",
                    "agent": "editor",
                    "original_section": os.path.basename(section_path),
                    "edited_section": os.path.basename(edited_filename),
                    "original_length": len(original_content),
                    "edited_length": len(edited_content),
                },
            )

        return {
            "artifacts": edited_sections,
            "suggestions": {"next_agent": "continuity", "edited_sections": list(edited_sections.values())},
        }

    def _create_editing_prompt(self, subject: str, content: str, style: str) -> str:
        """Create the prompt for editing content."""
        style_instructions = {
            "clarity": "Focus on improving clarity, simplifying complex concepts, and making explanations clearer.",
            "consistency": "Focus on consistency in terminology, style, and formatting throughout the text.",
            "pedagogy": "Enhance pedagogical elements: add explanations before use of concepts, examples, and quick checks.",
            "conciseness": "Make the text more concise by removing redundancy while preserving important information.",
        }

        style_text = style_instructions.get(style, "Improve the text for clarity, consistency, and readability.")

        return f"""{style_text}

Edit the following content from a book about '{subject}'. Improve it while preserving the core information and meaning.

Requirements:
- Maintain factual accuracy
- Improve clarity and readability
- Ensure consistent terminology
- Fix grammar and style issues
- Preserve important technical details

Current content:
{content}

Edited content:"""
