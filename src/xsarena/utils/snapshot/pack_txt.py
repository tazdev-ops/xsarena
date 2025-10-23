"""Text packing utilities for snapshot operations."""

import contextlib
import io
from pathlib import Path
from typing import List, Sequence, Tuple

from .collect import (
    PINNED_FIRST,
    REDACT,
    _expand_includes,
    _git_ls_files,
    _is_excluded,
    _language_tag,
    _posix,
    _read_truncated,
    _sha256,
)


def flatten_txt(
    out_path: Path,
    include: Sequence[str],
    exclude: Sequence[str],
    max_bytes_per_file: int,
    total_max_bytes: int,
    use_git_tracked: bool,
    include_untracked: bool,
    redact: bool,
    add_repo_map: bool,
) -> Tuple[Path, List[str]]:
    notes: List[str] = []
    # Base file set
    if use_git_tracked:
        files = _git_ls_files(["ls-files"])
        if include_untracked:
            files |= _git_ls_files(["ls-files", "--others", "--exclude-standard"])
        if not files:
            notes.append("git: no files (or not a repo); falling back to globs")
            files = _expand_includes(include)
    else:
        files = _expand_includes(include)

    # Filter excludes
    base = Path(".").resolve()
    filtered = []
    for f in files:
        try:
            rel = _posix(f.relative_to(base)) if f.is_absolute() else _posix(f)
        except ValueError:
            # If the file is outside the project directory, skip it
            continue
        # Hard-skip if rel path contains any of:
        # "repo_flat.txt", "xsa_min_snapshot", "xsa_debug_report", "snapshot_chunks/", "review/"
        if any(
            skip_path in rel
            for skip_path in [
                "repo_flat.txt",
                "xsa_min_snapshot",
                "xsa_debug_report",
                "snapshot_chunks/",
                "review/",
            ]
        ):
            continue
        if not _is_excluded(rel, exclude):
            filtered.append(f)

    # Correct priority ordering
    # Create a map for sorting pinned files according to their defined order
    pinned_order_map = {path: i for i, path in enumerate(PINNED_FIRST)}

    pinned_files: List[Tuple[str, Path]] = []
    rest_files: List[Path] = []

    # Separate the filtered files into pinned and rest
    for f in filtered:
        try:
            rel_path_str = _posix(f.relative_to(base)) if f.is_absolute() else _posix(f)
        except ValueError:
            # If the file is outside the project directory, skip it
            continue
        if rel_path_str in pinned_order_map:
            pinned_files.append((rel_path_str, f))
        else:
            rest_files.append(f)

    # Sort pinned files according to the order in PINNED_FIRST
    pinned_files.sort(key=lambda item: pinned_order_map[item[0]])

    # Sort the rest of the files alphabetically by their relative path
    def get_sort_key(p):
        try:
            return _posix(p.relative_to(base)) if p.is_absolute() else _posix(p)
        except ValueError:
            # If the file is outside the project directory, return a default value
            return str(p)

    rest_files.sort(key=get_sort_key)

    # Combine the sorted lists to get the final ordered list of files
    ordered = [f for rel_path_str, f in pinned_files] + rest_files

    # Flatten to buffer with budget
    buf = io.StringIO()
    # Header with simple instructions for the chatbot
    buf.write("# Repo Flat Pack\n\n")
    buf.write("Instructions for assistant:\n")
    buf.write("- Treat '=== START FILE: path ===' boundaries as file delimiters.\n")
    buf.write("- Do not summarize early;\n")
    buf.write("  ask for next files if needed.\n")
    buf.write("- Keep references by path for follow-ups.\n\n")

    # Optional repo map
    if add_repo_map:
        buf.write("## Repo Map (selected files)\n\n")
        for f in ordered[:200]:
            rel = _posix(f.relative_to(base)) if f.is_absolute() else _posix(f)
            size = f.stat().st_size if f.exists() else -1
            buf.write(f"- {rel}  ({size} bytes, sha256:{_sha256(f)[:10]})\n")
        buf.write("\n")

    # Content
    written = 0
    for f in ordered:
        if written >= total_max_bytes:
            notes.append("total budget reached; remaining files omitted")
            break
        rel = _posix(f.relative_to(base)) if f.is_absolute() else _posix(f)
        lang = _language_tag(f)
        header = f"=== START FILE: {rel} ===\n"
        footer = f"=== END FILE: {rel} ===\n\n"
        body, truncated = _read_truncated(f, max_bytes_per_file)
        if redact:
            with contextlib.suppress(Exception):
                body = REDACT(body)
        section = []
        section.append(header)
        if lang:
            section.append(f"```{lang}\n")
        section.append(body)
        if lang:
            section.append("\n```")
        section.append("\n")
        section.append(footer)
        chunk = "".join(section)
        buf.write(chunk)
        written += len(chunk.encode("utf-8"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(buf.getvalue(), encoding="utf-8")
    return out_path, notes
