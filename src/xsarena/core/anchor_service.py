"""Anchor service for all anchor-related functionality."""

from .backends.transport import BackendTransport


def anchor_from_text(txt: str, tail_chars: int) -> str:
    """
    Create an anchor from arbitrary text.

    Args:
        txt: The text to create an anchor from
        tail_chars: Number of characters to use for the anchor

    Returns:
        An anchor from the text
    """
    if not txt:
        return ""
    s = txt[-tail_chars:]
    p = max(s.rfind("."), s.rfind("!"), s.rfind("?"))
    if p != -1 and p >= len(s) - 120:
        s = s[: p + 1]
    return s.strip()


def semantic_anchor_from_text(text: str, context_chars: int = 400) -> str:
    """
    Create a semantic anchor by summarizing the last part of the text.

    Args:
        text: The text to summarize
        context_chars: Number of characters to use for context

    Returns:
        A semantic summary of the text tail
    """
    if not text:
        return ""

    # Get the last context_chars characters
    context = text[-context_chars:]

    # For now, we'll use a simple approach to extract key sentences
    # In a real implementation, this would call an LLM to summarize
    sentences = context.split(".")

    # Filter out empty sentences and take the last few meaningful ones
    meaningful_sentences = [
        s.strip() for s in sentences if s.strip() and len(s.strip()) > 10
    ]

    # Take the last 1-2 sentences as the semantic summary
    if len(meaningful_sentences) >= 2:
        semantic_summary = ". ".join(meaningful_sentences[-2:])
    elif meaningful_sentences:
        semantic_summary = meaningful_sentences[-1]
    else:
        # Fallback to simple anchor if no meaningful sentences found
        return anchor_from_text(text, context_chars)

    # Add a period if needed
    if semantic_summary and not semantic_summary.endswith("."):
        semantic_summary += "."

    return semantic_summary


def build_anchor_continue_prompt(anchor: str) -> str:
    """
    Build a prompt to continue from an anchor.

    Args:
        anchor: The anchor text to continue from

    Returns:
        A prompt to continue from the anchor
    """
    if not anchor:
        return "Continue from where you left off."
    return f"Continue exactly from after the anchor; do not repeat or reintroduce; no summary.\\nANCHOR:\\n<<<ANCHOR\\n{anchor}\\nANCHOR>>>"


def build_anchor_prompt(anchor_text: str, anchor_length: int = 300) -> str:
    """Build an anchor prompt to maintain context."""
    if not anchor_text:
        return ""

    # Take the last anchor_length characters
    anchor = anchor_text[-anchor_length:]

    # Try to find a sentence boundary to avoid cutting mid-sentence
    last_sentence_end = anchor.rfind(".")
    if last_sentence_end != -1 and last_sentence_end > anchor_length * 0.7:
        anchor = anchor[last_sentence_end + 1 :].strip()

    if not anchor:
        return ""
    return f"\\nANCHOR:\\n<<<ANCHOR\\n{anchor}\\nANCHOR>>>\\nContinue exactly from after the anchor; do not repeat or reintroduce; no summary."


async def create_anchor(
    content: str,
    use_semantic: bool = False,
    transport: Optional[BackendTransport] = None,
    context_chars: int = 400,
    tail_chars: int = 300,
) -> str:
    """
    Create an anchor from content, using either simple text extraction or semantic summarization.

    Args:
        content: The content to create an anchor from
        use_semantic: Whether to use semantic summarization or simple text extraction
        transport: Backend transport for semantic summarization (required if use_semantic=True)
        context_chars: Number of characters to use for semantic context
        tail_chars: Number of characters to use for simple text extraction

    Returns:
        The created anchor text
    """
    if not content:
        return ""

    if use_semantic and transport:
        return await summarize_tail_via_backend(content, transport, context_chars)
    else:
        return anchor_from_text(content, tail_chars)


async def summarize_tail_via_backend(
    text: str, transport: BackendTransport, context_chars: int = 400
) -> str:
    """
    Create a semantic anchor by calling the backend to summarize the last part of the text.

    Args:
        text: The text to summarize
        transport: The backend transport to use
        context_chars: Number of characters to use for context

    Returns:
        A semantic summary of the text tail
    """
    if not text or not transport:
        return ""

    # Get the last context_chars characters
    context = text[-context_chars:]

    # Create a system message asking for a short summary
    system_prompt = (
        "You are a text summarization assistant. "
        "Summarize the last 1-2 lines of the provided text in 1-2 lines, "
        "preserving the key semantic meaning and context."
    )
    user_prompt = f"Summarize this text in 1-2 lines:\\n\\n{context}"

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "model": "gpt-4o",  # Use a fast model for this
        "temperature": 0.1,  # Low temperature for consistency
        "max_tokens": 100,  # Keep it short
    }

    try:
        response = await transport.send(payload)
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        return content.strip()
    except Exception:
        # Fallback to simple anchor if backend call fails
        return semantic_anchor_from_text(text, context_chars)
