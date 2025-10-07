#!/usr/bin/env python3
# GTK4 GUI for XSArena — wraps the xsarena CLI subprocess with a native GUI.
# Requires: PyGObject (GTK4), Linux recommended.
#
# Features:
# - Backend: bridge|openrouter, model, /capture, /or.status, CF controls
# - System: load directives file, /style.narrative on/off, /style.nobs on/off, /systemfile
# - Book modes: zero2hero/reference/nobs/pop/bilingual + subject/lang/plan/max/window/outPath
# - Ingestion: /ingest.synth file → synth.md with chunkKB/synthChars
# - Study tools: exam.cram, flashcards/glossary/index
# - Autopilot: pause/resume/stop, /next, checkpoints save/load, /auto.out
# - Recipes: run recipe file; “inline plan” (paste YAML → saved → /run.recipe path)
# - Live log console

import contextlib
import os
import shutil
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk

APP_ID = "org.xsarena.GTK"


def find_cli_command():
    # Prefer console script 'xsarena'; fallback to local lma_cli.py
    exe = shutil.which("xsarena")
    if exe:
        return [exe]
    # Fallback to Python file
    if os.path.exists("xsarena_cli.py"):
        return [sys.executable, "xsarena_cli.py"]
    if os.path.exists("lma_cli.py"):
        return [sys.executable, "lma_cli.py"]
    # Last resort: console script 'lmastudio' (compat)
    exe2 = shutil.which("lmastudio")
    if exe2:
        return [exe2]
    return None


class CLIProcessManager:
    def __init__(self, on_line_cb, on_exit_cb):
        self.proc = None
        self.thread = None
        self.on_line = on_line_cb
        self.on_exit = on_exit_cb
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self.proc and self.proc.poll() is None:
                return True
            cmd = find_cli_command()
            if not cmd:
                self.on_line("[GUI] Could not find xsarena CLI. Install and ensure it is on PATH.\n")
                return False
            env = os.environ.copy()
            # Force fallback REPL for robust non-interactive piping
            env["XSA_USE_PTK"] = "0"
            try:
                self.proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env,
                )
            except Exception as e:
                self.on_line(f"[GUI] Failed to start CLI: {e}\n")
                return False

            self.thread = threading.Thread(target=self._reader_loop, daemon=True)
            self.thread.start()
            self.on_line(f"[GUI] Started CLI: {' '.join(cmd)} (XSA_USE_PTK=0)\n")
            return True

    def _reader_loop(self):
        try:
            for line in self.proc.stdout:
                if line is None:
                    break
                GLib.idle_add(self.on_line, line)
        except Exception as e:
            GLib.idle_add(self.on_line, f"[GUI] Reader error: {e}\n")
        finally:
            code = None
            with contextlib.suppress(Exception):
                code = self.proc.poll()
            GLib.idle_add(self.on_exit, code)

    def send(self, text: str):
        with self._lock:
            if not self.proc or self.proc.poll() is None:
                self.on_line("[GUI] CLI is not running. Click Start.\n")
                return
            try:
                self.proc.stdin.write(text.strip() + "\n")
                self.proc.stdin.flush()
            except Exception as e:
                self.on_line(f"[GUI] Send failed: {e}\n")

    def stop(self):
        with self._lock:
            if self.proc and self.proc.poll() is None:
                with contextlib.suppress(Exception):
                    self.proc.terminate()


class XSArenaGTK(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.manager = CLIProcessManager(self.append_log, self.on_cli_exit)
        self.win = None
        self.logbuf = None

        # Backend models
        self.backend_combo = None
        self.model_entry = None

        # System
        self.directives_entry = None
        self.nobs_switch = None
        self.narrative_switch = None

        # Book
        self.subject_entry = None
        self.lang_entry = None
        self.plan_check = None
        self.max_spin = None
        self.win_spin = None
        self.out_entry = None

        # Ingest
        self.ingest_src_entry = None
        self.ingest_out_entry = None
        self.chunk_spin = None
        self.synth_spin = None

        # Study
        self.synth_path_entry = None
        self.flash_out_entry = None
        self.gloss_out_entry = None
        self.index_out_entry = None

        # Autopilot
        self.next_entry = None
        self.chk_name_entry = None
        self.auto_out_entry2 = None

        # Recipes
        self.recipe_path_entry = None
        self.inline_textview = None

        # Jobs
        self.jobs_liststore = None
        self.sse_log_buffer = None
        self.sse_active = False

        # Code
        self.code_file_tree = None
        self.code_editor_buffer = None

        # Snapshot
        self.snapshot_progress = None

    def do_activate(self):
        if not self.win:
            self.win = Gtk.ApplicationWindow(application=self, title="XSArena GTK")
            self.win.set_default_size(1200, 800)

            header = Gtk.HeaderBar()
            start_btn = Gtk.Button(label="Start CLI")
            start_btn.connect("clicked", self.on_start_cli)
            stop_btn = Gtk.Button(label="Stop CLI")
            stop_btn.connect("clicked", self.on_stop_cli)
            status_btn = Gtk.Button(label="Status")
            status_btn.connect("clicked", lambda *_: self.manager.send("/status"))

            header.pack_start(start_btn)
            header.pack_start(stop_btn)
            header.pack_start(status_btn)
            self.win.set_titlebar(header)

            root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            self.win.set_child(root)

            left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            left.set_size_request(460, -1)
            right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

            root.append(left)
            root.append(right)

            # Left: Notebook with tabs
            nb = Gtk.Notebook()
            left.append(nb)

            nb.append_page(self.build_backend_tab(), Gtk.Label(label="Backend"))
            nb.append_page(self.build_system_tab(), Gtk.Label(label="System"))
            nb.append_page(self.build_book_tab(), Gtk.Label(label="Book"))
            nb.append_page(self.build_ingest_tab(), Gtk.Label(label="Ingest"))
            nb.append_page(self.build_study_tab(), Gtk.Label(label="Study"))
            nb.append_page(self.build_autopilot_tab(), Gtk.Label(label="Autopilot"))
            nb.append_page(self.build_recipe_tab(), Gtk.Label(label="Run Inline/Recipe"))
            nb.append_page(self.build_cloudflare_tab(), Gtk.Label(label="Cloudflare"))
            nb.append_page(self.build_jobs_tab(), Gtk.Label(label="Jobs"))
            nb.append_page(self.build_code_tab(), Gtk.Label(label="Code"))
            nb.append_page(self.build_snapshot_tab(), Gtk.Label(label="Snapshot"))

            # Right: Log console
            scrolled = Gtk.ScrolledWindow()
            self.logbuf = Gtk.TextBuffer()
            tv = Gtk.TextView.new_with_buffer(self.logbuf)
            tv.set_monospace(True)
            tv.set_editable(False)
            scrolled.set_child(tv)
            right.append(scrolled)

        self.win.present()

    # UI builders
    def build_backend_tab(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row1.append(Gtk.Label(label="Backend:"))

        # Use the modern DropDown widget with string array
        self.backend_combo = Gtk.DropDown.new_from_strings(["bridge", "openrouter"])

        row1.append(self.backend_combo)
        set_backend_btn = Gtk.Button(label="Set")
        set_backend_btn.connect("clicked", self.on_set_backend)
        row1.append(set_backend_btn)
        box.append(row1)

        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row2.append(Gtk.Label(label="Model:"))
        self.model_entry = Gtk.Entry()
        self.model_entry.set_text("openrouter/auto")
        row2.append(self.model_entry)
        set_model_btn = Gtk.Button(label="Set Model")
        set_model_btn.connect("clicked", self.on_set_model)
        row2.append(set_model_btn)
        box.append(row2)

        row3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        capture_btn = Gtk.Button(label="Capture IDs (Bridge)")
        capture_btn.connect("clicked", lambda *_: self.manager.send("/capture"))
        or_status_btn = Gtk.Button(label="OpenRouter Status")
        or_status_btn.connect("clicked", lambda *_: self.manager.send("/or.status"))
        row3.append(capture_btn)
        row3.append(or_status_btn)
        box.append(row3)

        return box

    def build_system_tab(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row1.append(Gtk.Label(label="Directives file:"))
        self.directives_entry = Gtk.Entry()
        self.directives_entry.set_placeholder_text("directives/ancient_iranian_languages.en.txt")
        row1.append(self.directives_entry)
        load_sys_btn = Gtk.Button(label="Load")
        load_sys_btn.connect("clicked", self.on_load_systemfile)
        row1.append(load_sys_btn)
        box.append(row1)

        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.nobs_switch = Gtk.Switch()
        self.narrative_switch = Gtk.Switch()
        nobs_btn = Gtk.Button(label="No‑BS ON/OFF")
        narr_btn = Gtk.Button(label="Narrative ON/OFF")
        nobs_btn.connect("clicked", self.on_toggle_nobs)
        narr_btn.connect("clicked", self.on_toggle_narrative)
        row2.append(Gtk.Label(label="Style:"))
        row2.append(nobs_btn)
        row2.append(self.nobs_switch)
        row2.append(narr_btn)
        row2.append(self.narrative_switch)
        box.append(row2)

        return box

    def build_book_tab(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        row1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row1.append(Gtk.Label(label="Subject:"))
        self.subject_entry = Gtk.Entry()
        self.subject_entry.set_placeholder_text("Ancient Iranian Languages")
        row1.append(self.subject_entry)
        box.append(row1)

        row1b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row1b.append(Gtk.Label(label="Language (bilingual):"))
        self.lang_entry = Gtk.Entry()
        self.lang_entry.set_placeholder_text("e.g., Japanese")
        row1b.append(self.lang_entry)
        box.append(row1b)

        row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.plan_check = Gtk.CheckButton(label="Plan first")
        row2.append(self.plan_check)
        box.append(row2)

        row3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row3.append(Gtk.Label(label="Max chunks:"))
        self.max_spin = Gtk.SpinButton.new_with_range(0, 999, 1)
        self.max_spin.set_value(6)
        row3.append(self.max_spin)
        row3.append(Gtk.Label(label="Window:"))
        self.win_spin = Gtk.SpinButton.new_with_range(0, 200, 1)
        self.win_spin.set_value(100)
        row3.append(self.win_spin)
        box.append(row3)

        row4 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row4.append(Gtk.Label(label="Out path:"))
        self.out_entry = Gtk.Entry()
        self.out_entry.set_placeholder_text("./books/manual.md")
        row4.append(self.out_entry)
        box.append(row4)

        row5 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        z2h = Gtk.Button(label="Zero2Hero")
        z2h.connect("clicked", self.on_run_zero2hero)
        refb = Gtk.Button(label="Reference")
        refb.connect("clicked", self.on_run_reference)
        nob = Gtk.Button(label="No‑BS")
        nob.connect("clicked", self.on_run_nobs)
        pop = Gtk.Button(label="Pop‑Science")
        pop.connect("clicked", self.on_run_pop)
        bil = Gtk.Button(label="Bilingual")
        bil.connect("clicked", self.on_run_bilingual)
        row5.append(z2h)
        row5.append(refb)
        row5.append(nob)
        row5.append(pop)
        row5.append(bil)
        box.append(row5)

        return box

    def build_ingest_tab(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        r1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r1.append(Gtk.Label(label="Source file:"))
        self.ingest_src_entry = Gtk.Entry()
        self.ingest_src_entry.set_placeholder_text("sources/persian_history_scripts_corpus.md")
        r1.append(self.ingest_src_entry)
        box.append(r1)

        r2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r2.append(Gtk.Label(label="Synth out:"))
        self.ingest_out_entry = Gtk.Entry()
        self.ingest_out_entry.set_placeholder_text("books/ail.scripts.synth.md")
        r2.append(self.ingest_out_entry)
        box.append(r2)

        r3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r3.append(Gtk.Label(label="chunkKB:"))
        self.chunk_spin = Gtk.SpinButton.new_with_range(10, 2000, 10)
        self.chunk_spin.set_value(100)
        r3.append(self.chunk_spin)
        r3.append(Gtk.Label(label="synthChars:"))
        self.synth_spin = Gtk.SpinButton.new_with_range(2000, 40000, 500)
        self.synth_spin.set_value(16000)
        r3.append(self.synth_spin)
        box.append(r3)

        run_btn = Gtk.Button(label="Run /ingest.synth")
        run_btn.connect("clicked", self.on_ingest)
        box.append(run_btn)

        return box

    def build_study_tab(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        r1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        exb = Gtk.Button(label="Exam‑cram (subject from Book tab)")
        exb.connect("clicked", self.on_exam_cram)
        r1.append(exb)
        box.append(r1)

        r2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r2.append(Gtk.Label(label="Synth path:"))
        self.synth_path_entry = Gtk.Entry()
        self.synth_path_entry.set_placeholder_text("books/ail.scripts.synth.md")
        r2.append(self.synth_path_entry)
        box.append(r2)

        r3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r3.append(Gtk.Label(label="Flashcards out:"))
        self.flash_out_entry = Gtk.Entry()
        self.flash_out_entry.set_placeholder_text("books/ail.scripts.flashcards.md")
        r3.append(self.flash_out_entry)
        box.append(r3)

        r4 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r4.append(Gtk.Label(label="Glossary out:"))
        self.gloss_out_entry = Gtk.Entry()
        self.gloss_out_entry.set_placeholder_text("books/ail.scripts.glossary.md")
        r4.append(self.gloss_out_entry)
        box.append(r4)

        r5 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r5.append(Gtk.Label(label="Index out:"))
        self.index_out_entry = Gtk.Entry()
        self.index_out_entry.set_placeholder_text("books/ail.scripts.index.md")
        r5.append(self.index_out_entry)
        box.append(r5)

        fc = Gtk.Button(label="Flashcards.from")
        fc.connect("clicked", self.on_flashcards)
        gl = Gtk.Button(label="Glossary.from")
        gl.connect("clicked", self.on_glossary)
        ix = Gtk.Button(label="Index.from")
        ix.connect("clicked", self.on_index)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.append(fc)
        row.append(gl)
        row.append(ix)
        box.append(row)

        return box

    def build_autopilot_tab(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        r1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pause = Gtk.Button(label="Pause")
        pause.connect("clicked", lambda *_: self.manager.send("/book.pause"))
        resume = Gtk.Button(label="Resume")
        resume.connect("clicked", lambda *_: self.manager.send("/book.resume"))
        stop = Gtk.Button(label="Stop")
        stop.connect("clicked", lambda *_: self.manager.send("/book.stop"))
        status = Gtk.Button(label="Status")
        status.connect("clicked", lambda *_: self.manager.send("/status"))
        r1.append(pause)
        r1.append(resume)
        r1.append(stop)
        r1.append(status)
        box.append(r1)

        r2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r2.append(Gtk.Label(label="Next override:"))
        self.next_entry = Gtk.Entry()
        self.next_entry.set_placeholder_text('e.g., "Continue with Pahlavi heterograms; add 3 quick checks."')
        r2.append(self.next_entry)
        send_next = Gtk.Button(label="Send /next")
        send_next.connect("clicked", self.on_send_next)
        r2.append(send_next)
        box.append(r2)

        r3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r3.append(Gtk.Label(label="Checkpoint name:"))
        self.chk_name_entry = Gtk.Entry()
        self.chk_name_entry.set_placeholder_text("ail-week2")
        r3.append(self.chk_name_entry)
        save = Gtk.Button(label="Save")
        save.connect("clicked", self.on_save_checkpoint)
        load = Gtk.Button(label="Load")
        load.connect("clicked", self.on_load_checkpoint)
        r3.append(save)
        r3.append(load)
        box.append(r3)

        r4 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r4.append(Gtk.Label(label="Auto.out path:"))
        self.auto_out_entry2 = Gtk.Entry()
        self.auto_out_entry2.set_placeholder_text("./books/manual.cont.md")
        r4.append(self.auto_out_entry2)
        ao = Gtk.Button(label="Set /auto.out")
        ao.connect("clicked", self.on_set_auto_out)
        r4.append(ao)
        box.append(r4)

        return box

    def build_recipe_tab(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        r1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        r1.append(Gtk.Label(label="Recipe path:"))
        self.recipe_path_entry = Gtk.Entry()
        self.recipe_path_entry.set_placeholder_text("recipes/ail.en.yml")
        r1.append(self.recipe_path_entry)
        rb = Gtk.Button(label="Run /run.recipe")
        rb.connect("clicked", self.on_run_recipe)
        r1.append(rb)
        box.append(r1)

        box.append(Gtk.Label(label="Inline plan (YAML/JSON) → saved to .xsarena/inline_recipe.yml then /run.recipe"))

        sc = Gtk.ScrolledWindow()
        self.inline_textview = Gtk.TextView()
        self.inline_textview.set_monospace(True)
        sc.set_child(self.inline_textview)
        box.append(sc)
        run_inline_btn = Gtk.Button(label="Run Inline Plan")
        run_inline_btn.connect("clicked", self.on_run_inline_plan)
        box.append(run_inline_btn)

        return box

    def build_cloudflare_tab(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )
        r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        cfstat = Gtk.Button(label="CF Status")
        cfstat.connect("clicked", lambda *_: self.manager.send("/cf.status"))
        cfres = Gtk.Button(label="CF Resume")
        cfres.connect("clicked", lambda *_: self.manager.send("/cf.resume"))
        r.append(cfstat)
        r.append(cfres)
        box.append(r)
        box.append(Gtk.Label(label="Use CF Resume after solving the challenge in your browser (bridge backend)."))
        return box

    def build_jobs_tab(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        # Jobs list
        scrolled = Gtk.ScrolledWindow()
        self.jobs_liststore = Gtk.ListStore(str, str, str, str)  # id, state, subject, backend
        treeview = Gtk.TreeView(model=self.jobs_liststore)

        # Add columns
        for i, col_title in enumerate(["ID", "State", "Subject", "Backend"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            treeview.append_column(column)

        scrolled.set_child(treeview)
        box.append(scrolled)

        # Control buttons
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect("clicked", self.on_refresh_jobs)
        controls.append(refresh_btn)

        resume_btn = Gtk.Button(label="Resume")
        resume_btn.connect("clicked", self.on_resume_job)
        controls.append(resume_btn)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", self.on_cancel_job)
        controls.append(cancel_btn)

        fork_btn = Gtk.Button(label="Fork")
        fork_btn.connect("clicked", self.on_fork_job)
        controls.append(fork_btn)

        budget_btn = Gtk.Button(label="Budget")
        budget_btn.connect("clicked", self.on_set_budget)
        controls.append(budget_btn)

        outline_btn = Gtk.Button(label="Open Outline")
        outline_btn.connect("clicked", self.on_open_outline)
        controls.append(outline_btn)

        box.append(controls)

        # SSE Log viewer
        log_label = Gtk.Label(label="Live Events:")
        box.append(log_label)

        log_scrolled = Gtk.ScrolledWindow()
        self.sse_log_buffer = Gtk.TextBuffer()
        log_tv = Gtk.TextView.new_with_buffer(self.sse_log_buffer)
        log_tv.set_monospace(True)
        log_tv.set_editable(False)
        log_scrolled.set_child(log_tv)
        log_scrolled.set_vexpand(True)
        box.append(log_scrolled)

        # SSE control
        sse_ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sse_start_btn = Gtk.Button(label="Start SSE")
        sse_start_btn.connect("clicked", self.on_start_sse)
        sse_ctrl.append(sse_start_btn)

        sse_stop_btn = Gtk.Button(label="Stop SSE")
        sse_stop_btn.connect("clicked", self.on_stop_sse)
        sse_ctrl.append(sse_stop_btn)

        box.append(sse_ctrl)

        return box

    def build_code_tab(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        # Top: File browser and editor
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # Left: File tree
        file_scrolled = Gtk.ScrolledWindow()
        file_store = Gtk.TreeStore(str, str)  # name, path
        self.code_file_tree = Gtk.TreeView(model=file_store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Files", renderer, text=0)
        self.code_file_tree.append_column(column)

        # Populate file tree
        self.populate_file_tree(file_store)

        file_scrolled.set_child(self.code_file_tree)
        file_scrolled.set_size_request(200, -1)
        top_box.append(file_scrolled)

        # Right: Editor
        editor_scrolled = Gtk.ScrolledWindow()
        self.code_editor_buffer = Gtk.TextBuffer()
        editor_tv = Gtk.TextView.new_with_buffer(self.code_editor_buffer)
        editor_tv.set_monospace(True)
        editor_scrolled.set_child(editor_tv)
        top_box.append(editor_scrolled)

        box.append(top_box)

        # Bottom: Controls
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        load_file_btn = Gtk.Button(label="Load File")
        load_file_btn.connect("clicked", self.on_load_file)
        controls.append(load_file_btn)

        diff_btn = Gtk.Button(label="Diff")
        diff_btn.connect("clicked", self.on_code_diff)
        controls.append(diff_btn)

        dry_run_btn = Gtk.Button(label="Dry Run Patch")
        dry_run_btn.connect("clicked", self.on_dry_run_patch)
        controls.append(dry_run_btn)

        apply_btn = Gtk.Button(label="Apply Patch")
        apply_btn.connect("clicked", self.on_apply_patch)
        controls.append(apply_btn)

        test_btn = Gtk.Button(label="Run Tests")
        test_btn.connect("clicked", self.on_run_tests)
        controls.append(test_btn)

        box.append(controls)

        return box

    def build_snapshot_tab(self):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        # Controls
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        snapshot_btn = Gtk.Button(label="Create Snapshot")
        snapshot_btn.connect("clicked", self.on_create_snapshot)
        controls.append(snapshot_btn)

        diff_btn = Gtk.Button(label="Diff Snapshots")
        diff_btn.connect("clicked", self.on_diff_snapshots)
        controls.append(diff_btn)

        share_btn = Gtk.Button(label="Share Snapshot")
        share_btn.connect("clicked", self.on_share_snapshot)
        controls.append(share_btn)

        box.append(controls)

        # Progress/status
        self.snapshot_progress = Gtk.ProgressBar()
        box.append(self.snapshot_progress)

        # Result display
        result_scrolled = Gtk.ScrolledWindow()
        result_buffer = Gtk.TextBuffer()
        result_tv = Gtk.TextView.new_with_buffer(result_buffer)
        result_tv.set_editable(False)
        result_scrolled.set_child(result_tv)
        result_scrolled.set_vexpand(True)
        box.append(result_scrolled)

        return box

    def populate_file_tree(self, store):
        """Populate the file tree with Python files from src directory."""
        from pathlib import Path

        def add_directory(parent, dir_path):
            for item in dir_path.iterdir():
                if item.is_dir():
                    # Create a parent node for directories
                    dir_iter = store.append(parent, [item.name, str(item)])
                    add_directory(dir_iter, item)
                elif item.suffix == ".py":
                    store.append(parent, [item.name, str(item)])

        src_path = Path("src")
        if src_path.exists():
            add_directory(None, src_path)

    # Jobs tab event handlers
    def on_refresh_jobs(self, btn):
        # Would make API call to get job list
        self.append_log("[GUI] Refreshing jobs list (API call would go here)\n")

    def on_resume_job(self, btn):
        self.manager.send("/book.resume")

    def on_cancel_job(self, btn):
        self.manager.send("/book.stop")

    def on_fork_job(self, btn):
        self.append_log("[GUI] Fork job selected (would call API)\n")

    def on_set_budget(self, btn):
        self.append_log("[GUI] Budget setting selected\n")

    def on_open_outline(self, btn):
        import webbrowser

        webbrowser.open("http://127.0.0.1:8787")  # Default serve URL

    def on_start_sse(self, btn):
        self.append_log("[GUI] Starting SSE stream (would connect to API)\n")
        self.sse_active = True

    def on_stop_sse(self, btn):
        self.append_log("[GUI] Stopping SSE stream\n")
        self.sse_active = False

    # Code tab event handlers
    def on_load_file(self, btn):
        # Get selected file from tree
        selection = self.code_file_tree.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter:
            file_path = model[tree_iter][1]
            if file_path and os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        self.code_editor_buffer.set_text(content)
                except Exception as e:
                    self.append_log(f"[GUI] Error loading file: {e}\n")

    def on_code_diff(self, btn):
        self.append_log("[GUI] Running code diff (would call diff command)\n")

    def on_dry_run_patch(self, btn):
        self.append_log("[GUI] Running dry run patch (would call patch dry-run)\n")

    def on_apply_patch(self, btn):
        self.append_log("[GUI] Applying patch (would call patch apply)\n")

    def on_run_tests(self, btn):
        self.append_log("[GUI] Running tests (would execute pytest)\n")
        self.manager.send("/book.test")

    # Snapshot tab event handlers
    def on_create_snapshot(self, btn):
        self.append_log("[GUI] Creating snapshot (would call xsarena snapshot run)\n")
        self.manager.send("xsarena snapshot run")

    def on_diff_snapshots(self, btn):
        self.append_log("[GUI] Diffing snapshots\n")

    def on_share_snapshot(self, btn):
        self.append_log("[GUI] Sharing snapshot\n")

    # Event handlers
    def on_start_cli(self, *_):
        self.manager.start()

    def on_stop_cli(self, *_):
        self.manager.stop()

    def on_set_backend(self, *_):
        selected = self.backend_combo.get_selected()
        if selected == 0:
            be = "bridge"
        elif selected == 1:
            be = "openrouter"
        else:
            be = "bridge"
        self.manager.send(f"/backend {be}")

    def on_set_model(self, *_):
        model = self.model_entry.get_text().strip()
        if model:
            self.manager.send(f"/or.model {model}")

    def on_load_systemfile(self, *_):
        path = self.directives_entry.get_text().strip()
        if path:
            self.manager.send(f"/systemfile {path}")

    def on_toggle_nobs(self, btn):
        # Toggle by reading current state
        state = self.nobs_switch.get_active()
        self.manager.send("/style.nobs off" if state else "/style.nobs on")
        self.nobs_switch.set_active(not state)

    def on_toggle_narrative(self, btn):
        state = self.narrative_switch.get_active()
        self.manager.send("/style.narrative off" if state else "/style.narrative on")
        self.narrative_switch.set_active(not state)

    def common_book_args(self):
        subject = self.subject_entry.get_text().strip() or "Subject"
        plan = "--plan" if self.plan_check.get_active() else ""
        maxc = int(self.max_spin.get_value())
        wind = int(self.win_spin.get_value())
        outp = self.out_entry.get_text().strip()
        flags = []
        if plan:
            flags.append(plan)
        if maxc:
            flags.append(f"--max={maxc}")
        if wind:
            flags.append(f"--window={wind}")
        if outp:
            flags.append(f"--outdir={os.path.dirname(outp)}" if os.path.dirname(outp) else "")
        return subject, " ".join([f for f in flags if f])

    def on_run_zero2hero(self, *_):
        s, flags = self.common_book_args()
        self.manager.send(f'/repo.use book.zero2hero "{s}"')
        self.manager.send(f'/book.zero2hero "{s}" {flags}')

    def on_run_reference(self, *_):
        s, flags = self.common_book_args()
        self.manager.send(f'/repo.use book.reference "{s}"')
        self.manager.send(f'/book.reference "{s}" {flags}')

    def on_run_nobs(self, *_):
        s, flags = self.common_book_args()
        self.manager.send(f'/repo.use book.nobs "{s}"')
        self.manager.send(f'/book.nobs "{s}" {flags}')

    def on_run_pop(self, *_):
        s, flags = self.common_book_args()
        self.manager.send(f'/repo.use book.pop "{s}"')
        self.manager.send(f'/book.pop "{s}" {flags}')

    def on_run_bilingual(self, *_):
        s, flags = self.common_book_args()
        lang = self.lang_entry.get_text().strip()
        if not lang:
            self.append_log("[GUI] Provide target language for bilingual.\n")
            return
        self.manager.send(f'/repo.use book.bilingual "{s}" --lang={lang}')
        self.manager.send(f'/book.bilingual "{s}" --lang={lang} {flags}')

    def on_ingest(self, *_):
        src = self.ingest_src_entry.get_text().strip()
        outp = self.ingest_out_entry.get_text().strip()
        ck = int(self.chunk_spin.get_value())
        sc = int(self.synth_spin.get_value())
        if not (src and outp):
            self.append_log("[GUI] Provide source and synth paths.\n")
            return
        self.manager.send(f"/ingest.synth {src} {outp} {ck} {sc}")

    def on_exam_cram(self, *_):
        s = self.subject_entry.get_text().strip() or "Ancient Iranian Languages"
        self.manager.send(f'/exam.cram "{s}"')

    def on_flashcards(self, *_):
        syn = self.synth_path_entry.get_text().strip()
        outp = self.flash_out_entry.get_text().strip()
        if syn and outp:
            self.manager.send(f"/flashcards.from {syn} {outp} 200")
        else:
            self.append_log("[GUI] Provide synth and flashcards out paths.\n")

    def on_glossary(self, *_):
        syn = self.synth_path_entry.get_text().strip()
        outp = self.gloss_out_entry.get_text().strip()
        if syn and outp:
            self.manager.send(f"/glossary.from {syn} {outp}")
        else:
            self.append_log("[GUI] Provide synth and glossary out paths.\n")

    def on_index(self, *_):
        syn = self.synth_path_entry.get_text().strip()
        outp = self.index_out_entry.get_text().strip()
        if syn and outp:
            self.manager.send(f"/index.from {syn} {outp}")
        else:
            self.append_log("[GUI] Provide synth and index out paths.\n")

    def on_send_next(self, *_):
        txt = self.next_entry.get_text().strip()
        if txt:
            self.manager.send(f'/next "{txt}"')

    def on_save_checkpoint(self, *_):
        name = self.chk_name_entry.get_text().strip() or "checkpoint"
        self.manager.send(f"/book.save {name}")

    def on_load_checkpoint(self, *_):
        name = self.chk_name_entry.get_text().strip()
        if name:
            self.manager.send(f"/book.load {name}")
        else:
            self.append_log("[GUI] Provide checkpoint name.\n")

    def on_set_auto_out(self, *_):
        path = self.auto_out_entry2.get_text().strip()
        if path:
            self.manager.send(f"/auto.out {path}")

    def on_run_recipe(self, *_):
        path = self.recipe_path_entry.get_text().strip()
        if path:
            self.manager.send(f"/run.recipe {path}")
        else:
            self.append_log("[GUI] Provide recipe path.\n")

    def on_run_inline_plan(self, *_):
        buf = self.inline_textview.get_buffer()
        start = buf.get_start_iter()
        end = buf.get_end_iter()
        text = buf.get_text(start, end, False)
        if not text.strip():
            self.append_log("[GUI] Paste YAML/JSON first.\n")
            return
        os.makedirs(".xsarena", exist_ok=True)
        tmp = os.path.join(".xsarena", "inline_recipe.yml")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            self.manager.send(f"/run.recipe {tmp}")
        except Exception as e:
            self.append_log(f"[GUI] Failed to write inline plan: {e}\n")

    # Logging / lifecycle
    def append_log(self, line: str):
        if not self.logbuf:
            return
        end = self.logbuf.get_end_iter()
        self.logbuf.insert(end, line)

    def on_cli_exit(self, code):
        self.append_log(f"[GUI] CLI exited with code {code}\n")


def main():
    app = XSArenaGTK()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
