"""Lossless processing modes for XSArena."""

from pathlib import Path

from ..core.engine import Engine


# Load templates directly from directive files
def _load_directive_content(file_path: str) -> str:
    """Load content from a directive file."""
    # First try relative to current working directory
    if Path(file_path).exists():
        return Path(file_path).read_text(encoding="utf-8").strip()

    # Try relative to project root (relative to this file)
    project_root = Path(__file__).parent.parent.parent.parent
    full_path = project_root / file_path
    if full_path.exists():
        return full_path.read_text(encoding="utf-8").strip()

    # Return empty string if not found
    return ""


# Load system prompts from directive files
SYSTEM_PROMPTS = {
    "lossless": _load_directive_content("directives/roles/lossless.md"),
}

# Fallback hardcoded value if directive file is not available
if not SYSTEM_PROMPTS["lossless"]:
    SYSTEM_PROMPTS[
        "lossless"
    ] = "You are a text processing assistant. Preserve all original meaning while improving clarity and structure."


class LosslessMode:
    """Handles lossless text processing functionality."""

    def __init__(self, engine: Engine):
        self.engine = engine

    async def ingest_synth(self, text: str) -> str:
        """Ingest and synthesize information from text."""
        prompt = f"""Please analyze and synthesize this text, extracting key concepts, facts, and insights:

{text}

Provide a synthesized summary that captures the essential information in a structured format."""

        system_prompt = SYSTEM_PROMPTS["lossless"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def rewrite_lossless(self, text: str) -> str:
        """Rewrite text while preserving all meaning."""
        prompt = f"""Rewrite this text to improve clarity, grammar, and structure while preserving all original facts, details, and meaning:

{text}

Focus on making it more readable while keeping every piece of information intact."""

        system_prompt = SYSTEM_PROMPTS["lossless"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def lossless_run(self, text: str) -> str:
        """Perform a comprehensive lossless processing run."""
        # This would typically run multiple passes of improvement
        result = await self.rewrite_lossless(text)

        # Additional passes could be added here
        result = await self.rewrite_lossless(result)  # Second pass for refinement

        return result

    async def improve_flow(self, text: str) -> str:
        """Improve the flow and transitions in text."""
        prompt = f"""Review this text and improve the flow and transitions between paragraphs and sections:

{text}

Add connecting phrases, improve transitions, and ensure smooth reading flow while preserving all original content."""

        system_prompt = SYSTEM_PROMPTS["lossless"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def break_paragraphs(self, text: str) -> str:
        """Break dense paragraphs into more readable chunks."""
        prompt = f"""Break up these dense paragraphs into more readable, shorter paragraphs:

{text}

Keep related ideas together but separate distinct concepts into their own paragraphs."""

        system_prompt = SYSTEM_PROMPTS["lossless"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def enhance_structure(self, text: str) -> str:
        """Enhance text structure with appropriate headings and formatting."""
        prompt = f"""Improve the structure of this text with appropriate headings, subheadings, and formatting:

{text}

Add markdown formatting where appropriate to improve readability while preserving all content."""

        system_prompt = SYSTEM_PROMPTS["lossless"]
        return await self.engine.send_and_collect(prompt, system_prompt)
