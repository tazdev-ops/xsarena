"""Lossless processing modes for XSArena."""

from typing import Optional

from ..core.engine import Engine
from ..core.prompt import pcl


class LosslessMode:
    """Handles lossless text processing functionality."""

    def __init__(self, engine: Engine):
        self.engine = engine

    async def ingest_synth(self, text: str, extra_notes: Optional[str] = None) -> str:
        """Ingest and synthesize information from text."""
        prompt = f"""Please analyze and synthesize this text, extracting key concepts, facts, and insights:

{text}

Provide a synthesized summary that captures the essential information in a structured format."""

        # Build system prompt using PCL with lossless role directive
        role_content = self._load_role_directive("lossless")
        system_prompt = self._build_system_prompt(
            "text synthesis", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def rewrite_lossless(
        self, text: str, extra_notes: Optional[str] = None
    ) -> str:
        """Rewrite text while preserving all meaning."""
        prompt = f"""Rewrite this text to improve clarity, grammar, and structure while preserving all original facts, details, and meaning:

{text}

Focus on making it more readable while keeping every piece of information intact."""

        # Build system prompt using PCL with lossless role directive
        role_content = self._load_role_directive("lossless")
        system_prompt = self._build_system_prompt(
            "lossless text rewriting", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def lossless_run(self, text: str, extra_notes: Optional[str] = None) -> str:
        """Perform a comprehensive lossless processing run."""
        # This would typically run multiple passes of improvement
        result = await self.rewrite_lossless(text, extra_notes=extra_notes)

        # Additional passes could be added here
        result = await self.rewrite_lossless(
            result, extra_notes=extra_notes
        )  # Second pass for refinement

        return result

    async def improve_flow(self, text: str, extra_notes: Optional[str] = None) -> str:
        """Improve the flow and transitions in text."""
        prompt = f"""Review this text and improve the flow and transitions between paragraphs and sections:

{text}

Add connecting phrases, improve transitions, and ensure smooth reading flow while preserving all original content."""

        # Build system prompt using PCL with lossless role directive
        role_content = self._load_role_directive("lossless")
        system_prompt = self._build_system_prompt(
            "text flow improvement", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def break_paragraphs(
        self, text: str, extra_notes: Optional[str] = None
    ) -> str:
        """Break dense paragraphs into more readable chunks."""
        prompt = f"""Break up these dense paragraphs into more readable, shorter paragraphs:

{text}

Keep related ideas together but separate distinct concepts into their own paragraphs."""

        # Build system prompt using PCL with lossless role directive
        role_content = self._load_role_directive("lossless")
        system_prompt = self._build_system_prompt(
            "paragraph restructuring", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def enhance_structure(
        self, text: str, extra_notes: Optional[str] = None
    ) -> str:
        """Enhance text structure with appropriate headings and formatting."""
        prompt = f"""Improve the structure of this text with appropriate headings, subheadings, and formatting:

{text}

Add markdown formatting where appropriate to improve readability while preserving all content."""

        # Build system prompt using PCL with lossless role directive
        role_content = self._load_role_directive("lossless")
        system_prompt = self._build_system_prompt(
            "text structure enhancement", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    def _load_role_directive(self, role_name: str) -> str:
        """Load content from a role directive file."""
        from ..utils.project_paths import get_project_root

        # Use robust project root resolution
        project_root = get_project_root()
        role_path = project_root / "directives" / "roles" / f"{role_name}.md"

        if role_path.exists():
            try:
                return role_path.read_text(encoding="utf-8").strip()
            except Exception:
                pass

        # Return empty string if not found
        return ""

    def _build_system_prompt(
        self, subject: str, extra_notes: Optional[str], role_content: str
    ) -> str:
        """Build system prompt using PCL with role directive content."""
        # Compose the prompt using PCL
        composition = pcl.compose(
            subject=subject,
            base="reference",  # Use reference base for structured text processing
            overlays=["no_bs"],  # Use no_bs overlay for clear, direct instructions
            extra_notes=extra_notes,
        )

        # If role directive exists, append its content to the system text
        if role_content:
            composition.system_text += f"\n\n{role_content}"

        return composition.system_text
