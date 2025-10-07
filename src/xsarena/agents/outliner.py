"""Outliner agent for XSArena - creates detailed outlines for books."""

import json
from typing import Any, Dict

from .base import Agent


class OutlinerAgent(Agent):
    """Agent responsible for creating detailed outlines for books."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("outliner", config)

    async def run(self, job_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a detailed outline for the book.

        Args:
            job_id: The ID of the job to work on
            context: Context containing subject and other parameters

        Returns:
            Dictionary containing the outline artifact and suggestions
        """
        from ..core.backends import get_backend
        from ..core.engine import Engine
        from ..core.state import SessionState

        # Get the subject from context
        subject = context.get("subject", "Unknown topic")
        style = context.get("style", "comprehensive")

        # Set up the engine
        backend = get_backend(context.get("backend", "openrouter"))
        state = SessionState()
        state.continuation_mode = "normal"

        engine = Engine(backend, state)
        engine.state.job_id = job_id  # Enable cost tracking

        # Create the outline prompt
        outline_prompt = self._create_outline_prompt(subject, style)

        # Generate the outline
        outline_response = await engine.send_and_collect(outline_prompt)

        # Save the outline as an artifact
        outline_path = self.save_artifact(job_id, "outline", outline_response)

        # Parse the outline and create a structured plan
        plan_dict = self._parse_outline(outline_response, subject)
        plan_path = self.save_artifact(job_id, "plan", json.dumps(plan_dict, indent=2))

        # Write an event to the job log
        self.write_event(
            job_id,
            {
                "type": "outline_completed",
                "agent": "outliner",
                "outline_length": len(outline_response),
                "plan_sections": len(plan_dict.get("sections", [])),
            },
        )

        return {
            "artifacts": {"outline": outline_path, "plan": plan_path},
            "suggestions": {"next_agent": "writer", "plan_path": plan_path},
        }

    def _create_outline_prompt(self, subject: str, style: str) -> str:
        """Create the prompt for generating the outline."""
        style_instructions = {
            "comprehensive": "Create a comprehensive, detailed outline with multiple chapters and subtopics.",
            "concise": "Create a concise outline focusing on the essential topics.",
            "technical": "Create a technical outline with detailed subtopics and concepts.",
            "pedagogical": "Create an educational outline that builds from foundations to advanced topics.",
        }

        style_text = style_instructions.get(style, style_instructions["comprehensive"])

        return f"""{style_text}

Create a detailed outline for a comprehensive book about '{subject}'. Include chapters with their subtopics, learning objectives, and key concepts. Structure it for a step-by-step learning journey from basics to advanced topics.

Use clear headings and subheadings. For each major section, include:
- Learning objectives
- Key concepts to cover
- Prerequisites (if any)
- Applications and examples

Format the outline in markdown with clear hierarchy."""

    def _parse_outline(self, outline_text: str, subject: str) -> Dict[str, Any]:
        """Parse the outline text into a structured plan."""
        import re

        # Simple parsing - in a real implementation this would be more sophisticated
        lines = outline_text.split("\n")
        sections = []
        current_section = None

        for line in lines:
            # Check for headers of various levels
            header_match = re.match(r"^(\s*#{1,6}\s+)(.*)", line)
            if header_match:
                level = len(header_match.group(1).strip())
                title = header_match.group(2).strip()

                section = {
                    "level": level,
                    "title": title,
                    "content_hint": f"Cover the topic: {title}",
                    "completed": False,
                }

                if current_section is not None and level > current_section.get("level", 0):
                    # This is a subsection of the current section
                    if "subsections" not in current_section:
                        current_section["subsections"] = []
                    current_section["subsections"].append(section)
                else:
                    # This is a top-level section
                    sections.append(section)
                    current_section = section

        return {
            "subject": subject,
            "sections": sections,
            "total_sections": len(sections),
            "generated_at": "TODO: add timestamp",
            "completed_sections": [],
        }
