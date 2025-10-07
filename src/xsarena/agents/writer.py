"""Writer agent for XSArena - writes book sections based on plan."""

import json
import os
from typing import Any, Dict

from .base import Agent


class WriterAgent(Agent):
    """Agent responsible for writing book sections based on a plan."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("writer", config)

    async def run(self, job_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Write book sections based on the plan.

        Args:
            job_id: The ID of the job to work on
            context: Context containing plan, subject, and other parameters

        Returns:
            Dictionary containing written sections and progress
        """
        from ..core.backends import get_backend
        from ..core.engine import Engine
        from ..core.state import SessionState

        # Get parameters from context
        subject = context.get("subject", "Unknown topic")
        plan_path = context.get("plan_path")
        max_chunks = context.get("max_chunks", 8)
        style = context.get("style", "comprehensive")

        # Load the plan if path is provided
        plan_dict = None
        if plan_path and os.path.exists(plan_path):
            with open(plan_path, "r", encoding="utf-8") as f:
                plan_dict = json.load(f)
        else:
            # Try to load from job artifacts
            plan_content = self.load_artifact(job_id, "plan")
            if plan_content:
                plan_dict = json.loads(plan_content)

        # Set up the engine
        backend = get_backend(context.get("backend", "openrouter"))
        state = SessionState()
        state.continuation_mode = "anchor"  # Use anchor continuation for coherent writing
        state.anchor_length = context.get("anchor_length", 200)

        engine = Engine(backend, state)
        engine.state.job_id = job_id  # Enable cost tracking

        written_sections = {}
        section_count = 0

        # If we have a plan, write sections according to it
        if plan_dict and "sections" in plan_dict:
            for section in plan_dict["sections"]:
                if section_count >= max_chunks:
                    break

                section_title = section.get("title", f"Section {section_count + 1}")
                content_hint = section.get("content_hint", f"Write about {section_title}")

                # Create the writing prompt
                writing_prompt = self._create_writing_prompt(subject, section_title, content_hint, style)

                # Generate the section content
                section_content = await engine.send_and_collect(writing_prompt)

                # Save the section as an artifact
                section_filename = f"section_{section_count + 1:03d}_{section_title.replace(' ', '_')[:50]}"
                section_path = self.save_artifact(job_id, section_filename, section_content)

                written_sections[f"section_{section_count + 1}"] = section_path

                # Update progress in the plan
                plan_dict["completed_sections"] = plan_dict.get("completed_sections", []) + [section_count + 1]

                # Write an event to the job log
                self.write_event(
                    job_id,
                    {
                        "type": "section_written",
                        "agent": "writer",
                        "section": section_count + 1,
                        "title": section_title,
                        "length": len(section_content),
                    },
                )

                section_count += 1

        # If no plan or we still need more content, write additional sections
        while section_count < max_chunks:
            section_title = f"Additional Content {section_count + 1}"
            content_hint = f"Continue the book about {subject}, adding important information not covered yet"

            writing_prompt = self._create_writing_prompt(subject, section_title, content_hint, style)
            section_content = await engine.send_and_collect(writing_prompt)

            section_filename = f"section_{section_count + 1:03d}_additional"
            section_path = self.save_artifact(job_id, section_filename, section_content)

            written_sections[f"section_{section_count + 1}"] = section_path

            # Write an event to the job log
            self.write_event(
                job_id,
                {
                    "type": "section_written",
                    "agent": "writer",
                    "section": section_count + 1,
                    "title": section_title,
                    "length": len(section_content),
                },
            )

            section_count += 1

        # Update and save the plan
        if plan_dict:
            plan_path = self.save_artifact(job_id, "plan", json.dumps(plan_dict, indent=2))

        return {
            "artifacts": written_sections,
            "suggestions": {
                "next_agent": "editor",
                "written_sections": list(written_sections.values()),
                "plan_path": plan_path if plan_dict else None,
            },
        }

    def _create_writing_prompt(self, subject: str, section_title: str, content_hint: str, style: str) -> str:
        """Create the prompt for writing a section."""
        style_instructions = {
            "comprehensive": "Write a comprehensive, detailed section with examples, explanations, and practical applications.",
            "concise": "Write a clear, concise section focusing on key points and essentials.",
            "technical": "Write with technical precision, including definitions, formulas, and detailed explanations.",
            "pedagogical": "Write in a teaching style with explanations before use of concepts, examples, and quick checks.",
        }

        style_text = style_instructions.get(style, style_instructions["comprehensive"])

        return f"""{style_text}

Write the section titled "{section_title}" for a book about "{subject}".

Content guidance: {content_hint}

Requirements:
- Use clear headings and subheadings
- Include examples where appropriate
- Make it educational and informative
- Ensure it flows well with previous sections
- End with a NEXT: instruction for the continuation

Content:"""
