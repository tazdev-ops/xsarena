"""Snapshot writers for different output formats."""

from pathlib import Path

from ...core.snapshot_config import load_snapshot_presets
from .pack_txt import flatten_txt


def write_text_snapshot(
    out_path: str,
    mode: str = "minimal",
    with_git: bool = False,
    with_jobs: bool = False,
    with_manifest: bool = False,
    include_system: bool = False,
    dry_run: bool = False,
) -> str:
    """
    Write a text snapshot with configurable options.

    Args:
        out_path: Path to output file
        mode: Snapshot mode (minimal, standard, maximal, etc.)
        with_git: Include git-related files
        with_jobs: Include job-related files
        with_manifest: Include manifest files
        include_system: Include system files
        dry_run: If True, return the path without writing

    Returns:
        Path string of the output file
    """
    # Resolve include/exclude via core.snapshot_config.load_snapshot_presets()
    all_presets, default_excludes = load_snapshot_presets()

    # Choose preset by mode (fallback minimal)
    selected_preset = all_presets.get(mode, all_presets.get("minimal", {}))
    includes = selected_preset.get("include", [])

    # Add additional includes based on flags
    if with_git:
        includes.extend([".git/**/*", ".gitignore", ".gitattributes"])
    if with_jobs:
        includes.extend([".xsarena/jobs/**/*"])
    if with_manifest:
        includes.extend([".xsarena/manifest.json", "project_manifest.json"])

    # Correctly combine default and preset-specific excludes
    preset_excludes = selected_preset.get("exclude", [])
    final_excludes = default_excludes + preset_excludes

    # Call flatten_txt with appropriate parameters
    out_path_obj = Path(out_path).expanduser()

    if not dry_run:
        flatten_txt(
            out_path=out_path_obj,
            include=includes,
            exclude=final_excludes,
            max_bytes_per_file=180000,  # ≈180000
            total_max_bytes=2500000,  # ≈2500000
            use_git_tracked=False,
            include_untracked=False,
            redact=True,
            add_repo_map=include_system,
        )

    return str(out_path_obj)


def write_pro_snapshot(
    out_path: str,
    mode: str = "standard",
) -> str:
    """
    Write a professional snapshot with more comprehensive coverage.

    Args:
        out_path: Path to output file
        mode: Snapshot mode (standard, maximal, etc.)

    Returns:
        Path string of the output file
    """
    # Use "maximal" preset
    all_presets, default_excludes = load_snapshot_presets()
    selected_preset = all_presets.get(mode, all_presets.get("maximal", {}))
    includes = selected_preset.get("include", [])

    # Correctly combine default and preset-specific excludes
    preset_excludes = selected_preset.get("exclude", [])
    final_excludes = default_excludes + preset_excludes

    # Call flatten_txt with appropriate parameters
    out_path_obj = Path(out_path).expanduser()

    flatten_txt(
        out_path=out_path_obj,
        include=includes,
        exclude=final_excludes,
        max_bytes_per_file=180000,
        total_max_bytes=4000000,  # ≈4000000
        use_git_tracked=False,
        include_untracked=False,
        redact=False,  # No redaction for pro snapshot
        add_repo_map=True,
    )

    return str(out_path_obj)


def write_zip_snapshot(out_path: str, mode: str = "standard") -> str:
    """
    Minimal zip snapshot writer for tests/import surface.
    """
    import contextlib
    from zipfile import ZIP_DEFLATED, ZipFile

    all_presets, default_excludes = load_snapshot_presets()
    spec = all_presets.get(mode, all_presets.get("minimal", {}))
    includes = spec.get("include", [])

    # Correctly combine default and preset-specific excludes
    preset_excludes = spec.get("exclude", [])
    final_excludes = default_excludes + preset_excludes

    tmp_txt = Path(out_path).with_suffix(".txt")
    flatten_txt(
        out_path=tmp_txt,
        include=includes,
        exclude=final_excludes,
        max_bytes_per_file=120_000,
        total_max_bytes=1_000_000,
        use_git_tracked=False,
        include_untracked=False,
        redact=True,
        add_repo_map=True,
    )
    outp = Path(out_path).expanduser()
    outp.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(outp, "w", compression=ZIP_DEFLATED) as zf:
        zf.write(tmp_txt, arcname="snapshot.txt")
    with contextlib.suppress(Exception):
        tmp_txt.unlink()
    return str(outp)
