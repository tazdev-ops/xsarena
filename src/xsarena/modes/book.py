"""Book authoring modes for XSArena."""

from pathlib import Path
from typing import Dict, Optional

from ..core.backends.transport import BackendTransport
from ..core.state import SessionState
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
    "book.zero2hero": _load_directive_content("directives/base/zero2hero.md"),
}

# Fallback hardcoded value if directive file is not available
if not SYSTEM_PROMPTS["book.zero2hero"]:
    SYSTEM_PROMPTS[
        "book.zero2hero"
    ] = """SUBJECT: {subject}

ROLE
You are a seasoned practitioner and teacher in {subject}. Write a comprehensive, high‑density self‑study manual that takes a serious learner from foundations to a master's‑level grasp and practice.

COVERAGE CONTRACT (do not violate)
- Scope: cover the entire field and its major subfields, theory → methods → applications → pitfalls → practice. Include core debates, default choices (and when to deviate), and limits of claims.
- Depth: build from zero to graduate‑level competence; teach skills, not trivia. Show decisive heuristics, procedures, and failure modes at the point of use.
- No early wrap‑up: do not conclude, summarize, or end before the whole field and subfields are covered to the target depth. Treat "continue." as proceeding exactly where you left off on the next input.
- Continuity: pick up exactly where the last chunk stopped; no re‑introductions; no throat‑clearing.

VOICE AND STANCE
- Plain, direct language; avoid pompous terms and circumlocutions.
- Prefer short sentences and concrete nouns/verbs.
- Remove throat‑clearing, meta commentary, and rhetorical filler.

STYLE
- Mostly tight paragraph prose. Use bullets only when a read-and-do list is clearer.
- Examples only when they materially clarify a decision or distinction.
- Keep numbers when they guide choices; avoid derivations.

JARGON
- Prefer plain language; on first use, write the full term with a short parenthetical gloss; minimize acronyms.

CONTROVERSIES
- Cover directly. Label strength: [robust] [mixed] [contested]. Present main views; state when each might be right; pick a default and give the reason.

EVIDENCE AND CREDITS
- Name only canonical figures, laws, or must‑know sources when attribution clarifies.

PRACTICALITY
- Weave procedures, defaults/ranges, quick checks, and common failure modes where they matter.
- Include checklists, rubrics, and projects/exercises across the arc.

CONTINUATION & CHUNKING
- Write ~800–1,200 words per chunk; stop at a natural break.
- End every chunk with one line: NEXT: [what comes next] (the next specific subtopic).
- On input continue. resume exactly where you left off, with no repetition or re‑introductions, and end again with NEXT: [...]
- Do not end until the manual is complete. When truly complete, end with: NEXT: [END].

BEGIN
Start now from the foundations upward. No preface or meta; go straight into teaching.
"""

# Load user prompts from directive files (if they exist)
USER_PROMPTS = {
    # Define any user prompts that might exist in directives
}


def _load_output_budget_addendum() -> str:
    """Load the output budget addendum from directive file or return default."""
    from ..utils.project_paths import get_project_root

    # Try to load from directive file using robust project root resolution
    project_root = get_project_root()
    budget_path = project_root / "directives" / "prompt" / "output_budget.md"

    if budget_path.exists():
        try:
            return budget_path.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # Return default content if file not found or error
    return """OUTPUT BUDGET
- Use the full available output window in each response. Do not hold back or end early.
- If you approach the limit mid-subtopic, stop cleanly (no wrap-up). You will resume exactly where you left off on the next input.
- Do not jump ahead or skip subtopics to stay concise. Continue teaching until the whole field and subfields reach the target depth.
"""


class BookMode:
    """Handles book authoring functionality."""

    def __init__(self, transport: BackendTransport, state: SessionState):
        self.transport = transport
        self.state = state

    async def zero2hero(self, topic: str, outline: Optional[str] = None) -> str:
        """Create a comprehensive book from zero to hero level."""
        # Use the local SYSTEM_PROMPTS defined in this module
        local_system_prompts = {"book.zero2hero": SYSTEM_PROMPTS["book.zero2hero"]}

        if outline:
            prompt = f"Using this outline, write a comprehensive book about {topic}:\n\n{outline}"
        else:
            prompt = f"Write a comprehensive book about {topic} from zero to hero level, covering all essential concepts progressively."

        system_prompt = local_system_prompts["book.zero2hero"].format(subject=topic)

        # Add output budget addendum if enabled
        if self.state.output_budget_snippet_on:
            system_prompt = (
                system_prompt.strip() + "\n\n" + _load_output_budget_addendum()
            )

        # Set session mode for the anti-wrap logic
        self.state.session_mode = "zero2hero"

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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

        prompt = f"Write a comprehensive reference book about {topic}. Include detailed explanations, examples, and cross-references."

        # Use the local SYSTEM_PROMPTS defined in this module
        system_prompt = """You are a skilled author helping write a comprehensive book.
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing."""

        # Add output budget addendum if enabled
        if self.state.output_budget_snippet_on:
            system_prompt = (
                system_prompt.strip() + "\n\n" + _load_output_budget_addendum()
            )

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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

    async def pop(self, topic: str) -> str:
        """Create a popular science/book style content."""

        prompt = f"Write an engaging, accessible book about {topic} in a popular science style. Make it understandable to general audiences."

        # Use the local SYSTEM_PROMPTS defined in this module
        system_prompt = """You are a skilled author helping write a comprehensive book.
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing."""

        # Add output budget addendum if enabled
        if self.state.output_budget_snippet_on:
            system_prompt = (
                system_prompt.strip() + "\n\n" + _load_output_budget_addendum()
            )

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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

    async def nobs(self, topic: str) -> str:
        """Create a no-bullshit manual about the topic."""

        prompt = f"Write a concise, no-nonsense manual about {topic}. Focus on practical information, skip fluff, be direct."

        # Use the local SYSTEM_PROMPTS defined in this module
        system_prompt = """You are a skilled author helping write a comprehensive book.
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing."""

        # Add output budget addendum if enabled
        if self.state.output_budget_snippet_on:
            system_prompt = (
                system_prompt.strip() + "\n\n" + _load_output_budget_addendum()
            )

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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

    async def exam(self, topic: str) -> str:
        """Create an exam preparation book."""

        prompt = f"Write a comprehensive exam preparation book about {topic}. Include key concepts, practice questions, and explanations."

        # Use the local SYSTEM_PROMPTS defined in this module
        system_prompt = """You are a skilled author helping write a comprehensive book.
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing."""

        # Add output budget addendum if enabled
        if self.state.output_budget_snippet_on:
            system_prompt = (
                system_prompt.strip() + "\n\n" + _load_output_budget_addendum()
            )

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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

    async def bilingual(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text between languages with alignment."""
        prompt = f"Translate the following text from {source_lang} to {target_lang}:\n\n{text}\n\nMaintain the original meaning and context."

        # Use the local SYSTEM_PROMPTS defined in this module
        system_prompt = """You are a translation and alignment expert. Translate text accurately between languages.
Maintain the original meaning and context. Provide translation that is natural in the target language."""

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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

    async def generate_outline(self, topic: str) -> str:
        """Generate a detailed outline for a book."""
        prompt = f"Create a detailed outline for a book about {topic}. Include main chapters, subsections, and key points for each section."

        # Use the local SYSTEM_PROMPTS defined in this module
        system_prompt = """You are a skilled author helping write a comprehensive book.
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing."""

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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

    async def write_chapter(
        self, topic: str, chapter_num: int, chapter_title: str, outline_section: str
    ) -> str:
        """Write a specific chapter based on outline."""
        prompt = f"Write Chapter {chapter_num} titled '{chapter_title}' of the book about {topic}. Use the following outline: {outline_section}"

        # Use the local SYSTEM_PROMPTS defined in this module
        system_prompt = """You are a skilled author helping write a comprehensive book.
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing."""

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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

    async def polish_text(self, text: str) -> str:
        """Polish text by tightening prose and removing repetition."""
        prompt = f"Review and improve this text: {text}\n\nFocus on tightening prose, removing repetition, and improving flow while preserving all facts and details."

        # Use the local SYSTEM_PROMPTS defined in this module
        system_prompt = """You are a skilled author helping write a comprehensive book.
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing."""

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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

    async def shrink_text(self, text: str) -> str:
        """Shrink text to 70% of original length while preserving facts."""
        prompt = f"Condense this text to approximately 70% of its current length while preserving all facts and key information: {text}"

        # Use the local SYSTEM_PROMPTS defined in this module
        system_prompt = """You are a skilled author helping write a comprehensive book.
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing."""

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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

    async def critique_text(self, text: str) -> str:
        """Critique text for repetition, flow issues, and clarity."""
        prompt = f" Critique this text for repetition, flow issues, and clarity: {text}"

        # Use the local SYSTEM_PROMPTS defined in this module
        system_prompt = """You are a skilled author helping write a comprehensive book.
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing."""

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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

    async def generate_diagram(self, description: str) -> str:
        """Generate a Mermaid diagram description."""
        prompt = f"Generate a mermaid diagram for: {description}\n\nChoose the most appropriate diagram type (flowchart, sequence, mindmap, etc.)"

        # Use the local SYSTEM_PROMPTS defined in this module
        system_prompt = """You are a skilled author helping write a comprehensive book.
Follow the user's instructions carefully. Maintain consistency in tone, style, and content across sections.
Focus on accuracy, clarity, and depth in your writing."""

        # Prepare the payload for the transport
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "model": getattr(
                self.state, "model", "default"
            ),  # Use default model if not set
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
