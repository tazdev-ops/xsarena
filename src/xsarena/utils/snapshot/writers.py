"""
Snapshot writing logic for XSArena snapshot utility.
"""

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..helpers import is_binary_sample, safe_read_bytes, safe_read_text
from .builders import build_git_context, build_jobs_summary, build_manifest, build_system_info, get_rules_digest, get_review_artifacts, ts_utc, rel_posix
from .collectors import collect_paths


def write_text_snapshot(
    out_path: Optional[str] = None,
    mode: str = "minimal",
    with_git: bool = False,
    with_jobs: bool = False,
    with_manifest: bool = False,
    git_tracked: bool = False,
    git_include_untracked: bool = False,
    include_system: bool = False,
    dry_run: bool = False,
    redact: bool = True,
    max_size: Optional[int] = None,
) -> None:
    """Write a text snapshot with optional context sections and file contents."""
    from .config import read_snapshot_config
    cfg = read_snapshot_config()
    if max_size is None:
        max_size = cfg.get("max_size", 262144)

    files = collect_paths(
        mode=mode,
        include_git_tracked=git_tracked,
        include_untracked=git_include_untracked,
    )

    if dry_run:
        print(f"Dry run: Would include {len(files)} files in snapshot")
        print(f"Mode: {mode}")
        print(f"Max file size: {max_size} bytes")
        print(f"With git: {with_git}")
        print(f"With jobs: {with_jobs}")
        print(f"With manifest: {with_manifest}")
        print(f"With system: {include_system}")
        print("Files that would be included:")
        for f in files[:20]:  # Show first 20 files
            print(f"  - {f}")
        if len(files) > 20:
            print(f"  ... and {len(files) - 20} more files")
        return

    # Build context
    context_parts = [f"Generated on: {ts_utc()}"]
    if include_system:
        context_parts.append(build_system_info().rstrip())
    if with_git:
        context_parts.append(build_git_context().rstrip())
    if with_jobs:
        context_parts.append(build_jobs_summary().rstrip())
    if with_manifest:
        context_parts.append(build_manifest(files).rstrip())

    context_str = "\n\n".join([p for p in context_parts if p])

    # Write output
    output_path = (
        Path(out_path) if out_path else Path("~/xsa_snapshot.txt").expanduser()
    )

    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write("# XSArena Built-in Snapshot\n")
        if context_str:
            f_out.write(context_str + "\n\n")

        # Write file contents
        for i, p in enumerate(files, 1):
            rp = rel_posix(p)
            f_out.write(f"--- START OF FILE {rp} ---\n")
            try:
                b, truncated = safe_read_bytes(p, max_size)
                if is_binary_sample(b):
                    size = p.stat().st_size
                    digest = hashlib.sha256(p.read_bytes()).hexdigest()
                    f_out.write(f"[BINARY FILE] size={size} sha256={digest}\n")
                else:
                    text = b.decode("utf-8", errors="replace")
                    if truncated:
                        text = f"[... FILE TRUNCATED to {max_size} bytes ...]\n" + text
                    # Apply redaction if enabled
                    if redact and cfg.get("redact", True):
                        from ..redact import redact_snapshot_content
                        text = redact_snapshot_content(text)
                    f_out.write(text)
            except Exception as e:
                f_out.write(f"[ERROR READING FILE: {e}]")
            f_out.write(f"\n--- END OF FILE {rp} ---\n\n")

    print(f"Text snapshot written to: {output_path}")


def write_zip_snapshot(
    out_path: Optional[str] = None,
    mode: str = "minimal",
    with_git: bool = False,
    with_jobs: bool = False,
    with_manifest: bool = False,
    git_tracked: bool = False,
    git_include_untracked: bool = False,
    include_system: bool = False,
    dry_run: bool = False,
    redact: bool = True,
    max_size: Optional[int] = None,
) -> None:
    """Write a zip snapshot with embedded files."""
    from .config import read_snapshot_config
    cfg = read_snapshot_config()
    if max_size is None:
        max_size = cfg.get("max_size", 262144)

    files = collect_paths(
        mode=mode,
        include_git_tracked=git_tracked,
        include_untracked=git_include_untracked,
    )

    if dry_run:
        print(f"Dry run: Would create zip with {len(files)} files")
        print(f"Mode: {mode}")
        print(f"Max file size: {max_size} bytes")
        print(f"With git: {with_git}")
        print(f"With jobs: {with_jobs}")
        print(f"With manifest: {with_manifest}")
        print(f"With system: {include_system}")
        return

    # Build context for snapshot.txt
    context_parts = [f"Generated on: {ts_utc()}"]
    if include_system:
        context_parts.append(build_system_info().rstrip())
    if with_git:
        context_parts.append(build_git_context().rstrip())
    if with_jobs:
        context_parts.append(build_jobs_summary().rstrip())
    if with_manifest:
        context_parts.append(build_manifest(files).rstrip())

    context_str = "\n\n".join([p for p in context_parts if p])

    output_path = (
        Path(out_path) if out_path else Path("~/xsa_snapshot.zip").expanduser()
    )

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # Create snapshot.txt manifest
        manifest = []
        manifest.append("# XSArena Built-in Snapshot")
        manifest.append(context_str)
        manifest.append(f"\n--- MANIFEST ({len(files)} files) ---")
        for p in files:
            try:
                size = p.stat().st_size
                manifest.append(f"{size:>8} {rel_posix(p)}")
            except Exception:
                manifest.append(f"{'ERROR':>8} {rel_posix(p)}")
        manifest.append("\n--- END OF SNAPSHOT ---")

        z.writestr("snapshot.txt", "\n".join(manifest))

        # Add the selected files to the zip
        for i, p in enumerate(files, 1):
            rp = rel_posix(p)
            try:
                b, truncated = safe_read_bytes(p, max_size)
                if is_binary_sample(b):
                    # Store as binary file
                    z.writestr(rp, b)
                    # Also add metadata
                    meta_content = f"# BINARY FILE\npath: {rp}\nsize: {p.stat().st_size}\nsha256: {hashlib.sha256(p.read_bytes()).hexdigest()}\n"
                    z.writestr(rp + ".meta", meta_content)
                else:
                    # Store as text
                    text = b.decode("utf-8", errors="replace")
                    if truncated:
                        text = f"[... FILE TRUNCATED to {max_size} bytes ...]\n" + text
                    # Apply redaction if enabled
                    if redact and cfg.get("redact", True):
                        from ..redact import redact_snapshot_content
                        text = redact_snapshot_content(text)
                    z.writestr(rp, text)
            except Exception as e:
                z.writestr(rp + ".error", f"[ERROR READING FILE: {e}]")

    print(f"Zip snapshot written to: {output_path}")


def write_pro_snapshot(
    out_path: Optional[str] = None,
    max_inline: int = 100000,
    include_system: bool = True,
    include_git: bool = True,
    include_jobs: bool = True,
    include_manifest: bool = True,
    include_rules: bool = True,
    include_reviews: bool = True,
    include_digest: bool = True,
    mode: str = "standard",
    dry_run: bool = False,
    redact: bool = True,
) -> None:
    """Write a pro snapshot with enhanced debugging capabilities."""

    from .config import read_snapshot_config
    cfg = read_snapshot_config()
    max_size = cfg.get("max_size", 262144)

    files = collect_paths(mode=mode)

    if dry_run:
        print(f"Dry run: Would create pro snapshot with {len(files)} files")
        print(f"Max inline: {max_inline} bytes")
        print(f"Include system: {include_system}")
        print(f"Include git: {include_git}")
        print(f"Include jobs: {include_jobs}")
        print(f"Include manifest: {include_manifest}")
        print(f"Include rules: {include_rules}")
        print(f"Include reviews: {include_reviews}")
        print(f"Include digest: {include_digest}")
        return

    # Build context
    context_parts = [f"Generated on: {ts_utc()}"]
    if include_system:
        context_parts.append(build_system_info().rstrip())
    if include_git:
        context_parts.append(build_git_context().rstrip())
    if include_jobs:
        context_parts.append(build_jobs_summary().rstrip())
    if include_manifest:
        context_parts.append(build_manifest(files).rstrip())

    # Additional pro-specific sections
    if include_rules:
        context_parts.append(get_rules_digest().rstrip())
    if include_reviews:
        context_parts.append(get_review_artifacts().rstrip())

    context_str = "\n\n".join([p for p in context_parts if p])

    # Prepare the content
    content_parts = ["# XSArena Pro Built-in Snapshot"]
    if context_str:
        content_parts.append(context_str)

    # Add file contents
    for i, p in enumerate(files, 1):
        rp = rel_posix(p)
        content_parts.append(f"--- START OF FILE {rp} ---")
        try:
            b, truncated = safe_read_bytes(p, max_size)
            if is_binary_sample(b):
                size = p.stat().st_size
                digest = hashlib.sha256(p.read_bytes()).hexdigest()
                content_parts.append(f"[BINARY FILE] size={size} sha256={digest}")
            else:
                text = b.decode("utf-8", errors="replace")
                if truncated:
                    text = f"[... FILE TRUNCATED to {max_size} bytes ...]\n" + text
                # Apply redaction if enabled
                if redact and cfg.get("redact", True):
                    from ..redact import redact_snapshot_content
                    text = redact_snapshot_content(text)
                content_parts.append(text)
        except Exception as e:
            content_parts.append(f"[ERROR READING FILE: {e}]")
        content_parts.append(f"--- END OF FILE {rp} ---\n")

    # Join all content
    full_content = "\n".join(content_parts)

    # Add digest if required
    if include_digest:
        digest = hashlib.sha256(full_content.encode("utf-8")).hexdigest()
        full_content += (
            f"\nSnapshot Integrity Digest (SHA256 of entire snapshot): {digest}\n"
        )

    # Write the output
    output_path = (
        Path(out_path) if out_path else Path("~/xsa_debug_report.txt").expanduser()
    )

    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write(full_content)

    print(f"Pro snapshot written to: {output_path}")