def test_import_playground():
    import importlib

    m = importlib.import_module("xsarena.cli.cmds_playground")
    assert hasattr(m, "app")
