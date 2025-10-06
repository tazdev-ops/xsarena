#!/usr/bin/env python3
# Textual TUI for the LMArena Prompt Studio CLI, compatible with Textual versions
# that provide either TextLog (newer) or Log (older). Adds Bilingual button and fixes thread log issue.

import os
import subprocess
import sys
import threading

from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal
from textual.widgets import Button, Checkbox, Footer, Header, Input, Static

# Fallback import for the log widget (TextLog in newer Textual, Log in older)
try:
    from textual.widgets import TextLog as LogWidget

    LOG_IS_TEXTLOG = True
except ImportError:
    from textual.widgets import Log as LogWidget  # type: ignore

    LOG_IS_TEXTLOG = False

CLI_CMD = ["xsarena"]


class StudioApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    #controls {
        height: 14;
        dock: top;
        padding: 1 2;
    }
    #logs {
        height: 1fr;
        border: round $surface;
        margin: 1;
    }
    #status {
        height: 3;
        padding: 0 1;
    }
    Button {
        width: auto;
        margin: 0 1;
    }
    Input {
        width: 40;
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("f5", "refresh_status", "Status"),
    ]

    def __init__(self):
        super().__init__()
        self.proc: subprocess.Popen | None = None
        self.reader_thread: threading.Thread | None = None
        self._stop_reader = threading.Event()

    def compose(self) -> ComposeResult:
        yield Header()
        with Grid(id="controls"):
            yield Static("Book Studio", id="title")
            with Horizontal():
                yield Button("Capture", id="btn_capture")
                yield Button("Status", id="btn_status")
                yield Button("Pause", id="btn_pause")
                yield Button("Resume", id="btn_resume")
                yield Button("Stop", id="btn_stop")
            with Horizontal():
                yield Static("Subject:")
                yield Input(placeholder="e.g., Psychology", id="in_subject")
                yield Checkbox("Plan first", id="cb_plan")
                yield Input(placeholder="max chunks (optional)", id="in_max")
                yield Input(placeholder="window (optional)", id="in_window")
                yield Input(placeholder="out dir (optional)", id="in_outdir")
                yield Button("Zero2Hero", id="btn_z2h")
                yield Button("Reference", id="btn_ref")
                yield Button("Pop-Science", id="btn_pop")
                yield Button("Exam Cram", id="btn_cram")
            with Horizontal():
                yield Static("Lang:")
                yield Input(placeholder="e.g., Japanese", id="in_lang")
                yield Button("Bilingual", id="btn_bilingual")
                yield Static("Lossless input file:")
                yield Input(placeholder="path/to/book.md", id="in_lossless")
                yield Button("Lossless Run", id="btn_lossless")
            with Horizontal():
                yield Static("Translate file:")
                yield Input(placeholder="path/to/file.md", id="in_trans_file")
                yield Input(placeholder="language (e.g., Japanese)", id="in_trans_lang")
                yield Button("Translate", id="btn_translate")
            with Horizontal():
                yield Static("Next override:")
                yield Input(
                    placeholder='e.g., "Continue to master’s level; do not end."',
                    id="in_next",
                )
                yield Button("Send Next", id="btn_next")
        yield LogWidget(id="logs")
        yield Static("Ready", id="status")
        yield Footer()

    def on_mount(self):
        self.start_cli()

    def start_cli(self):
        if self.proc and self.proc.poll() is None:
            return
        try:
            self.proc = subprocess.Popen(
                CLI_CMD,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            self._set_status("Error: Cannot start xsarena. Make sure it's installed.")
            return
        self._stop_reader.clear()
        self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.reader_thread.start()
        # IMPORTANT: we're on the app thread here; call append directly (not call_from_thread)
        self._append_log("TUI: Launched lma_cli.py")

    def _reader_loop(self):
        assert self.proc and self.proc.stdout
        for line in self.proc.stdout:
            if self._stop_reader.is_set():
                break
            self._log(line.rstrip("\n"))
        code = self.proc.wait()
        self._log(f"CLI exited with code {code}")

    def _log(self, msg: str):
        # Called from reader thread; use call_from_thread
        self.call_from_thread(self._append_log, msg)

    def _append_log(self, msg: str):
        log = self.query_one("#logs", LogWidget)
        if LOG_IS_TEXTLOG:
            try:
                log.write(msg)  # type: ignore[attr-defined]
            except Exception:
                try:
                    log.write_line(msg)  # type: ignore[attr-defined]
                except Exception:
                    pass
        else:
            try:
                log.write_line(msg)  # type: ignore[attr-defined]
            except Exception:
                try:
                    log.write(msg)  # type: ignore[attr-defined]
                except Exception:
                    pass

    def _set_status(self, text: str):
        self.query_one("#status", Static).update(text)

    def send_cmd(self, cmd: str):
        if not self.proc or not self.proc.stdin:
            self._append_log("TUI: CLI not running.")
            return
        try:
            self.proc.stdin.write(cmd.strip() + "\n")
            self.proc.stdin.flush()
        except Exception as e:
            self._append_log(f"TUI: Failed to send cmd: {e}")

    def action_refresh_status(self):
        self.send_cmd("/status")

    async def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id or ""

        if bid == "btn_capture":
            self.send_cmd("/capture")
            self._set_status("Capture ON → click Retry in LMArena.")
        elif bid == "btn_status":
            self.send_cmd("/status")
        elif bid == "btn_pause":
            self.send_cmd("/book.pause")
            self._set_status("Autopilot paused.")
        elif bid == "btn_resume":
            self.send_cmd("/book.resume")
            self._set_status("Autopilot resumed.")
        elif bid == "btn_stop":
            self.send_cmd("/book.stop")
            self._set_status("Autopilot stopped.")

        elif bid in ("btn_z2h", "btn_ref", "btn_pop", "btn_cram"):
            subject = self.query_one("#in_subject", Input).value.strip()
            plan = self.query_one("#cb_plan", Checkbox).value
            maxv = self.query_one("#in_max", Input).value.strip()
            wind = self.query_one("#in_window", Input).value.strip()
            outd = self.query_one("#in_outdir", Input).value.strip()
            if not subject:
                self._set_status("Subject required.")
                return
            flags = []
            if plan:
                flags.append("--plan")
            if maxv:
                flags.append(f"--max={maxv}")
            if wind:
                flags.append(f"--window={wind}")
            if outd:
                flags.append(f"--outdir={outd}")
            if bid == "btn_z2h":
                self.send_cmd(f"/book.zero2hero {subject} " + " ".join(flags))
            elif bid == "btn_ref":
                self.send_cmd(f"/book.reference {subject} " + " ".join(flags))
            elif bid == "btn_pop":
                self.send_cmd(f"/book.pop {subject} " + " ".join(flags))
            else:
                self.send_cmd(f"/exam.cram {subject} " + " ".join(flags))
            self._set_status("Book run started…")

        elif bid == "btn_bilingual":
            subject = self.query_one("#in_subject", Input).value.strip()
            lang = self.query_one("#in_lang", Input).value.strip()
            plan = self.query_one("#cb_plan", Checkbox).value
            maxv = self.query_one("#in_max", Input).value.strip()
            wind = self.query_one("#in_window", Input).value.strip()
            outd = self.query_one("#in_outdir", Input).value.strip()
            if not subject or not lang:
                self._set_status("Subject and language required.")
                return
            flags = [f"--lang={lang}"]
            if plan:
                flags.append("--plan")
            if maxv:
                flags.append(f"--max={maxv}")
            if wind:
                flags.append(f"--window={wind}")
            if outd:
                flags.append(f"--outdir={outd}")
            self.send_cmd(f"/book.bilingual {subject} " + " ".join(flags))
            self._set_status("Bilingual book started…")

        elif bid == "btn_lossless":
            path = self.query_one("#in_lossless", Input).value.strip()
            if not path:
                self._set_status("Provide an input file.")
                return
            self.send_cmd(f"/lossless.run {path}")
            self._set_status("Lossless pipeline started…")

        elif bid == "btn_translate":
            path = self.query_one("#in_trans_file", Input).value.strip()
            lang = self.query_one("#in_trans_lang", Input).value.strip()
            if not path or not lang:
                self._set_status("Provide file and language.")
                return
            self.send_cmd(f"/translate.file {path} {lang}")
            self._set_status("Translate started…")

        elif bid == "btn_next":
            txt = self.query_one("#in_next", Input).value.strip()
            if not txt:
                self._set_status("Enter a next override text.")
                return
            self.send_cmd(f"/next {txt}")
            self._set_status("Next override sent.")

    def on_unmount(self):
        self._stop_reader.set()
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
        except Exception:
            pass


def main():
    # Ensure xsarena is available (check that it can be run)
    try:
        subprocess.run(["xsarena", "--help"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print(
            "xsarena_tui.py: xsarena command not found. Make sure xsarena is installed."
        )
    app = StudioApp()
    app.run()


if __name__ == "__main__":
    main()
