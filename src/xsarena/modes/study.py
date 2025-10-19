"""Study and learning modes for XSArena."""

from pathlib import Path
from typing import Any, Dict, List

from ..core.engine import Engine
from ..utils.project_paths import get_project_root


# Load templates directly from directive files
def _load_directive_content(file_path: str) -> str:
    """Load content from a directive file."""
    # First try relative to current working directory
    if Path(file_path).exists():
        return Path(file_path).read_text(encoding="utf-8").strip()

    # Try relative to project root using robust resolution
    project_root = get_project_root()
    full_path = project_root / file_path
    if full_path.exists():
        return full_path.read_text(encoding="utf-8").strip()

    # Return empty string if not found
    return ""


# Load system prompts from directive files
SYSTEM_PROMPTS = {
    "book": _load_directive_content("directives/roles/book.md"),
}

# Fallback hardcoded value if directive file is not available
if not SYSTEM_PROMPTS["book"]:
    SYSTEM_PROMPTS[
        "book"
    ] = "You are an educational assistant. Create study materials, flashcards, and learning aids."


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
