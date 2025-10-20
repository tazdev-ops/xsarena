"""
Generate study aids for all books in a directory.
"""
import subprocess
from pathlib import Path

books_dir = Path("./books")

for book in books_dir.glob("*.md"):
    print(f"\nProcessing: {book.name}")

    # Flashcards
    subprocess.run(
        [
            "xsarena",
            "study",
            "generate",
            "flashcards",
            str(book),
            "--out",
            f"study/{book.stem}_flashcards.md",
        ]
    )

    # Quiz
    subprocess.run(
        [
            "xsarena",
            "study",
            "generate",
            "quiz",
            str(book),
            "--num",
            "50",
            "--out",
            f"study/{book.stem}_quiz.md",
        ]
    )

    print(f"✓ Study aids created for {book.name}")
