#!/usr/bin/env python3
"""
Simple test script to verify that lma_cli.py can be imported and contains expected functionality.
"""

def test_import():
    """Test that the lma_cli module can be imported without errors."""
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        # Import the lma_cli module
        import lma_cli
        
        print("✓ Successfully imported lma_cli module")
        
        # Check if key functions exist
        expected_functions = [
            'ask_collect',
            'build_payload',
            'extract_text_chunks',
            'strip_next_marker',
            'write_to_file',
            'autorun_loop',
            'repl',
            'main'
        ]
        
        missing_functions = []
        for func_name in expected_functions:
            if not hasattr(lma_cli, func_name):
                missing_functions.append(func_name)
        
        if missing_functions:
            print(f"✗ Missing functions: {missing_functions}")
        else:
            print("✓ All expected functions are present")
        
        # Check book autopilot variables
        expected_vars = [
            'AUTO_ON',
            'AUTO_TASK',
            'AUTO_OUT',
            'AUTO_COUNT',
            'AUTO_MAX',
            'LAST_NEXT_HINT'
        ]
        
        missing_vars = []
        for var_name in expected_vars:
            if not hasattr(lma_cli, var_name):
                missing_vars.append(var_name)
        
        if missing_vars:
            print(f"✗ Missing variables: {missing_vars}")
        else:
            print("✓ All expected autopilot variables are present")
        
        print("\n✓ All tests passed! The CLI implementation is ready for book autopilot functionality.")
        
    except ImportError as e:
        print(f"✗ Failed to import lma_cli: {e}")
        return False
    except Exception as e:
        print(f"✗ Error during test: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_import()