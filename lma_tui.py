#!/usr/bin/env python3
try:
    import xsarena_tui  # canonical wrapper script

    if __name__ == "__main__":
        xsarena_tui.StudioApp().run()
except Exception:
    # Fallback: run via module path if script missing
    from xsarena.gui.gtk_app import main as _gtk_main  # if you prefer GTK, keep/skip as needed

    if __name__ == "__main__":
        _gtk_main()
