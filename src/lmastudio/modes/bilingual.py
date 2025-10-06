"""Bilingual processing modes for LMASudio."""

from typing import Dict

from ..core.engine import Engine
from ..core.templates import SYSTEM_PROMPTS


class BilingualMode:
    """Handles bilingual text processing functionality."""

    def __init__(self, engine: Engine):
        self.engine = engine

    async def transform(self, text: str, source_lang: str, target_lang: str) -> str:
        """Transform text from source language to target language."""
        prompt = f"""Translate the following text from {source_lang} to {target_lang}:

{text}

Maintain the original meaning, tone, and context. Provide a natural translation in the target language."""

        system_prompt = SYSTEM_PROMPTS["bilingual"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def alignment_check(
        self, source_text: str, translated_text: str, source_lang: str, target_lang: str
    ) -> str:
        """Check alignment between source and translated text."""
        prompt = f"""Analyze the alignment between this source text in {source_lang} and its translation in {target_lang}:

Source ({source_lang}):
{source_text}

Translation ({target_lang}):
{translated_text}

Provide an alignment analysis highlighting any discrepancies, omissions, or mistranslations. Rate the alignment quality and suggest improvements."""

        system_prompt = SYSTEM_PROMPTS["bilingual"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def swap_direction(
        self, source_text: str, translated_text: str, source_lang: str, target_lang: str
    ) -> str:
        """Swap the translation direction and verify consistency."""
        prompt = f"""You are provided with a text in {source_lang} and its translation in {target_lang}.
Now translate the {target_lang} text back to {source_lang} to check consistency:

Original {source_lang} text:
{source_text}

{target_lang} translation:
{translated_text}

Please translate the {target_lang} text back to {source_lang} and compare with the original to check for consistency."""

        system_prompt = SYSTEM_PROMPTS["bilingual"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def improve_translation(
        self,
        source_text: str,
        current_translation: str,
        source_lang: str,
        target_lang: str,
    ) -> str:
        """Improve an existing translation."""
        prompt = f"""Improve this translation from {source_lang} to {target_lang}:

Source text ({source_lang}):
{source_text}

Current translation ({target_lang}):
{current_translation}

Provide an improved translation that better captures the meaning, tone, and nuance of the original text."""

        system_prompt = SYSTEM_PROMPTS["bilingual"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def glossary_build(
        self, text: str, source_lang: str, target_lang: str
    ) -> Dict[str, str]:
        """Build a glossary of key terms from bilingual text."""
        prompt = f"""Extract key terms and their translations from this bilingual text:

Source text ({source_lang}):
{text}

Create a glossary mapping important terms from {source_lang} to {target_lang}. Focus on domain-specific terminology, technical terms, and culturally specific concepts."""

        system_prompt = SYSTEM_PROMPTS["bilingual"]
        result = await self.engine.send_and_collect(prompt, system_prompt)

        # This would parse the result into a structured glossary
        # For now, return the raw result as a placeholder
        return {"glossary": result}
