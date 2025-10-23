import contextlib
import fnmatch
import json
import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import typer

from xsarena.core.snapshot_config import load_snapshot_presets
from xsarena.utils.secrets_scanner import SecretsScanner
from xsarena.utils.snapshot.pack_txt import flatten_txt

app = typer.Typer(
    help="Generate an intelligent, minimal, and configurable project snapshot."
)


@app.command(
    "create",
    help="Create a flat snapshot, ideal for chatbot uploads. Use --mode ultra-tight for the leanest version.",
)
def snapshot_create(
    mode: str = typer.Option("author-core", "--mode", help="Snapshot mode"),
    out: str = typer.Option("~/repo_flat.txt", "--out", "-o", help="Output .txt path"),
    include: List[str] = typer.Option(
        None,
        "--include",
        "-I",
        help="Extra include glob(s) (used in custom mode or appended to preset)",
    ),
    exclude: List[str] = typer.Option(
        None, "--exclude", "-X", help="Extra exclude glob(s)"
    ),
    git_tracked: bool = typer.Option(
        False, "--git-tracked", help="Enumerate files from git ls-files"
    ),
    max_per_file: int = typer.Option(
        180_000, "--max-per-file", help="Max bytes per file"
    ),
    total_max: int = typer.Option(2_500_000, "--total-max", help="Total max bytes"),
    redact: bool = typer.Option(True, "--redact/--no-redact", help="Apply redaction"),
    repo_map: bool = typer.Option(
        True, "--repo-map/--no-repo-map", help="Add repo map header"
    ),
):
    """
    Flatten curated files into a single .txt. Uses glob-based presets and budgets.
    Tip: 'ultra-tight' is best for AI. 'author-core' is more comprehensive. 'maximal' includes everything for debugging (targets ~1MB).
    """
    mode_lower = (mode or "author-core").lower()

    # Load all presets and default excludes from the single source of truth
    all_presets, default_excludes = load_snapshot_presets()

    # Resolve includes based on mode
    selected_preset = all_presets.get(mode_lower, {})
    if mode_lower == "custom":
        if not include:
            typer.echo(
                "Error: --mode=custom requires at least one --include (-I)", err=True
            )
            raise typer.Exit(code=1)
        inc = list(include)
    else:
        inc = selected_preset.get("include", [])
        if not inc and mode_lower not in all_presets:
            typer.echo(
                f"Error: Unknown mode '{mode}'. Choose from: {', '.join(all_presets.keys())} | custom",
                err=True,
            )
            raise typer.Exit(code=1)

    if mode_lower != "custom" and include:
        inc.extend(include)  # Append extra CLI includes to presets

    # Resolve excludes (preset + default + CLI)
    final_excludes = list(default_excludes)
    final_excludes.extend(selected_preset.get("exclude", []))
    if exclude:
        final_excludes.extend(exclude)
    env_extra = os.getenv("XSA_SNAPSHOT_EXCLUDE", "").strip()
    if env_extra:
        final_excludes += [pat.strip() for pat in env_extra.split(",") if pat.strip()]

    outp = Path(out).expanduser()
    try:
        if outp.exists():
            outp.unlink()
    except Exception:
        pass

    # Always exclude the output file (relative posix)
    try:
        rel_out = (
            outp.resolve().relative_to(Path(".").resolve())
            if outp.is_absolute()
            else outp
        )
        rel_out_pat = str(rel_out).replace("\\", "/")
        final_excludes.append(rel_out_pat)
    except ValueError:
        # If the output file is outside the current directory, don't add it to excludes
        pass

    try:
        out_path, notes = flatten_txt(
            out_path=outp,
            include=inc,
            exclude=final_excludes,
            max_bytes_per_file=max_per_file,
            total_max_bytes=total_max,
            use_git_tracked=git_tracked,
            include_untracked=False,
            redact=redact,
            add_repo_map=repo_map,
        )
        for n in notes:
            typer.echo(f"[note] {n}")

        # Small postflight summary (files embedded and size)
        try:
            text = outp.read_text(encoding="utf-8", errors="replace")
            entries = _parse_flatpack_boundaries(text)
            typer.echo(
                f"✓ Snapshot → {out_path} | files embedded: {len(entries)} | bytes: {outp.stat().st_size:,}"
            )
        except Exception:
            typer.echo(f"✓ Snapshot → {out_path}")

    except Exception as e:
        typer.echo(f"Error creating snapshot: {e}", err=True)
        raise typer.Exit(1) from e


@app.command("report", help="Report true on-disk size for presets (unlimited budgets).")
def snapshot_report():
    """
    Builds temporary flat packs (unlimited budgets) to show raw size of each preset.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tf:
        tmp_path = Path(tf.name)

    try:
        typer.echo("\nSnapshot Mode Size Report\n")
        typer.echo(f"{'Mode':<14} {'Size (bytes)':>12}")
        typer.echo("-" * 28)

        # Load presets to test sizes
        all_presets, default_excludes = load_snapshot_presets()

        # Test all available presets
        for preset_name in sorted(all_presets.keys()):
            preset_include = all_presets.get(preset_name, {}).get("include", [])
            if preset_include:  # Only test if the preset has includes
                flatten_txt(
                    out_path=tmp_path,
                    include=preset_include,
                    exclude=default_excludes,
                    max_bytes_per_file=999_999_999,
                    total_max_bytes=999_999_999,
                    use_git_tracked=False,
                    include_untracked=False,
                    redact=True,
                    add_repo_map=False,
                )
                preset_size = tmp_path.stat().st_size
                typer.echo(f"{preset_name:<14} {preset_size:>12,}")

        typer.echo("\nTip: Use 'xsarena ops snapshot create' to build a snapshot pack.")
    except Exception as e:
        typer.echo(f"Report failed: {e}", err=True)
    finally:
        with contextlib.suppress(Exception):
            os.unlink(str(tmp_path))


@app.command("debug-report", help="Generate a verbose snapshot for debugging.")
def snapshot_debug_report(
    out: str = typer.Option(
        "~/xsa_debug_report.txt", "--out", "-o", help="Output file"
    ),
):
    typer.echo(
        "⚠️  DEPRECATION WARNING: 'xsarena ops snapshot debug-report' is deprecated.",
        err=True,
    )
    typer.echo(
        "Use 'xsarena ops snapshot create --mode maximal --out ~/xsa_debug_report.txt' instead.",
        err=True,
    )
    # For backward compatibility, call the new command with appropriate parameters
    snapshot_create(
        mode="maximal",
        out=out,
        include=None,
        exclude=None,
        git_tracked=False,
        max_per_file=180_000,
        total_max=2_500_000,
        redact=False,
        repo_map=True,
    )


def _posix_path(p: Path) -> str:
    try:
        return p.resolve().relative_to(Path(".").resolve()).as_posix()
    except Exception:
        return p.as_posix().replace("\\", "/")


def _glob_any(rel: str, patterns: List[str]) -> bool:
    rel = rel.replace("\\", "/")
    return any(fnmatch.fnmatch(rel, pat) for pat in (patterns or []))


def _is_binary_quick(path: Path, sample_bytes: int = 8192) -> bool:
    try:
        b = path.read_bytes()[:sample_bytes]
    except Exception:
        return True
    if not b:
        return False
    if b"\x00" in b:
        return True
    text_chars = bytes(range(32, 127)) + b"\n\r\t\b\f"
    non_text_ratio = sum(ch not in text_chars for ch in b) / len(b)
    return non_text_ratio > 0.30


def _parse_flatpack_boundaries(text: str) -> List[Tuple[str, int, bool]]:
    lines = text.splitlines()
    entries = []
    i = 0
    start_re = re.compile(r"^===\s*START\s+FILE:\s*(.+?)\s*===$")
    end_re = re.compile(r"^===\s*END\s+FILE:\s*(.+?)\s*===$")
    while i < len(lines):
        m_a = start_re.match(lines[i])
        if not m_a:
            i += 1
            continue
        rel = m_a.group(1).strip()
        j = i + 1
        is_binary = False
        size_count = 0
        while j < len(lines):
            if lines[j].startswith("[BINARY FILE]"):
                is_binary = True
            if end_re.match(lines[j]):
                break
            size_count += len(lines[j]) + 1
            j += 1
        entries.append((rel, size_count, is_binary))
        i = j + 1
    return entries


@app.command("txt", help="Flat text snapshot (legacy CLI shape).")
def snapshot_txt(
    preset: str = typer.Option("author-core", "--preset", help="Snapshot preset"),
    out: str = typer.Option("~/repo_flat.txt", "--out", "-o"),
    total_max: int = typer.Option(2_500_000, "--total-max"),
    max_per_file: int = typer.Option(180_000, "--max-per-file"),
    repo_map: bool = typer.Option(True, "--repo-map/--no-repo-map"),
):
    all_presets, default_excludes = load_snapshot_presets()
    spec = all_presets.get(preset, {})
    includes = spec.get("include", [])
    outp = Path(out).expanduser()
    flatten_txt(
        out_path=outp,
        include=includes,
        exclude=default_excludes,
        max_bytes_per_file=max_per_file,
        total_max_bytes=total_max,
        use_git_tracked=False,
        include_untracked=False,
        redact=True,
        add_repo_map=repo_map,
    )
    typer.echo(str(outp))


@app.command("verify")
def snapshot_verify(
    snapshot_file: Optional[str] = typer.Option(
        None,
        "--file",
        "-f",
        help="Verify a built flat pack. If omitted, preflight verify.",
    ),
    mode: str = typer.Option(
        "author-core",
        "--mode",
        help="Mode to preflight (ignored if --file is provided)",
    ),
    include: List[str] = typer.Option(
        None, "--include", "-I", help="Extra include patterns (preflight)"
    ),
    exclude: List[str] = typer.Option(
        None, "--exclude", "-X", help="Extra exclude patterns (preflight)"
    ),
    git_tracked: bool = typer.Option(False, "--git-tracked"),
    max_per_file: int = typer.Option(
        200_000, "--max-per-file", help="Per-file budget (bytes)"
    ),
    total_max: int = typer.Option(
        4_000_000, "--total-max", help="Total budget (bytes, preflight only)"
    ),
    disallow: List[str] = typer.Option([], "--disallow", help="Disallow these globs."),
    fail_on: List[str] = typer.Option(
        ["secrets", "oversize", "disallowed", "binary", "missing_required"],
        "--fail-on",
        help="Fail on these categories.",
    ),
    require: List[str] = typer.Option(
        ["README.md", "pyproject.toml"], "--require", help="Paths that must be present"
    ),
    redaction_expected: bool = typer.Option(
        False,
        "--redaction-expected/--no-redaction-expected",
        help="Postflight: warn/fail if no [REDACTED_*] markers appear.",
    ),
    policy: Optional[str] = typer.Option(
        None, "--policy", help="Optional policy .yml."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output in JSON format"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress narrative output"),
):
    """
    Verify snapshot health: preflight (what would be included) or postflight (verify a built file).
    Exits non-zero if configured fail_on categories are hit.
    """
    if policy:
        try:
            import yaml

            data = yaml.safe_load(Path(policy).read_text(encoding="utf-8")) or {}
            disallow = data.get("disallow_globs", disallow) or disallow
            require = data.get("require", require) or require
            max_per_file = int(data.get("max_per_file", max_per_file))
            total_max = int(data.get("total_max", total_max))
            fail_on = data.get("fail_on", fail_on)
        except Exception as e:
            typer.echo(f"[verify] Warning: could not load policy: {e}")

    violations = {
        "secrets": [],
        "oversize": [],
        "disallowed": [],
        "binary": [],
        "missing_required": [],
    }

    def _print_summary(
        total_files: int, total_bytes: int, largest: List[Tuple[str, int]]
    ):
        if not json_output:
            typer.echo(f"[verify] files: {total_files}, bytes: {total_bytes:,}")
            if largest and not quiet:
                typer.echo("[verify] top-10 largest:")
                for rel, sz in largest[:10]:
                    typer.echo(f"  - {rel:<60} ({sz:>7,} bytes)")

    def _fail_if_needed(total_files: int, total_bytes: int):
        to_fail = {k for k in violations if violations[k] and k in set(fail_on)}
        if json_output:
            result = {
                "total_files": total_files,
                "total_bytes": total_bytes,
                "violations": violations,
                "categories_to_fail": sorted(to_fail),
                "status": "FAIL" if to_fail else "OK",
            }
            typer.echo(json.dumps(result))
        else:
            if to_fail:
                typer.echo("[verify] FAIL on categories: " + ", ".join(sorted(to_fail)))
                for cat in sorted(to_fail):
                    if not quiet:
                        typer.echo(f"  [{cat}]")
                        for msg in violations[cat][:25]:
                            typer.echo(f"    - {msg}")
                raise typer.Exit(1)
            if not quiet:
                typer.echo("[verify] OK")
        raise typer.Exit(1 if to_fail else 0)

    if snapshot_file:
        p = Path(snapshot_file)
        if not p.exists():
            typer.echo(f"[verify] file not found: {snapshot_file}")
            raise typer.Exit(2)
        text = p.read_text(encoding="utf-8", errors="replace")
        entries = _parse_flatpack_boundaries(text)
        total_bytes = 0
        largest = []
        for rel, approx_bytes, is_bin in entries:
            total_bytes += approx_bytes
            largest.append((rel, approx_bytes))
            if approx_bytes > max_per_file:
                violations["oversize"].append(
                    f"{rel} ({approx_bytes} > {max_per_file})"
                )
            if _glob_any(rel, disallow):
                violations["disallowed"].append(rel)
            if is_bin:
                violations["binary"].append(rel)
        largest.sort(key=lambda t: t[1], reverse=True)
        if redaction_expected and "[REDACTED_" not in text:
            violations.setdefault("redaction", []).append("no redaction markers found")
        _print_summary(len(entries), total_bytes, largest)
        present = {rel for rel, _, _ in entries}
        for req in require or []:
            if not any(fnmatch.fnmatch(r, req) for r in present):
                violations["missing_required"].append(req)
        _fail_if_needed(len(entries), total_bytes)

    # Preflight logic
    all_presets, default_excludes = load_snapshot_presets()

    base_includes = all_presets[mode].get("include", []) if mode in all_presets else []

    final_includes = base_includes + (include or [])
    final_excludes = default_excludes + (exclude or [])

    # Build candidates strictly from final_includes (expand globs), then filter with final_excludes
    included_files = set()
    for pat in final_includes:
        for p in Path(".").glob(pat):
            if p.is_file():
                included_files.add(p.resolve())

    excluded_files = set()
    for p in included_files:
        if _glob_any(_posix_path(p), final_excludes):
            excluded_files.add(p)

    final_set = included_files - excluded_files
    posix_map = {_posix_path(p): p for p in final_set}

    total_bytes = 0
    largest = []
    scanner = SecretsScanner()
    for rel, p in posix_map.items():
        sz = p.stat().st_size
        total_bytes += sz
        largest.append((rel, sz))
        if sz > max_per_file:
            violations["oversize"].append(f"{rel} ({sz} > {max_per_file})")
        if _glob_any(rel, disallow):
            violations["disallowed"].append(rel)
        if _is_binary_quick(p):
            violations["binary"].append(rel)
        try:
            findings = scanner.scan_file(p)
            if findings:
                violations["secrets"].append(
                    f"{rel} [{findings[0].get('type','secret')}]"
                )
        except Exception:
            pass

    largest.sort(key=lambda t: t[1], reverse=True)
    _print_summary(len(posix_map), total_bytes, largest)
    if total_bytes > total_max:
        violations["oversize"].append(f"[total] {total_bytes:,} > {total_max:,}")

    rels = list(posix_map.keys())
    for req in require or []:
        if not any(fnmatch.fnmatch(r, req) for r in rels):
            violations["missing_required"].append(req)

    _fail_if_needed(len(posix_map), total_bytes)
