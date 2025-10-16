def test_import_macros():
    import importlib

    m = importlib.import_module("xsarena.cli.cmds_macros")
    assert hasattr(m, "app")
