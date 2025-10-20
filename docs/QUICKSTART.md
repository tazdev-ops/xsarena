# Quick Start Guide

## Installation
```bash
pip install -e ".[dev]"
```

## First Run

### 1. Start bridge (if using browser mode)
```bash
xsarena ops service start-bridge-v2
```

Open Firefox, add `#bridge=5102` to model URL, click retry on any message.

### 2. Generate your first book
```bash
xsarena run book "Introduction to Python" \
  --length standard \
  --span medium \
  --follow
```

### 3. Check status
```bash
xsarena ops jobs ls
xsarena ops jobs summary <job_id>
```

## Common Tasks

**Continue existing book:**
```bash
xsarena run continue ./books/my_book.md --span medium
```

**Generate study aids:**
```bash
xsarena study generate flashcards ./books/my_book.md
xsarena study generate quiz ./books/my_book.md --num 50
```

**Create snapshot:**
```bash
xsarena ops snapshot create --mode ultra-tight
```

## Next Steps

- [Book Writing Guide](guides/BOOK_WRITING.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [FAQ](FAQ.md)
