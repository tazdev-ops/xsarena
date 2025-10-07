import pathlib
import subprocess


def ensure_branch(branch: str = "xsarena/coder/default") -> bool:
    """Create or switch to a branch, creating from current HEAD if it doesn't exist."""
    try:
        # Check if branch exists
        result = subprocess.run(
            ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
            capture_output=True,
            text=True,
            cwd=pathlib.Path().resolve(),
        )
        if result.returncode != 0:
            # Branch doesn't exist, create it
            result = subprocess.run(
                ["git", "checkout", "-b", branch], capture_output=True, text=True, cwd=pathlib.Path().resolve()
            )
        else:
            # Branch exists, switch to it
            result = subprocess.run(
                ["git", "checkout", branch], capture_output=True, text=True, cwd=pathlib.Path().resolve()
            )

        return result.returncode == 0
    except Exception:
        return False


def commit(message: str) -> bool:
    """Commit current changes with message."""
    try:
        result = subprocess.run(["git", "add", "."], capture_output=True, text=True, cwd=pathlib.Path().resolve())
        if result.returncode != 0:
            return False

        result = subprocess.run(
            ["git", "commit", "-m", message], capture_output=True, text=True, cwd=pathlib.Path().resolve()
        )
        return result.returncode == 0
    except Exception:
        return False


def stash_save(message: str = "xsarena coder stash") -> bool:
    """Save current changes to stash."""
    try:
        result = subprocess.run(
            ["git", "stash", "push", "-m", message], capture_output=True, text=True, cwd=pathlib.Path().resolve()
        )
        return result.returncode == 0
    except Exception:
        return False


def stash_apply() -> bool:
    """Apply latest stash."""
    try:
        result = subprocess.run(["git", "stash", "pop"], capture_output=True, text=True, cwd=pathlib.Path().resolve())
        return result.returncode == 0
    except Exception:
        return False


def get_diff(file_path: str) -> str:
    """Get unified diff for a specific file (limited to 400 lines)."""
    try:
        result = subprocess.run(
            ["git", "diff", file_path], capture_output=True, text=True, cwd=pathlib.Path().resolve()
        )
        if result.returncode == 0:
            lines = result.stdout.split("\n")
            if len(lines) > 400:
                return "\n".join(lines[:400]) + "\n... [truncated]"
            return result.stdout
        return ""
    except Exception:
        return ""


def get_git_status() -> str:
    """Get git status --porcelain output."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, cwd=pathlib.Path().resolve()
        )
        return result.stdout
    except Exception:
        return ""


def get_current_branch() -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, cwd=pathlib.Path().resolve()
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return ""
    except Exception:
        return ""


def get_last_commit_info() -> tuple[str, str]:
    """Get last commit hash and subject."""
    try:
        hash_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=pathlib.Path().resolve()
        )
        subject_result = subprocess.run(
            ["git", "log", "-1", "--pretty=%s"], capture_output=True, text=True, cwd=pathlib.Path().resolve()
        )

        commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else ""
        commit_subject = subject_result.stdout.strip() if subject_result.returncode == 0 else ""

        return commit_hash, commit_subject
    except Exception:
        return "", ""
