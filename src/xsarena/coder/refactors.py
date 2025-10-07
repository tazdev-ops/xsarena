import re
from typing import Tuple


def wrap_fstring_long(line: str) -> str:
    """Wrap a long f-string into multi-line format preserving f-string expressions."""
    if 'f"' not in line and "f'" not in line:
        return line  # Not an f-string

    # Check if the line is long enough to warrant wrapping
    if len(line) <= 120:
        return line

    # Find the f-string content and preserve expressions
    # This is a simplified approach that identifies expressions inside braces
    # and wraps them safely
    parts = []
    i = 0
    in_fstring = False
    start_quote = None

    while i < len(line):
        char = line[i]

        # Check for f-string start
        if not in_fstring and char.lower() == "f" and i + 1 < len(line):
            if line[i + 1] in ['"', "'", '"', "'"]:
                in_fstring = True
                start_quote = line[i + 1]
                parts.append(line[i : i + 2])  # f"
                i += 2
            elif line[i + 1] in ["r", "b"] and i + 2 < len(line) and line[i + 2] in ['"', "'", '"', "'"]:
                # Handle f-strings with r or b prefixes
                in_fstring = True
                start_quote = line[i + 2]
                parts.append(line[i : i + 3])  # fr, fb, etc.
                i += 3
            else:
                parts.append(char)
                i += 1
        elif in_fstring and char == start_quote:
            # End of f-string
            parts.append(char)
            in_fstring = False
            i += 1
        elif in_fstring and char == "{":
            # Start of expression
            expr_start = i
            brace_count = 1
            i += 1
            while i < len(line) and brace_count > 0:
                if line[i] == "{":
                    brace_count += 1
                elif line[i] == "}":
                    brace_count -= 1
                i += 1

            if brace_count == 0:  # Balanced braces
                expr = line[expr_start:i]
                # Check if this is the last expression in the f-string
                remaining = line[i:].lstrip()
                if remaining.startswith(start_quote) and len("".join(parts) + expr + remaining) > 120:
                    # Need to wrap
                    parts.append("\n    " + expr + "\n    + ")
                else:
                    parts.append(expr)
            else:
                # Unbalanced braces, add as is
                parts.append(char)
                i += 1
        else:
            parts.append(char)
            i += 1

    result = "".join(parts)

    # If the line is still too long, wrap it with parentheses
    if len(result) > 120:
        # Find the f-string start and wrap with parentheses
        f_match = re.search(r'(f[rb]?"|f[rb]?\')', result)
        if f_match:
            pos = f_match.end()
            content_start = result[:pos]
            content_end = result[pos:]
            # Wrap in parentheses for multi-line f-strings
            wrapped = content_start + "(\n    " + content_end.replace('"', '"+\n    "', 1).replace("'", "+'\n    ", 1)
            # Replace the closing quote
            wrapped = wrapped.replace('"+\n    "', '"+\n    + "', 1) + "\n)"
            return wrapped

    return result


def verticalize_call(code: str) -> str:
    """Split a long function call into multi-line format with trailing commas."""
    # Find function calls that are too long
    lines = code.split("\n")
    result_lines = []

    for line in lines:
        if len(line) > 120 and "(" in line and ")" in line:
            # Find the function call
            open_paren_idx = line.find("(")
            if open_paren_idx != -1:
                function_part = line[:open_paren_idx]
                args_part = line[open_paren_idx:]

                # Split arguments by commas, but be careful with nested parentheses
                args = extract_args(args_part)

                if len(args) > 1:  # Only if there are multiple arguments
                    indented_args = [f"    {arg.strip()}" for arg in args if arg.strip()]
                    if indented_args:
                        # Add trailing comma to all but the last argument
                        for i in range(len(indented_args) - 1):
                            if not indented_args[i].endswith(","):
                                indented_args[i] += ","

                        # Join with newlines
                        formatted_args = ",\n".join(indented_args) + "\n)"
                        result_line = f"{function_part}(\n{formatted_args}"
                        result_lines.append(result_line)
                        continue

        result_lines.append(line)

    return "\n".join(result_lines)


def extract_args(args_str: str) -> list:
    """Extract arguments from a function call string, handling nested parentheses."""
    args = []
    paren_count = 0
    current_arg_start = 1  # Skip the opening parenthesis

    i = 1  # Start after the opening parenthesis
    while i < len(args_str):
        char = args_str[i]

        if char == "(":
            paren_count += 1
        elif char == ")":
            paren_count -= 1
            if paren_count < 0:  # This is the closing paren for the function call
                # Add the last argument
                if i > current_arg_start:
                    args.append(args_str[current_arg_start:i])
                break
        elif char == "," and paren_count == 0:
            # Found an argument separator
            args.append(args_str[current_arg_start:i])
            current_arg_start = i + 1  # Skip the comma

        i += 1

    return args


def fix_long_line(code: str, max_len: int = 120) -> Tuple[str, bool]:
    """Apply common refactoring patterns to fix long lines."""
    changed = False

    # Check if we need to wrap f-strings
    if 'f"' in code or "f'" in code:
        new_code = wrap_fstring_long(code)
        if new_code != code:
            code = new_code
            changed = True

    # Check for long function calls
    if "(" in code and ")" in code and len(code) > max_len:
        new_code = verticalize_call(code)
        if new_code != code:
            code = new_code
            changed = True

    return code, changed
