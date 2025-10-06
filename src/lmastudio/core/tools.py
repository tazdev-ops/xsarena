"""File system and command tools for LMASudio."""

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
    if path_jail:
        safe_path = path_jail.resolve_path(path)
    else:
        safe_path = Path(path)

    if not safe_path.exists():
        raise FileNotFoundError(f"Directory does not exist: {safe_path}")

    if not safe_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {safe_path}")

    return [str(item) for item in safe_path.iterdir()]


def read_file(filepath: str, path_jail: Optional[PathJail] = None) -> str:
    """Read a file safely."""
    if path_jail:
        safe_path = path_jail.resolve_path(filepath)
    else:
        safe_path = Path(filepath)

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
    if path_jail:
        safe_path = path_jail.resolve_path(filepath)
    else:
        safe_path = Path(filepath)

    # Create parent directories if they don't exist
    safe_path.parent.mkdir(parents=True, exist_ok=True)

    with open(safe_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def append_file(
    filepath: str, content: str, path_jail: Optional[PathJail] = None
) -> bool:
    """Append content to a file safely."""
    if path_jail:
        safe_path = path_jail.resolve_path(filepath)
    else:
        safe_path = Path(filepath)

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
