import importlib

def test_import_modes():
    for mod in [
        "xsarena.modes.book",
        "xsarena.modes.coder",
        "xsarena.modes.chad",
        "xsarena.modes.bilingual",
        "xsarena.modes.lossless",
        "xsarena.modes.policy",
        "xsarena.modes.study",
    ]:
        assert importlib.import_module(mod) is not None