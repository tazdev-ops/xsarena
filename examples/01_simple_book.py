"""
Generate a simple book programmatically.
"""
import asyncio
import subprocess

# Fallback import for non-v2 layouts
try:
    from xsarena.core.v2_orchestrator.orchestrator import Orchestrator
    from xsarena.core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset
except ImportError:
    # If RunSpec/LengthPreset/SpanPreset aren't available, prefer the CLI:
    print("V2 orchestrator not available, using CLI fallback")
    subprocess.run(
        [
            "xsarena",
            "run",
            "book",
            "Python Programming Basics",
            "--length",
            "long",
            "--span",
            "medium",
            "--out",
            "./books/python_basics.md",
            "--follow",
        ],
        check=True,
    )
    exit(0)


async def main():
    orch = Orchestrator()

    spec = RunSpecV2(
        subject="Python Programming Basics",
        length=LengthPreset.LONG,
        span=SpanPreset.MEDIUM,
        overlays=["narrative", "no_bs"],
        out_path="./books/python_basics.md",
    )

    print("Starting generation...")
    job_id = await orch.run_spec(spec, backend_type="bridge")
    print(f"Job submitted: {job_id}")


if __name__ == "__main__":
    asyncio.run(main())
