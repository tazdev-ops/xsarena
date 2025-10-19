"""Bilingual processing modes for XSArena."""

from pathlib import Path
from typing import Dict, Optional

from ..core.engine import Engine
from ..core.prompt import pcl


class BilingualMode:
    """Handles bilingual text processing functionality."""

    def __init__(self, engine: Engine):
        self.engine = engine

    async def transform(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        extra_notes: Optional[str] = None,
    ) -> str:
        """Transform text from source language to target language."""
        prompt = f"""Translate the following text from {source_lang} to {target_lang}:

{text}

Maintain the original meaning, tone, and context. Provide a natural translation in the target language."""

        # Build system prompt using PCL with bilingual role directive
        role_content = self._load_role_directive("bilingual")
        system_prompt = self._build_system_prompt(
            "bilingual text processing", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def alignment_check(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        extra_notes: Optional[str] = None,
    ) -> str:
        """Check alignment between source and translated text."""
        prompt = f"""Analyze the alignment between this source text in {source_lang} and its translation in {target_lang}:

Source ({source_lang}):
{source_text}

Translation ({target_lang}):
{translated_text}

Provide an alignment analysis highlighting any discrepancies, omissions, or mistranslations. Rate the alignment quality and suggest improvements."""

        # Build system prompt using PCL with bilingual role directive
        role_content = self._load_role_directive("bilingual")
        system_prompt = self._build_system_prompt(
            "bilingual alignment analysis", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def swap_direction(
        self,
        source_text: str,
        translated_text: str,
        source_lang: str,
        target_lang: str,
        extra_notes: Optional[str] = None,
    ) -> str:
        """Swap the translation direction and verify consistency."""
        prompt = f"""You are provided with a text in {source_lang} and its translation in {target_lang}.
Now translate the {target_lang} text back to {source_lang} to check consistency:

Original {source_lang} text:
{source_text}

{target_lang} translation:
{translated_text}

Please translate the {target_lang} text back to {source_lang} and compare with the original to check for consistency."""

        # Build system prompt using PCL with bilingual role directive
        role_content = self._load_role_directive("bilingual")
        system_prompt = self._build_system_prompt(
            "bilingual consistency check", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def improve_translation(
        self,
        source_text: str,
        current_translation: str,
        source_lang: str,
        target_lang: str,
        extra_notes: Optional[str] = None,
    ) -> str:
        """Improve an existing translation."""
        prompt = f"""Improve this translation from {source_lang} to {target_lang}:

Source text ({source_lang}):
{source_text}

Current translation ({target_lang}):
{current_translation}

Provide an improved translation that better captures the meaning, tone, and nuance of the original text."""

        # Build system prompt using PCL with bilingual role directive
        role_content = self._load_role_directive("bilingual")
        system_prompt = self._build_system_prompt(
            "bilingual translation improvement", extra_notes, role_content
        )
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def glossary_build(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        extra_notes: Optional[str] = None,
    ) -> Dict[str, str]:
        """Build a glossary of key terms from bilingual text."""
        prompt = f"""Extract key terms and their translations from this bilingual text:

Source text ({source_lang}):
{text}

Create a glossary mapping important terms from {source_lang} to {target_lang}. Focus on domain-specific terminology, technical terms, and culturally specific concepts."""

        # Build system prompt using PCL with bilingual role directive
        role_content = self._load_role_directive("bilingual")
        system_prompt = self._build_system_prompt(
            "bilingual glossary building", extra_notes, role_content
        )
        result = await self.engine.send_and_collect(prompt, system_prompt)

        # This would parse the result into a structured glossary
        # For now, return the raw result as a placeholder
        return {"glossary": result}

    def _load_role_directive(self, role_name: str) -> str:
        """Load content from a role directive file."""
        # Try relative to project root (relative to this file)
        project_root = Path(__file__).parent.parent.parent.parent
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
            base="reference",  # Use reference base for clear, structured output
            overlays=["no_bs"],  # Use no_bs overlay for clarity
            extra_notes=extra_notes,
        )

        # If role directive exists, append its content to the system text
        if role_content:
            composition.system_text += f"\n\n{role_content}"

        return composition.system_text
