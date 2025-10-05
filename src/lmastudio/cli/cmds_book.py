"""Book mode CLI commands for LMASudio."""
import typer
from typing import Optional
from ..core.config import Config
from ..core.state import SessionState
from ..core.backends import create_backend
from ..core.engine import Engine
from ..modes.book import BookMode

app = typer.Typer()

@app.command("zero2hero")
def book_zero2hero(
    topic: str = typer.Argument(..., help="Topic for the zero-to-hero book"),
    outline: Optional[str] = typer.Option(None, help="Existing outline to follow")
):
    """Create a comprehensive book from zero to hero level."""
    config = Config()
    state = SessionState()
    backend = create_backend(config.backend, base_url=config.base_url, api_key=config.api_key, model=config.model)
    engine = Engine(backend, state)
    book_mode = BookMode(engine)
    
    result = asyncio.run(book_mode.zero2hero(topic, outline))
    print(result)

@app.command("reference")
def book_reference(
    topic: str = typer.Argument(..., help="Topic for the reference book")
):
    """Create a reference-style book with detailed information."""
    config = Config()
    state = SessionState()
    backend = create_backend(config.backend, base_url=config.base_url, api_key=config.api_key, model=config.model)
    engine = Engine(backend, state)
    book_mode = BookMode(engine)
    
    result = asyncio.run(book_mode.reference(topic))
    print(result)

@app.command("pop")
def book_pop(
    topic: str = typer.Argument(..., help="Topic for the popular science book")
):
    """Create a popular science/book style content."""
    config = Config()
    state = SessionState()
    backend = create_backend(config.backend, base_url=config.base_url, api_key=config.api_key, model=config.model)
    engine = Engine(backend, state)
    book_mode = BookMode(engine)
    
    result = asyncio.run(book_mode.pop(topic))
    print(result)

@app.command("nobs")
def book_nobs(
    topic: str = typer.Argument(..., help="Topic for the no-bullshit manual")
):
    """Create a no-bullshit manual about the topic."""
    config = Config()
    state = SessionState()
    backend = create_backend(config.backend, base_url=config.base_url, api_key=config.api_key, model=config.model)
    engine = Engine(backend, state)
    book_mode = BookMode(engine)
    
    result = asyncio.run(book_mode.nobs(topic))
    print(result)

@app.command("outline")
def book_outline(
    topic: str = typer.Argument(..., help="Topic for the book outline")
):
    """Generate a detailed outline for a book."""
    config = Config()
    state = SessionState()
    backend = create_backend(config.backend, base_url=config.base_url, api_key=config.api_key, model=config.model)
    engine = Engine(backend, state)
    book_mode = BookMode(engine)
    
    result = asyncio.run(book_mode.generate_outline(topic))
    print(result)

@app.command("polish")
def book_polish(
    text: str = typer.Argument(..., help="Text to polish")
):
    """Polish text by tightening prose and removing repetition."""
    config = Config()
    state = SessionState()
    backend = create_backend(config.backend, base_url=config.base_url, api_key=config.api_key, model=config.model)
    engine = Engine(backend, state)
    book_mode = BookMode(engine)
    
    result = asyncio.run(book_mode.polish_text(text))
    print(result)

@app.command("shrink")
def book_shrink(
    text: str = typer.Argument(..., help="Text to shrink to 70% length")
):
    """Shrink text to 70% of original length while preserving facts."""
    config = Config()
    state = SessionState()
    backend = create_backend(config.backend, base_url=config.base_url, api_key=config.api_key, model=config.model)
    engine = Engine(backend, state)
    book_mode = BookMode(engine)
    
    result = asyncio.run(book_mode.shrink_text(text))
    print(result)

@app.command("critique")
def book_critique(
    text: str = typer.Argument(..., help="Text to critique for repetition and flow")
):
    """Critique text for repetition, flow issues, and clarity."""
    config = Config()
    state = SessionState()
    backend = create_backend(config.backend, base_url=config.base_url, api_key=config.api_key, model=config.model)
    engine = Engine(backend, state)
    book_mode = BookMode(engine)
    
    result = asyncio.run(book_mode.critique_text(text))
    print(result)

@app.command("diagram")
def book_diagram(
    description: str = typer.Argument(..., help="Description of the diagram to generate")
):
    """Generate a Mermaid diagram description."""
    config = Config()
    state = SessionState()
    backend = create_backend(config.backend, base_url=config.base_url, api_key=config.api_key, model=config.model)
    engine = Engine(backend, state)
    book_mode = BookMode(engine)
    
    result = asyncio.run(book_mode.generate_diagram(description))
    print(result)

@app.command("hammer")
def book_hammer(
    enabled: bool = typer.Argument(..., help="Enable or disable coverage hammer")
):
    """Toggle the coverage hammer (anti-wrap continuation hint for self-study)."""
    config = Config()
    state = SessionState()
    
    state.coverage_hammer_on = enabled
    print(f"Coverage hammer: {'ON' if state.coverage_hammer_on else 'OFF'}")

@app.command("budget")
def output_budget(
    enabled: bool = typer.Argument(..., help="Enable or disable output budget addendum")
):
    """Toggle output budget addendum on book prompts."""
    config = Config()
    state = SessionState()
    
    state.output_budget_snippet_on = enabled
    print(f"Output budget addendum: {'ON' if state.output_budget_snippet_on else 'OFF'}")

@app.command("push")
def output_push(
    enabled: bool = typer.Argument(..., help="Enable or disable output pushing")
):
    """Toggle auto-extension within subtopic to hit min length."""
    config = Config()
    state = SessionState()
    
    state.output_push_on = enabled
    print(f"Output push: {'ON' if state.output_push_on else 'OFF'}")

@app.command("minchars")
def output_minchars(
    n: int = typer.Argument(..., help="Set minimal chars per chunk before moving on")
):
    """Set minimum characters per chunk."""
    config = Config()
    state = SessionState()
    
    if n < 1000:
        print("Value too small; suggest >= 2500.")
    
    state.output_min_chars = max(1000, n)
    print(f"Output min chars: {state.output_min_chars}")

@app.command("passes")
def output_passes(
    n: int = typer.Argument(..., help="Set max extension steps per chunk")
):
    """Set maximum extension passes per chunk."""
    config = Config()
    state = SessionState()
    
    if n < 0 or n > 10:
        print("Unusual value; using within [0..10].")
    
    state.output_push_max_passes = max(0, min(10, n))
    print(f"Output push max passes: {state.output_push_max_passes}")

@app.command("cont-mode")
def cont_mode(
    mode: str = typer.Argument(..., help="Set continuation mode (anchor/normal)")
):
    """Set continuation strategy."""
    config = Config()
    state = SessionState()
    
    if mode.lower() in ["anchor", "normal"]:
        state.continuation_mode = mode.lower()
        print(f"Continuation mode: {state.continuation_mode}")
    else:
        print("Usage: cont-mode [anchor|normal]")

@app.command("cont-anchor")
def cont_anchor(
    n: int = typer.Argument(..., help="Set anchor length in chars")
):
    """Set anchor length."""
    config = Config()
    state = SessionState()
    
    if n < 50 or n > 2000:
        print("Choose a value between 50 and 2000.")
    else:
        state.anchor_length = n
        print(f"Anchor length: {state.anchor_length}")

@app.command("repeat-warn")
def repeat_warn(
    enabled: bool = typer.Argument(..., help="Enable or disable repetition warning")
):
    """Toggle repetition warning."""
    config = Config()
    state = SessionState()
    
    state.repetition_warn = enabled
    print(f"Repetition warning: {'ON' if state.repetition_warn else 'OFF'}")

@app.command("repeat-thresh")
def repeat_thresh(
    threshold: float = typer.Argument(..., help="Set repetition Jaccard threshold (0..1)")
):
    """Set repetition threshold."""
    config = Config()
    state = SessionState()
    
    if threshold <= 0 or threshold >= 1:
        print("Use a value between 0 and 1 (e.g., 0.35).")
    else:
        state.repetition_threshold = threshold
        print(f"Repetition threshold: {state.repetition_threshold}")