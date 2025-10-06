"""Study and learning modes for LMASudio."""

from typing import Any, Dict, List

from ..core.engine import Engine
from ..core.templates import SYSTEM_PROMPTS


class StudyMode:
    """Handles study and learning functionality."""

    def __init__(self, engine: Engine):
        self.engine = engine

    async def generate_flashcards(self, content: str, num_cards: int = 10) -> str:
        """Generate flashcards from content."""
        prompt = f"""Generate {num_cards} flashcards from the following content. Format as Q: [question] A: [answer] pairs:

{content}"""

        system_prompt = SYSTEM_PROMPTS[
            "book"
        ]  # Using book mode for educational content
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def generate_quiz(
        self, content: str, num_questions: int = 10, question_type: str = "mixed"
    ) -> str:
        """Generate quiz questions from content."""
        prompt = f"""Generate {num_questions} quiz questions from the following content. Use {question_type} question types (multiple choice, short answer, true/false, etc.):

{content}

Provide questions with clear answer choices where appropriate and include the correct answers."""

        system_prompt = SYSTEM_PROMPTS["book"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def create_glossary(self, content: str) -> str:
        """Create a glossary of key terms from content."""
        prompt = f"""Create a comprehensive glossary of key terms from the following content:

{content}

Define each term clearly and concisely, focusing on terms that are important for understanding the content."""

        system_prompt = SYSTEM_PROMPTS["book"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def generate_index(self, content: str) -> str:
        """Generate an index for the content."""
        prompt = f"""Generate a detailed index for the following content, listing key topics and their locations:

{content}

Organize the index in a hierarchical format with main topics and subtopics."""

        system_prompt = SYSTEM_PROMPTS["book"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def drill_mode(
        self, questions: List[str], answers: List[str]
    ) -> Dict[str, Any]:
        """Conduct a spaced repetition drill session."""
        # This would typically implement a more complex interaction loop
        # For now, we'll return a simple analysis of the questions
        drill_session = {
            "total_questions": len(questions),
            "session_type": "spaced_repetition_drill",
            "instructions": "Present questions one at a time, track recall, and schedule reviews based on spaced repetition algorithms",
        }

        return drill_session

    async def create_study_guide(self, content: str) -> str:
        """Create a comprehensive study guide from content."""
        prompt = f"""Create a comprehensive study guide from the following content:

{content}

Include key concepts, summaries, important points to remember, and self-assessment questions."""

        system_prompt = SYSTEM_PROMPTS["book"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def topic_summary(self, content: str, topic: str) -> str:
        """Create a summary of a specific topic from content."""
        prompt = f"""Create a detailed summary of {topic} from the following content:

{content}

Focus specifically on information related to {topic} and how it connects to the broader content."""

        system_prompt = SYSTEM_PROMPTS["book"]
        return await self.engine.send_and_collect(prompt, system_prompt)
