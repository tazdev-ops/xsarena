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