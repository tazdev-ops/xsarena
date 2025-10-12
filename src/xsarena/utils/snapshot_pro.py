#!/usr/bin/env python3
"""
XSArena Snapshot Pro
- Deterministic project snapshot (text-first, binary-safe metadata).
- Chunking under a strict limit (default 110,000 chars per chunk).
- Index chunk with user message and auto summary.
- Atomic writes, manifest store, verify, and diff against last manifest.

No external dependencies. Python 3.8+.

Usage examples:
  python -m xsarena.utils.snapshot_pro write --root . \
    --out ~/snapshot.txt --chunks ~/snapshot_chunks --limit 110000 \
    --message "Context Capsule for session XYZ"

  python -m xsarena.utils.snapshot_pro verify --out ~/snapshot.txt --chunks ~/snapshot_chunks

  python -m xsarena.utils.snapshot_pro diff

Notes
- Deterministic: paths sorted, fixed newline, stable headers; timestamps excluded from hash.
- Excludes: sane defaults (VCS, caches, vendored); configurable.
- Large/binary files: metadata only by default; configurable ceiling for inline content.
- Chunk names: snapshot_part_aa, ba, ca, ... (compatible with your existing pattern).
"""

from __future__ import annotations

import argparse
import dataclasses
import fnmatch
import hashlib
import io
import json
import os
import shutil
import string
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

# ---------- Config defaults ----------

DEFAULT_EXCLUDES = [
    # VCS / tooling
    ".git/",
    ".hg/",
    ".svn/",
    ".idea/",
    ".vscode/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".pytest_cache/",
    ".cache/",
    ".tox/",
    ".coverage*",
    ".DS_Store",
    # Python build/caches
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.egg-info/",
    "build/",
    "dist/",
    "*.egg",
    # Node / packagers
    "node_modules/",
    "pnpm-lock.yaml",
    "package-lock.json",
    ".yarn/",
    ".pnpm-store/",
    # Virtualenvs
    "venv/",
    ".venv/",
    "env/",
    ".env/",
    # Project-specific noisy/derived
    "snapshot.txt",
    "preview_snapshot.txt",
    "final_snapshot.txt",
    "snapshot_chunks/",
    "snapshots/",
    ".xsarena/agent/journal.jsonl",
    # Binaries/logs
    "*.log",
    "*.pdf",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.webp",
    "*.ico",
    "*.zip",
    "*.tar",
    "*.tar.gz",
    "*.gz",
    "*.bz2",
    "*.xz",
    "*.7z",
    # IDE settings
    "*.iml",
    ".classpath",
    ".project",
    ".settings/",
    # OS noise
    "Thumbs.db",
    "ehthumbs.db",
    "Icon\r",
    "._*",
]

TEXT_EXTS = {
    ".py",
    ".pyi",
    ".md",
    ".markdown",
    ".txt",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".sh",
    ".bat",
    ".ps1",
    ".bash",
    ".zsh",
    ".fish",
    ".env",
    ".dockerignore",
    "Dockerfile",
    ".make",
    "Makefile",
    ".mk",
    ".csv",
    ".tsv",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".less",
    ".xml",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".vue",
    ".rst",
}

DEFAULT_LIMIT = 110_000  # characters per chunk
DEFAULT_MAX_INLINE_BYTES = 1_000_000  # 1MB cap for inline file content
MANIFEST_PATH = Path(".xsarena/snapshots/manifest.json")  # stored manifest
LAST_MANIFEST_PATH = Path(
    ".xsarena/snapshots/manifest_last.json"
)  # previous run (for diff)
CHUNKS_BASENAME = "snapshot_part_"

# ---------- Small utils ----------


def _normalize_path(root: Path, p: Path) -> str:
    rel = p.relative_to(root).as_posix()
    return rel


def _is_texty_name(name: str) -> bool:
    suffix = Path(name).suffix.lower()
    base = Path(name).name
    return suffix in TEXT_EXTS or base in TEXT_EXTS


def _looks_binary(sample: bytes) -> bool:
    if b"\x00" in sample:
        return True
    # Heuristic: too many non-printables
    text_chars = bytes({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
    nontext = sample.translate(None, text_chars)
    return len(nontext) / max(1, len(sample)) > 0.30


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_read_text(path: Path, max_bytes: int) -> Tuple[str, bool, int]:
    """
    Returns (text, truncated, bytes_read). Always returns UTF-8 text with errors replaced.
    """
    size = path.stat().st_size
    truncated = False
    to_read = min(size, max_bytes)
    with path.open("rb") as f:
        data = f.read(to_read)
        if size > max_bytes:
            truncated = True
    try:
        s = data.decode("utf-8", errors="replace")
    except Exception:
        s = data.decode("latin-1", errors="replace")
    # Normalize newlines to \n deterministically
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s, truncated, to_read


def _atomic_write_text(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(
        target.suffix + f".tmp-{os.getpid()}-{int(time.time()*1000)}"
    )
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)


def _clean_old_chunks(chunks_dir: Path) -> None:
    if not chunks_dir.exists():
        return
    for p in chunks_dir.glob(f"{CHUNKS_BASENAME}*"):
        try:
            p.unlink()
        except Exception:
            pass


def _git_info(root: Path) -> Dict[str, str]:
    try:
        rev = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        rev = ""
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
    except Exception:
        branch = ""
    return {"git_head": rev, "git_branch": branch}


def _matches_any(path_str: str, patterns: List[str]) -> bool:
    # Match on posix-style rel path; directory patterns end with /
    for pat in patterns:
        if pat.endswith("/"):
            # Directory. Match if path starts with that dir prefix
            # Use fnmatch for wildcard dirs too.
            if fnmatch.fnmatch(path_str + "/", pat):
                return True
            parts = path_str.split("/")
            # If pattern contains wildcards, try all prefixes
            for i in range(1, len(parts) + 1):
                if fnmatch.fnmatch("/".join(parts[:i]) + "/", pat):
                    return True
        else:
            if fnmatch.fnmatch(path_str, pat) or fnmatch.fnmatch(
                Path(path_str).name, pat
            ):
                return True
    return False


def _aa_series(n: int) -> List[str]:
    # Generate aa, ba, ca, ... za, then aa? For simplicity follow your existing existing aa, ba, ca pattern.
    letters = string.ascii_lowercase
    out = []
    for i in range(n):
        out.append(letters[i % 26] + "a")
    return out


# ---------- Core datatypes ----------


@dataclasses.dataclass(frozen=True)
class FileEntry:
    path: str  # POSIX relative path
    size: int
    sha256: str
    kind: str  # "text" or "binary"
    note: str = ""  # "truncated" etc.


@dataclasses.dataclass
class Manifest:
    root: str
    files: List[FileEntry]
    excludes: List[str]
    config: Dict[str, str]
    meta: Dict[
        str, str
    ]  # git info, created_at, etc. (created_at kept out of hash if determinism needed)

    def as_dict_for_hash(self) -> Dict:
        # Remove non-deterministic fields
        return {
            "root": self.root,
            "files": [dataclasses.asdict(f) for f in self.files],
            "excludes": self.excludes,
            "config": self.config,
        }

    def digest(self) -> str:
        s = json.dumps(self.as_dict_for_hash(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ---------- Builder ----------


class SnapshotBuilder:
    def __init__(
        self,
        root: Path,
        excludes: Optional[List[str]] = None,
        max_inline_bytes: int = DEFAULT_MAX_INLINE_BYTES,
        deterministic: bool = True,
    ):
        self.root = root.resolve()
        self.excludes = excludes or list(DEFAULT_EXCLUDES)
        self.max_inline_bytes = max_inline_bytes
        self.deterministic = deterministic

    def gather_files(self) -> List[Path]:
        paths: List[Path] = []
        for p in self.root.rglob("*"):
            if not p.is_file():
                continue
            rel = _normalize_path(self.root, p)
            # Skip hidden files at top-level? No—let patterns handle it.
            if _matches_any(rel, self.excludes):
                continue
            paths.append(p)
        paths.sort(key=lambda x: _normalize_path(self.root, x))
        return paths

    def build_manifest(self) -> Manifest:
        files: List[FileEntry] = []
        for p in self.gather_files():
            rel = _normalize_path(self.root, p)
            size = p.stat().st_size
            kind = "text"
            try:
                with p.open("rb") as f:
                    sample = f.read(4096)
                if _looks_binary(sample) and not _is_texty_name(rel):
                    kind = "binary"
            except Exception:
                kind = "binary"
            sha = _sha256_file(p) if p.exists() else "0" * 64
            note = ""
            if size > self.max_inline_bytes and kind == "text":
                note = f"TRUNCATED:{size}>={self.max_inline_bytes}"
            files.append(
                FileEntry(path=rel, size=size, sha256=sha, kind=kind, note=note)
            )

        meta = {}
        meta.update(_git_info(self.root))
        if not self.deterministic:
            meta["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cfg = {
            "max_inline_bytes": str(self.max_inline_bytes),
            "deterministic": str(self.deterministic),
        }
        return Manifest(
            root=str(self.root),
            files=files,
            excludes=self.excludes,
            config=cfg,
            meta=meta,
        )


# ---------- Formatting ----------


def _format_header(manifest: Manifest, message: str, summary: str) -> str:
    lines = []
    lines.append("=== XSArena Snapshot v3 ===")
    lines.append(f"ROOT: {manifest.root}")
    if manifest.meta.get("git_branch"):
        lines.append(f"GIT_BRANCH: {manifest.meta.get('git_branch')}")
    if manifest.meta.get("git_head"):
        lines.append(f"GIT_HEAD: {manifest.meta.get('git_head')}")
    lines.append(f"FILES: {len(manifest.files)}")
    total_bytes = sum(f.size for f in manifest.files)
    lines.append(f"TOTAL_BYTES: {total_bytes}")
    lines.append(f"MANIFEST_SHA256: {manifest.digest()}")
    if manifest.excludes:
        lines.append("EXCLUDES: " + ", ".join(manifest.excludes))
    lines.append("")
    if message:
        lines.append(">> MESSAGE_START")
        for mline in message.strip().splitlines():
            lines.append(f">> {mline}")
        lines.append(">> MESSAGE_END")
        lines.append("")
    if summary:
        lines.append(">> SUMMARY_START")
        lines.extend([">> " + s for s in summary.strip().splitlines()])
        lines.append(">> SUMMARY_END")
        lines.append("")
    return "\n".join(lines) + "\n"


def _format_file_section(
    root: Path, entry: FileEntry, max_inline_bytes: int
) -> Iterator[str]:
    # Header
    header = f"--- BEGIN FILE {entry.path} size={entry.size} sha256={entry.sha256} kind={entry.kind} {('note='+entry.note) if entry.note else ''}".strip()
    yield header + "\n"

    full_path = root / Path(entry.path)
    if entry.kind == "text":
        if entry.size <= max_inline_bytes:
            content, truncated, _ = _safe_read_text(full_path, max_inline_bytes)
            for line in content.splitlines():
                yield line + "\n"
            if truncated:
                yield f"... [TRUNCATED at {max_inline_bytes} bytes]\n"
        else:
            head_bytes = min(200_000, max_inline_bytes // 2)
            tail_bytes = min(200_000, max_inline_bytes - head_bytes)
            head_text, _, _ = _safe_read_text(full_path, head_bytes)
            yield f"[HEAD {head_bytes}B]\n"
            for line in head_text.splitlines():
                yield line + "\n"
            # Tail
            # Read tail by seeking from end
            try:
                with full_path.open("rb") as f:
                    f.seek(-tail_bytes, io.SEEK_END)
                    tail_data = f.read(tail_bytes)
                tail_text = (
                    tail_data.decode("utf-8", errors="replace")
                    .replace("\r\n", "\n")
                    .replace("\r", "\n")
                )
                yield f"[... TAIL {tail_bytes}B]\n"
                for line in tail_text.splitlines():
                    yield line + "\n"
            except Exception:
                yield "[TAIL_UNAVAILABLE]\n"
    else:
        yield f"[BINARY FILE: {entry.size} bytes, content omitted]\n"

    # Footer
    yield f"--- END FILE {entry.path}\n"


def _make_summary(manifest: Manifest, prev_manifest: Optional[Manifest]) -> str:
    total_files = len(manifest.files)
    total_bytes = sum(f.size for f in manifest.files)
    by_ext = Counter(Path(f.path).suffix.lower() for f in manifest.files)
    top_ext = ", ".join(
        f"{ext or '[no-ext]'}:{cnt}" for ext, cnt in by_ext.most_common(8)
    )
    largest = sorted(manifest.files, key=lambda f: f.size, reverse=True)[:8]
    largest_lines = [f"- {f.path} ({f.size}B)" for f in largest]

    diff_lines = []
    if prev_manifest:
        prev_map = {f.path: f for f in prev_manifest.files}
        curr_map = {f.path: f for f in manifest.files}
        added = sorted(set(curr_map) - set(prev_map))
        removed = sorted(set(prev_map) - set(curr_map))
        changed = sorted(
            p
            for p in (set(curr_map) & set(prev_map))
            if curr_map[p].sha256 != prev_map[p].sha256
        )

        def sample(lst):
            return lst[:8]

        diff_lines.append(
            f"Δ Added: {len(added)} | Removed: {len(removed)} | Changed: {len(changed)}"
        )
        if added:
            diff_lines.append("  Added: " + ", ".join(sample(added)))
        if removed:
            diff_lines.append("  Removed: " + ", ".join(sample(removed)))
        if changed:
            diff_lines.append("  Changed: " + ", ".join(sample(changed)))

    parts = [
        f"Files: {total_files} | Bytes: {total_bytes}",
        f"Top extensions: {top_ext or '(none)'}",
        "Largest files:",
        *largest_lines,
    ]
    if diff_lines:
        parts.append("Diff vs previous:")
        parts.extend(diff_lines)
    return "\n".join(parts)


# ---------- Chunker ----------


class Chunker:
    def __init__(self, limit: int):
        self.limit = limit
        self.chunks: List[str] = []
        self._current: List[str] = []
        self._len = 0

    def _flush(self):
        if self._current:
            self.chunks.append("".join(self._current))
            self._current = []
            self._len = 0

    def add_line(self, s: str):
        # If a single line exceeds limit, split line
        if len(s) > self.limit:
            start = 0
            while start < len(s):
                take = min(self.limit, len(s) - start)
                piece = s[start : start + take]
                self.add_line(piece)
                start += take
            return
        if self._len + len(s) > self.limit:
            self._flush()
        self._current.append(s)
        self._len += len(s)

    def add_section(self, it: Iterable[str]):
        for line in it:
            self.add_line(line)

    def finalize(self) -> List[str]:
        self._flush()
        return self.chunks


# ---------- IO + Orchestration ----------


def _load_manifest(path: Path) -> Optional[Manifest]:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    files = [FileEntry(**f) for f in data["files"]]
    return Manifest(
        root=data["root"],
        files=files,
        excludes=data["excludes"],
        config=data["config"],
        meta=data.get("meta", {}),
    )


def _save_manifest(path: Path, manifest: Manifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(
        {
            "root": manifest.root,
            "files": [dataclasses.asdict(f) for f in manifest.files],
            "excludes": manifest.excludes,
            "config": manifest.config,
            "meta": manifest.meta,
            "digest": manifest.digest(),
        },
        indent=2,
        sort_keys=True,
    )
    _atomic_write_text(path, content)


def write_snapshot(
    root: Path,
    out_file: Path,
    chunks_dir: Optional[Path],
    message: str,
    limit: int,
    excludes: List[str],
    deterministic: bool,
    max_inline_bytes: int,
) -> Tuple[Manifest, List[str]]:
    builder = SnapshotBuilder(root, excludes, max_inline_bytes, deterministic)
    prev = _load_manifest(LAST_MANIFEST_PATH) or _load_manifest(MANIFEST_PATH)
    manifest = builder.build_manifest()
    summary = _make_summary(manifest, prev)
    header = _format_header(manifest, message, summary)

    # Build chunker and feed header + files
    chunker = Chunker(limit=limit)
    chunker.add_section(header.splitlines(keepends=True))

    for entry in manifest.files:
        section = _format_file_section(root, entry, max_inline_bytes)
        # For very large file sections, split across chunks naturally
        chunker.add_section(section)

    chunks = chunker.finalize()
    if not chunks:
        chunks = ["(empty snapshot)\n"]

    # Prefix index into headers and append chunk metadata.
    total = len(chunks)
    chunk_names = _aa_series(total)
    chunk_wrapped: List[str] = []
    for idx, body in enumerate(chunks, 1):
        head = [
            f"== CHUNK {idx}/{total} = {CHUNKS_BASENAME}{chunk_names[idx-1]} ==",
            f"MANIFEST_SHA256: {manifest.digest()}",
            "",
        ]
        tail = [
            "",
            f"== END CHUNK {idx}/{total} ==",
        ]
        chunk_wrapped.append("\n".join(head) + "\n" + body + "\n".join(tail) + "\n")

    # Atomic write of single snapshot file (concatenation)
    snapshot_text = "".join(chunk_wrapped)
    _atomic_write_text(out_file, snapshot_text)

    # Write chunk files if requested
    written_paths: List[str] = []
    if chunks_dir:
        chunks_dir = chunks_dir.expanduser().resolve()
        chunks_dir.mkdir(parents=True, exist_ok=True)
        _clean_old_chunks(chunks_dir)
        for idx, content in enumerate(chunk_wrapped, 1):
            name = f"{CHUNKS_BASENAME}{chunk_names[idx-1]}"
            p = chunks_dir / name
            _atomic_write_text(p, content)
            written_paths.append(str(p))

    # Save manifest (current) and roll last
    if MANIFEST_PATH.exists():
        shutil.copy2(MANIFEST_PATH, LAST_MANIFEST_PATH)
    _save_manifest(MANIFEST_PATH, manifest)
    return manifest, written_paths


def verify_snapshot(out_file: Path, chunks_dir: Optional[Path]) -> Tuple[bool, str]:
    # Verify manifest hash markers are consistent
    texts: List[str] = []
    if out_file.exists():
        texts.append(out_file.read_text(encoding="utf-8", errors="replace"))
    if chunks_dir and Path(chunks_dir).exists():
        parts = sorted(Path(chunks_dir).glob(f"{CHUNKS_BASENAME}*"))
        for p in parts:
            texts.append(p.read_text(encoding="utf-8", errors="replace"))

    if not texts:
        return False, "No snapshot files found"

    # Collect all MANIFEST_SHA256 line values and ensure they're unanimous.
    hashes = set()
    for t in texts:
        for line in t.splitlines():
            if line.startswith("MANIFEST_SHA256:"):
                hashes.add(line.split(":", 1)[1].strip())
    if not hashes:
        return False, "No MANIFEST_SHA256 markers present"
    if len(hashes) > 1:
        return False, f"Mismatch in MANIFEST_SHA256 markers: {hashes}"

    # Recompute the digest from manifest.json and compare
    manifest = _load_manifest(MANIFEST_PATH)
    if not manifest:
        return False, "manifest.json missing"
    want = manifest.digest()
    got = list(hashes)[0]
    if want != got:
        return False, f"Digest mismatch: manifest.json={want} vs snapshot markers={got}"
    return True, "OK"


def diff_manifest() -> str:
    curr = _load_manifest(MANIFEST_PATH)
    prev = _load_manifest(LAST_MANIFEST_PATH)
    if not curr or not prev:
        return "No diff available (missing manifests)"
    prev_map = {f.path: f for f in prev.files}
    curr_map = {f.path: f for f in curr.files}
    added = sorted(set(curr_map) - set(prev_map))
    removed = sorted(set(prev_map) - set(curr_map))
    changed = sorted(
        p
        for p in (set(curr_map) & set(prev_map))
        if curr_map[p].sha256 != prev_map[p].sha256
    )
    lines = []
    lines.append(f"Added ({len(added)}):")
    lines.extend(f"  + {p}" for p in added[:100])
    lines.append(f"Removed ({len(removed)}):")
    lines.extend(f"  - {p}" for p in removed[:100])
    lines.append(f"Changed ({len(changed)}):")
    lines.extend(f"  * {p}" for p in changed[:100])
    return "\n".join(lines)


# ---------- CLI ----------


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="xsarena-snapshot-pro",
        description="Deterministic snapshot + chunker (Pro)",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("write", help="Write snapshot and chunks")
    w.add_argument("--root", default=".", type=str, help="Root directory to snapshot")
    w.add_argument(
        "--out",
        default=str(Path.home() / "snapshot.txt"),
        type=str,
        help="Path to write unified snapshot file",
    )
    w.add_argument(
        "--chunks",
        default=str(Path.home() / "snapshot_chunks"),
        type=str,
        help="Directory for chunk files (set to '' to skip)",
    )
    w.add_argument(
        "--limit",
        default=DEFAULT_LIMIT,
        type=int,
        help="Max characters per chunk (hard cap)",
    )
    w.add_argument(
        "--message", default="", type=str, help="Message to embed into index chunk"
    )
    w.add_argument(
        "--message-file", default="", type=str, help="Read message from file"
    )
    w.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Add an exclude pattern (can repeat)",
    )
    w.add_argument(
        "--no-default-excludes",
        action="store_true",
        help="Do not include built-in excludes",
    )
    w.add_argument(
        "--max-inline-bytes",
        default=DEFAULT_MAX_INLINE_BYTES,
        type=int,
        help="Max file bytes to inline (text). Larger text files get head/tail only.",
    )
    w.add_argument(
        "--non-deterministic",
        action="store_true",
        help="Include created_at to aid human debugging (breaks bitwise determinism)",
    )

    v = sub.add_parser("verify", help="Verify snapshot markers match manifest")
    v.add_argument("--out", default=str(Path.home() / "snapshot.txt"), type=str)
    v.add_argument("--chunks", default=str(Path.home() / "snapshot_chunks"), type=str)

    d = sub.add_parser("diff", help="Show diff vs previous manifest")

    args = ap.parse_args(argv)

    if args.cmd == "write":
        root = Path(args.root).resolve()
        out = Path(args.out).expanduser().resolve()
        chunks_dir = Path(args.chunks).expanduser().resolve() if args.chunks else None

        excludes = [] if args.no_default_excludes else list(DEFAULT_EXCLUDES)
        excludes.extend(args.exclude or [])

        message = args.message or ""
        if args.message_file:
            try:
                message = Path(args.message_file).read_text(encoding="utf-8")
            except Exception as e:
                print(f"Warning: failed to read message file: {e}", file=sys.stderr)

        manifest, written = write_snapshot(
            root=root,
            out_file=out,
            chunks_dir=chunks_dir,
            message=message,
            limit=int(args.limit),
            excludes=excludes,
            deterministic=not args.non_deterministic,
            max_inline_bytes=int(args.max_inline_bytes),
        )
        ok, why = verify_snapshot(out, chunks_dir)
        print(f"Wrote snapshot to: {out}")
        if written:
            print(f"Chunks: {len(written)} files under {chunks_dir}")
        print(f"Manifest: {MANIFEST_PATH} (digest={manifest.digest()})")
        print(f"Verify: {ok} ({why})")
        return 0 if ok else 2

    elif args.cmd == "verify":
        out = Path(args.out).expanduser().resolve()
        chunks_dir = Path(args.chunks).expanduser().resolve() if args.chunks else None
        ok, why = verify_snapshot(out, chunks_dir)
        print(f"Verify: {ok} ({why})")
        return 0 if ok else 2

    elif args.cmd == "diff":
        print(diff_manifest())
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
