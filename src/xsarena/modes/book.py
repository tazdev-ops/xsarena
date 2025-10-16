"""Book authoring modes for XSArena."""

from typing import Dict, Optional

from ..core.backends.transport import BackendTransport
from ..core.state import SessionState
from ..core.templates import SYSTEM_PROMPTS, USER_PROMPTS


class BookMode:
    """Handles book authoring functionality."""

    def __init__(self, transport: BackendTransport, state: SessionState):
        self.transport = transport
        self.state = state

    async def zero2hero(self, topic: str, outline: Optional[str] = None) -> str:
        """Create a comprehensive book from zero to hero level."""
        from ..core.templates import OUTPUT_BUDGET_ADDENDUM, SYSTEM_PROMPTS

        if outline:
            prompt = f"Using this outline, write a comprehensive book about {topic}:\n\n{outline}"
        else:
            prompt = f"Write a comprehensive, detailed book about {topic}. Start with basic concepts and progressively build to advanced topics."

        system_prompt = SYSTEM_PROMPTS["book.zero2hero"].format(subject=topic)

        # Add output budget addendum if enabled
        if self.state.output_budget_snippet_on:
            system_prompt = system_prompt.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM

        # Set session mode for the anti-wrap logic
        self.state.session_mode = "zero2hero"

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "model": getattr(self.state, 'model', 'default')  # Use default model if not set
        }

        # Send the request using the transport
        response = await self.transport.send(payload)
        
        # Extract the content from the response
        choices = response.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            return content
        else:
            return "No response from backend"

    async def reference(self, topic: str) -> str:
        """Create a reference-style book with detailed information."""
        from ..core.templates import OUTPUT_BUDGET_ADDENDUM, SYSTEM_PROMPTS

        prompt = f"Write a comprehensive reference book about {topic}. Include detailed explanations, examples, and cross-references."
        system_prompt = SYSTEM_PROMPTS["book"]

        # Add output budget addendum if enabled
        if self.engine.state.output_budget_snippet_on:
            system_prompt = system_prompt.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM

        return await self.engine.send_and_collect(prompt, system_prompt)

    async def pop(self, topic: str) -> str:
        """Create a popular science/book style content."""
        from ..core.templates import OUTPUT_BUDGET_ADDENDUM, SYSTEM_PROMPTS

        prompt = f"Write an engaging, accessible book about {topic} in a popular science style. Make it understandable to general audiences."
        system_prompt = SYSTEM_PROMPTS["book"]

        # Add output budget addendum if enabled
        if self.engine.state.output_budget_snippet_on:
            system_prompt = system_prompt.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM

        return await self.engine.send_and_collect(prompt, system_prompt)

    async def nobs(self, topic: str) -> str:
        """Create a no-bullshit manual about the topic."""
        from ..core.templates import OUTPUT_BUDGET_ADDENDUM, SYSTEM_PROMPTS

        prompt = f"Write a concise, no-nonsense manual about {topic}. Focus on practical information, skip fluff, be direct."
        system_prompt = SYSTEM_PROMPTS["book"]

        # Add output budget addendum if enabled
        if self.engine.state.output_budget_snippet_on:
            system_prompt = system_prompt.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM

        return await self.engine.send_and_collect(prompt, system_prompt)

    async def exam(self, topic: str) -> str:
        """Create an exam preparation book."""
        from ..core.templates import OUTPUT_BUDGET_ADDENDUM, SYSTEM_PROMPTS

        prompt = f"Write a comprehensive exam preparation book about {topic}. Include key concepts, practice questions, and explanations."
        system_prompt = SYSTEM_PROMPTS["book"]

        # Add output budget addendum if enabled
        if self.engine.state.output_budget_snippet_on:
            system_prompt = system_prompt.strip() + "\n\n" + OUTPUT_BUDGET_ADDENDUM

        return await self.engine.send_and_collect(prompt, system_prompt)

    async def bilingual(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text between languages with alignment."""
        prompt = f"Translate the following text from {source_lang} to {target_lang}:\n\n{text}\n\nMaintain the original meaning and context."
        system_prompt = SYSTEM_PROMPTS["bilingual"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def generate_outline(self, topic: str) -> str:
        """Generate a detailed outline for a book."""
        prompt = USER_PROMPTS["outline"].format(topic=topic)
        system_prompt = SYSTEM_PROMPTS["book"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def write_chapter(
        self, topic: str, chapter_num: int, chapter_title: str, outline_section: str
    ) -> str:
        """Write a specific chapter based on outline."""
        prompt = USER_PROMPTS["chapter"].format(
            topic=topic,
            chapter_num=chapter_num,
            chapter_title=chapter_title,
            outline_section=outline_section,
        )
        system_prompt = SYSTEM_PROMPTS["book"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def polish_text(self, text: str) -> str:
        """Polish text by tightening prose and removing repetition."""
        prompt = USER_PROMPTS["polish"].format(text=text)
        system_prompt = SYSTEM_PROMPTS["book"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def shrink_text(self, text: str) -> str:
        """Shrink text to 70% of original length while preserving facts."""
        prompt = USER_PROMPTS["shrink"].format(text=text)
        system_prompt = SYSTEM_PROMPTS["book"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def critique_text(self, text: str) -> str:
        """Critique text for repetition, flow issues, and clarity."""
        prompt = USER_PROMPTS["critique"].format(text=text)
        system_prompt = SYSTEM_PROMPTS["book"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def generate_diagram(self, description: str) -> str:
        """Generate a Mermaid diagram description."""
        prompt = USER_PROMPTS["diagram"].format(description=description)
        system_prompt = SYSTEM_PROMPTS["book"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def export_chapters(self, full_book: str) -> Dict[str, str]:
        """Split a full book into chapters with TOC and cross-links."""
        # This would parse the full book and split into chapters
        # For now, return a simple example
        chapters = {}
        lines = full_book.split("\n")

        current_chapter = "Introduction"
        current_content = []

        for line in lines:
            if line.strip().startswith("# Chapter") or line.strip().startswith(
                "## Chapter"
            ):
                # Save previous chapter
                if current_content:
                    chapters[current_chapter] = "\n".join(current_content)

                # Start new chapter
                current_chapter = line.strip().replace("#", "").strip()
                current_content = [line]
            else:
                current_content.append(line)

        # Save the last chapter
        if current_content:
            chapters[current_chapter] = "\n".join(current_content)

        return chapters
