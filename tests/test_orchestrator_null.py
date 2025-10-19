"""Test orchestrator with NullTransport."""


def test_orchestrator_null():
    """Test orchestrator with NullTransport basic functionality."""
    # Create orchestrator with null transport
    from xsarena.core.backends import create_backend
    from xsarena.core.v2_orchestrator.orchestrator import Orchestrator
    from xsarena.core.v2_orchestrator.specs import LengthPreset, RunSpecV2, SpanPreset

    null_transport = create_backend(
        "null",
        script=[
            "Introduction to testing. NEXT: [Continue with main concepts]",
            "Main concepts of testing. NEXT: [Continue with examples]",
            "Examples of testing. NEXT: [END]",
        ],
    )

    orchestrator = Orchestrator(transport=null_transport)

    # Test that we can create an orchestrator instance and run basic operations
    assert orchestrator is not None
    assert hasattr(orchestrator, "run_spec")

    # Test that we can create a run spec
    run_spec = RunSpecV2(
        subject="Test Subject",
        length=LengthPreset("standard"),
        span=SpanPreset("medium"),
        overlays=["narrative"],
        extra_note="",
        extra_files=[],
        out_path="./test_output.md",
        profile="",
    )

    assert run_spec.subject == "Test Subject"
    assert run_spec.length.value == "standard"
    assert run_spec.span.value == "medium"

    print("✓ Orchestrator null basic test passed")
