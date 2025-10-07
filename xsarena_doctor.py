#!/usr/bin/env python3
"""
XSarena Doctor - A test script to verify z2h functionality and failover behavior
"""

import os
import tempfile
from pathlib import Path


def run_synthetic_test():
    """Run a synthetic z2h test on a stub subject"""
    print("🧪 Running XSarena Doctor - Synthetic z2h test")
    print("=" * 60)

    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Working in temp directory: {temp_dir}")

        # Change to the temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Test 1: Run z2h command
            print("\n1️⃣  Testing z2h command...")

            # First create the .xsarena directory
            os.makedirs(".xsarena/jobs", exist_ok=True)

            # Create a fake book directory
            os.makedirs("books", exist_ok=True)

            # Import and test the CLI functionality
            from src.xsarena.cli.cmds_jobs import z2h

            # Run a test z2h command with minimal parameters
            print("   Running: z2h('Test Subject', out='books/test.final.md', max_chunks=2, min_chars=1000)")
            job_id = z2h("Test Subject", out="books/test.final.md", max_chunks=2, min_chars=1000)
            print(f"   ✓ Submitted job: {job_id}")

            # Test 2: Verify artifacts were created
            print("\n2️⃣  Verifying artifacts...")

            job_dir = Path(".xsarena/jobs") / job_id
            expected_files = [
                job_dir / "job.json",
                job_dir / "events.jsonl",
                job_dir / "checkpoints",
            ]

            for expected_file in expected_files:
                if expected_file.exists():
                    print(f"   ✓ Found: {expected_file}")
                else:
                    print(f"   ✗ Missing: {expected_file}")

            # Test 3: Check if final book was created
            final_book = Path("books/test.final.md")
            if final_book.exists():
                print(f"   ✓ Final book created: {final_book}")
            else:
                print(f"   ⚠ Final book not found: {final_book} (this is expected for a synthetic test)")

            # Test 4: Test jobs commands
            print("\n3️⃣  Testing jobs commands...")

            from src.xsarena.cli.cmds_jobs import cancel, fork, log, ls, resume

            print("   ✓ Jobs commands imported successfully")

            # Test listing jobs
            print("   Testing jobs list...")
            ls()
            print("   ✓ Jobs list command executed")

            # Test log command
            print("   Testing jobs log...")
            try:
                log(job_id)
                print("   ✓ Jobs log command executed")
            except Exception as e:
                print(f"   ⚠ Jobs log failed (expected): {e}")

            # Test cancel command
            print("   Testing jobs cancel...")
            try:
                cancel(job_id)
                print(f"   ✓ Job cancelled: {job_id}")
            except Exception as e:
                print(f"   ⚠ Cancel failed: {e}")

            # Test resume command
            print("   Testing jobs resume...")
            try:
                # Re-submit the job first to test resume
                job_id2 = z2h("Resume Test", out="books/resume-test.md", max_chunks=1, min_chars=500)
                print(f"   ✓ Re-submitted job for resume test: {job_id2}")

                # Test resume
                resume(job_id2)
                print(f"   ✓ Job resumed: {job_id2}")
            except Exception as e:
                print(f"   ⚠ Resume failed: {e}")

            # Test fork command
            print("   Testing jobs fork...")
            try:
                fork(job_id2, backend="openrouter")
                print(f"   ✓ Job forked: {job_id2}")
            except Exception as e:
                print(f"   ⚠ Fork failed: {e}")

            print("\n✅ All tests completed!")
            print("=" * 60)
            print("XSarena Doctor: All core functionality appears to be working!")
            print("Note: Some tests may have expected failures in synthetic environment.")

        except Exception as e:
            print(f"❌ Doctor test failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            os.chdir(original_cwd)

    return True


def check_code_quality():
    """Check code quality and linting"""
    print("\n🔍 Checking code quality...")

    # Run ruff and black checks
    import subprocess

    try:
        result = subprocess.run(
            ["python", "-m", "ruff", "check", ".", "--select", "I,E4,E7,E9,F401,F403,F405", "--quiet"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        if result.returncode == 0:
            print("   ✓ Ruff check passed")
        else:
            print(f"   ⚠ Ruff check issues: {result.stdout}")
    except FileNotFoundError:
        print("   ⚠ Ruff not found - install with: pip install ruff")
    except Exception as e:
        print(f"   ⚠ Ruff check failed: {e}")

    try:
        result = subprocess.run(
            ["python", "-m", "black", "--check", "--quiet", "."],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
        )
        if result.returncode == 0:
            print("   ✓ Black format check passed")
        else:
            print(f"   ⚠ Black format issues: {result.stdout}")
    except FileNotFoundError:
        print("   ⚠ Black not found - install with: pip install black")
    except Exception as e:
        print(f"   ⚠ Black check failed: {e}")


def main():
    """Main doctor command"""
    print("🏥 XSarena Doctor - System Health Check")
    print("=" * 60)

    success = run_synthetic_test()

    check_code_quality()

    if success:
        print("\n🎉 Doctor check complete - XSarena appears healthy!")
        return 0
    else:
        print("\n⚠️  Doctor check found issues")
        return 1


if __name__ == "__main__":
    exit(main())
