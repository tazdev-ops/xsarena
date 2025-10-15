"""Coder mode for XSArena."""

from ..core.engine import Engine
from ..core.templates import SYSTEM_PROMPTS
from ..core.tools import PathJail, append_file, list_dir, read_file, run_cmd, write_file


class CoderMode:
    """Handles coding functionality with file system tools."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.path_jail = PathJail("./workspace")  # Default workspace jail
        self.engine.set_tools(
            [
                self.list_dir,
                self.read_file,
                self.write_file,
                self.append_file,
                self.run_cmd,
            ]
        )

    async def list_dir(self, path: str) -> str:
        """List directory contents."""
        try:
            contents = list_dir(path, self.path_jail)
            return "\n".join(contents)
        except Exception as e:
            return f"Error listing directory: {e}"

    async def read_file(self, filepath: str) -> str:
        """Read a file."""
        try:
            content = read_file(filepath, self.path_jail)
            return content
        except Exception as e:
            return f"Error reading file: {e}"

    async def write_file(self, filepath: str, content: str) -> str:
        """Write content to a file."""
        try:
            success = write_file(filepath, content, self.path_jail)
            return f"File written successfully: {success}"
        except Exception as e:
            return f"Error writing file: {e}"

    async def append_file(self, filepath: str, content: str) -> str:
        """Append content to a file."""
        try:
            success = append_file(filepath, content, self.path_jail)
            return f"Content appended successfully: {success}"
        except Exception as e:
            return f"Error appending to file: {e}"

    async def run_cmd(self, cmd: str) -> str:
        """Run a command."""
        try:
            import shlex

            cmd_parts = shlex.split(cmd)
            result = await run_cmd(cmd_parts)
            return f"Return code: {result['returncode']}\nStdout: {result['stdout']}\nStderr: {result['stderr']}"
        except Exception as e:
            return f"Error running command: {e}"

    async def code_project(self, requirements: str, language: str = "python") -> str:
        """Generate a complete code project based on requirements."""
        prompt = f"""Generate a complete {language} project based on these requirements:

{requirements}

Create the necessary files and structure. Include appropriate comments and follow best practices for {language}."""

        system_prompt = SYSTEM_PROMPTS["coder"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def fix_code(self, code: str, issue: str) -> str:
        """Fix issues in code."""
        prompt = f"""Fix this issue in the code:

Issue: {issue}

Code:
{code}

Provide the corrected code with explanations of the changes made."""

        system_prompt = SYSTEM_PROMPTS["coder"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def review_code(self, code: str, language: str = "python") -> str:
        """Review code for best practices."""
        prompt = f"""Review this {language} code for best practices, security issues, and optimization opportunities:

{code}

Provide detailed feedback on improvements."""

        system_prompt = SYSTEM_PROMPTS["coder"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def add_feature(self, existing_code: str, feature_description: str) -> str:
        """Add a feature to existing code."""
        prompt = f"""Add this feature to the existing code:

Feature: {feature_description}

Existing code:
{existing_code}

Provide the updated code with the new feature implemented."""

        system_prompt = SYSTEM_PROMPTS["coder"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    async def debug_code(self, code: str, error_message: str) -> str:
        """Debug code based on error message."""
        prompt = f"""Debug this code based on the error message:

Error message: {error_message}

Code:
{code}

Identify the issue and provide a fix."""

        system_prompt = SYSTEM_PROMPTS["coder"]
        return await self.engine.send_and_collect(prompt, system_prompt)

    def set_workspace(self, path: str):
        """Set the workspace path jail."""
        self.path_jail = PathJail(path)
