"""File system and command tools for XSArena."""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional


class PathJail:
    """Restricts file operations to a specific directory tree."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path).resolve()

    def resolve_path(self, path: str) -> Path:
        """Resolve a path within the jail."""
        base = self.base_path
        target = (base / path).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            raise ValueError(f"Path {path} escapes the jail")
        return target


def list_dir(path: str, path_jail: Optional[PathJail] = None) -> List[str]:
    """List directory contents safely."""
    safe_path = path_jail.resolve_path(path) if path_jail else Path(path)

    if not safe_path.exists():
        raise FileNotFoundError(f"Directory does not exist: {safe_path}")

    if not safe_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {safe_path}")

    return [str(item) for item in safe_path.iterdir()]


def read_file(filepath: str, path_jail: Optional[PathJail] = None) -> str:
    """Read a file safely."""
    safe_path = path_jail.resolve_path(filepath) if path_jail else Path(filepath)

    if not safe_path.exists():
        raise FileNotFoundError(f"File does not exist: {safe_path}")

    if not safe_path.is_file():
        raise IsADirectoryError(f"Path is a directory, not a file: {safe_path}")

    with open(safe_path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(
    filepath: str, content: str, path_jail: Optional[PathJail] = None
) -> bool:
    """Write content to a file safely."""
    safe_path = path_jail.resolve_path(filepath) if path_jail else Path(filepath)

    # Create parent directories if they don't exist
    safe_path.parent.mkdir(parents=True, exist_ok=True)

    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def append_file(
    filepath: str, content: str, path_jail: Optional[PathJail] = None
) -> bool:
    """Append content to a file safely."""
    safe_path = path_jail.resolve_path(filepath) if path_jail else Path(filepath)

    # Create parent directories if they don't exist
    safe_path.parent.mkdir(parents=True, exist_ok=True)

    with open(safe_path, "a", encoding="utf-8") as f:
        f.write(content)

    return True


async def run_cmd(cmd: List[str], timeout: int = 30) -> Dict[str, str]:
    """Run a command safely with timeout."""
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            return {
                "returncode": process.returncode,
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
            }
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
            }
    except Exception as e:
        return {"returncode": -1, "stdout": "", "stderr": str(e)}


def get_safe_path(filepath: str, base_dir: str = "./") -> str:
    """Get a safe path that's restricted to the base directory."""
    base = Path(base_dir).resolve()
    target = (base / filepath).resolve()

    try:
        target.relative_to(base)
    except ValueError:
        raise ValueError(f"Path {filepath} escapes the base directory")

    return str(target)


def apply_patch(path: str, patch: str, path_jail: Optional[PathJail] = None) -> dict:
    """Apply a unified diff patch to a file."""
    p = path_jail.resolve_path(path) if path_jail else Path(path)
    if not p.is_file():
        return {"ok": False, "error": "file_not_found"}
    try:
        import subprocess

        proc = subprocess.run(
            ["patch", str(p)],
            input=patch,
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr}
        return {"ok": True, "details": proc.stdout}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def search_text(
    path: str, query: str, regex: bool = False, path_jail: Optional[PathJail] = None
) -> dict:
    """Search for a string or regex in a file or directory."""
    p = path_jail.resolve_path(path) if path_jail else Path(path)
    try:
        import re

        hits = []
        files_to_search = [p] if p.is_file() else list(p.rglob("*"))

        for file in files_to_search:
            if file.is_file() and file.stat().st_size < 1_000_000:  # Safety limit
                try:
                    content = file.read_text(encoding="utf-8")
                    for i, line in enumerate(content.splitlines(), 1):
                        if (regex and re.search(query, line)) or (
                            not regex and query in line
                        ):
                            hits.append(
                                {"file": str(file), "line": i, "text": line[:200]}
                            )
                            if len(hits) >= 100:  # Result limit
                                return {"ok": True, "results": hits, "truncated": True}
                except Exception:
                    continue  # Skip unreadable files
        return {"ok": True, "results": hits}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def run_tests(args: str = "-q", path_jail: Optional[PathJail] = None) -> dict:
    """Run pytest with given arguments."""
    try:
        result = await run_cmd(["pytest"] + args.split())
        return {
            "ok": result["returncode"] == 0,
            "summary": result["stdout"],
            "details": result["stderr"],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def diff_file(filepath: str, path_jail: Optional[PathJail] = None) -> str:
    """Show unified diff of a file compared to its original state."""
    try:
        safe_path = path_jail.resolve_path(filepath) if path_jail else Path(filepath)

        if not safe_path.exists():
            return f"[diff] File does not exist: {safe_path}"

        # For now, we'll just return a placeholder diff
        # In a real implementation, this would compare with a backup or git repo
        with open(safe_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Return a simple representation of the file content as a diff
        lines = content.split("\n")
        diff_lines = []
        for _i, line in enumerate(lines, 1):
            diff_lines.append(f"+{line}")  # Mark all lines as additions for simplicity

        return "\n".join(diff_lines)
    except Exception as e:
        return f"[diff] Error generating diff: {str(e)}"
