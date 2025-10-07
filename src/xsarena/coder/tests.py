import pathlib


def create_test_skeleton(module_path: str):
    """Create a basic pytest skeleton for a module."""
    # Convert module path to test path
    module_path = pathlib.Path(module_path)

    # If the path is like src/xsarena/core/engine.py, the test should be tests/test_engine.py
    if "src" in module_path.parts and "xsarena" in module_path.parts:
        # Extract the relative path from xsarena onwards
        try:
            xsarena_idx = module_path.parts.index("xsarena")
            rel_parts = module_path.parts[xsarena_idx + 1 :]  # Everything after xsarena
            module_name = rel_parts[-1].replace(".py", "")  # Get module name without .py
            test_name = f"test_{module_name}"

            # Create tests directory if it doesn't exist
            tests_dir = pathlib.Path("tests")
            tests_dir.mkdir(exist_ok=True)

            # Create test file
            test_file = tests_dir / f"{test_name}.py"

            # Get the module import path
            import_path = ".".join(rel_parts)  # xsarena.core.engine

            if not test_file.exists():
                skeleton_content = f'''import pytest
from {import_path} import *

def test_placeholder():
    """Basic placeholder test - replace with real tests"""
    # Add your tests here
    assert True
'''
                test_file.write_text(skeleton_content, encoding="utf-8")
                return str(test_file)
            else:
                return f"Test file already exists: {test_file}"
        except ValueError:
            # If 'xsarena' is not in path, use a more generic approach
            module_name = module_path.stem
            test_name = f"test_{module_name}"
            tests_dir = pathlib.Path("tests")
            tests_dir.mkdir(exist_ok=True)
            test_file = tests_dir / f"{test_name}.py"

            if not test_file.exists():
                skeleton_content = f'''import pytest
import {module_name}

def test_placeholder():
    """Basic placeholder test - replace with real tests"""
    # Add your tests here
    assert True
'''
                test_file.write_text(skeleton_content, encoding="utf-8")
                return str(test_file)
            else:
                return f"Test file already exists: {test_file}"
    else:
        # For other paths, create a generic test
        module_name = module_path.stem
        test_name = f"test_{module_name}"
        tests_dir = pathlib.Path("tests")
        tests_dir.mkdir(exist_ok=True)
        test_file = tests_dir / f"{test_name}.py"

        if not test_file.exists():
            skeleton_content = f'''import pytest
import {module_name}

def test_placeholder():
    """Basic placeholder test - replace with real tests"""
    # Add your tests here
    assert True
'''
            test_file.write_text(skeleton_content, encoding="utf-8")
            return str(test_file)
        else:
            return f"Test file already exists: {test_file}"


def has_tests(module_path: str) -> bool:
    """Check if a module already has tests."""
    module_path = pathlib.Path(module_path)
    module_name = module_path.stem
    test_name = f"test_{module_name}"
    test_file = pathlib.Path("tests") / f"{test_name}.py"
    return test_file.exists()
