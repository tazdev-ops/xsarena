from typer.testing import CliRunner

from xsarena.cli.main import app

runner = CliRunner()


def test_root_help():
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    assert "book" in r.output
    assert "debug" in r.output


def test_all_commands_show_help():
    # Get all top-level command names from the help text
    result = runner.invoke(app, ["--help"])
    lines = result.stdout.splitlines()
    in_commands_section = False
    commands = []
    for line in lines:
        if "Commands" in line:
            in_commands_section = True
            continue
        if in_commands_section and "│" in line and not line.strip().startswith("│ --"):
            # Split the line by the table separator
            parts = line.split("│")
            if len(parts) >= 3:
                # The command is in the second part (index 1)
                command_part = parts[1] if len(parts) > 1 else ""

                # Check if this is a continuation line by seeing if the command part starts with significant spaces
                # Real commands start relatively early in the column, continuation lines start with many spaces
                # A real command line looks like: ' command_name   description...'
                # A continuation line looks like: '               more_description...'
                if (
                    command_part.strip()
                ):  # Only process if there's content in the command column
                    # Check if the command column starts with significant whitespace (indicating continuation)
                    # We'll assume that if there are more than 15 leading spaces, it's a continuation
                    leading_spaces = len(command_part) - len(command_part.lstrip())
                    if leading_spaces <= 10:  # Real commands have fewer leading spaces
                        command = (
                            command_part.strip().split()[0]
                            if command_part.strip().split()
                            else ""
                        )
                        # Only add real commands, not continuation lines from long descriptions
                        if (
                            command
                            and command not in ["help", "Commands"]
                            and len(command) > 1
                        ):
                            # Check if the command looks like a valid CLI command (alphanumeric + hyphens/underscores)
                            if all(c.isalnum() or c in ["-", "_"] for c in command):
                                commands.append(command)
        # Stop when we reach the end of the commands table
        if in_commands_section and "╰" in line:
            break

    # Remove duplicates while preserving order
    unique_commands = []
    for cmd in commands:
        if cmd not in unique_commands:
            unique_commands.append(cmd)

    # Test the --help flag for each discovered command
    for command in unique_commands:
        if command == "help":
            continue  # 'help' command is special
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0, f"Command '{command}' --help failed"
