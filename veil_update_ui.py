"""Small, non-blocking update prompt for stable Veil releases."""
from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox

from palette_core import atomic_json
from studio_version import VERSION
from veil_update import check_latest, verified_download


def _state_path(app) -> Path:
    return Path(app.user_path).with_name("veil-update.json")


def _skipped(app) -> str:
    try:
        return str(json.loads(_state_path(app).read_text(encoding="utf-8")).get("skip", ""))
    except (OSError, ValueError, TypeError):
        return ""


def check_in_background(app, manual: bool = False) -> None:
    if app.demo or app.closing:
        return

    def work():
        try:
            release, problem = check_latest(VERSION), None
        except Exception as error:
            release, problem = None, str(error)
        def complete():
            if not app.root.winfo_exists() or app.closing:
                return
            if problem:
                if manual:
                    messagebox.showinfo("Veil updates", "Could not check for updates. " + problem, parent=app.root)
                return
            if release and (manual or release["version"] != _skipped(app)):
                show_update(app, release)
            elif manual:
                messagebox.showinfo("Veil updates", "You have the latest available stable release.", parent=app.root)
        try:
            app.root.after(0, complete)
        except tk.TclError:
            pass

    threading.Thread(target=work, daemon=True, name="Veil update check").start()


def show_update(app, release: dict) -> None:
    window = tk.Toplevel(app.root)
    window.title("Veil update")
    window.configure(bg=app.c["panel"])
    window.transient(app.root)
    window.resizable(False, False)
    body = app.frame(window, app.c["panel"])
    body.pack(fill="both", expand=True, padx=app.p(22), pady=app.p(20))
    app.label(body, f'Veil {release["version"]} is available', size=16, bold=True,
              bg=app.c["panel"]).pack(anchor="w")
    notes = release["notes"][:1800] or "A new stable version is ready."
    app.label(body, notes, size=10, bg=app.c["panel"], wraplength=app.p(460),
              justify="left").pack(anchor="w", pady=(app.p(12), app.p(20)))
    status = app.label(body, "", size=10, muted=True, bg=app.c["panel"])
    status.pack(anchor="w")
    controls = app.frame(body, app.c["panel"])
    controls.pack(anchor="e", pady=(app.p(12), 0))

    def skip():
        atomic_json(_state_path(app), {"schema": 1, "skip": release["version"]})
        window.destroy()

    def upgrade():
        for child in controls.winfo_children():
            child.configure(state="disabled")
        status.configure(text="Downloading and verifying…")
        def work():
            try:
                here = Path(app.user_path).parent
                root = here.parent.parent if here.parent.name.startswith("Veil-v") else here.parent
                archive = root / "Veil-Updates" / release["archive"]["name"]
                verified_download(release, archive)
                with archive.open('rb') as stream:
                    digest=hashlib.file_digest(stream,'sha256').hexdigest()
                instruction = root / "Veil-Updates" / "pending-update.json"
                atomic_json(instruction, {"schema": 1, "version": release["version"],
                         "archive": str(archive), "current": str(here),
                         "sha256": digest,
                         "root": str(root), "pointer": str(root / "Veil-Launcher" / "current-release.txt"),
                         "wait_pid": os.getpid()})
                error = None
            except Exception as exc:
                instruction, error = None, str(exc)
            def complete():
                if not app.root.winfo_exists():
                    return
                if error:
                    status.configure(text="Update could not be prepared.")
                    messagebox.showerror("Veil update", error, parent=window)
                    for child in controls.winfo_children():
                        child.configure(state="normal")
                    return
                executable = [sys.executable]
                if not getattr(sys, "frozen", False):
                    executable.append(str(here / "omen_studio.py" if (here / "omen_studio.py").is_file()
                                          else here / "veil_app.py"))
                app.after_successful_close = lambda: subprocess.Popen(
                    executable + ["--apply-update", str(instruction)], cwd=str(here),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                app.close()
                try:
                    alive = bool(app.root.winfo_exists())
                except tk.TclError:
                    alive = False
                if alive:
                    waiting = bool(app.closing)
                    status.configure(text="Waiting for Veil to restore and close…" if waiting
                                     else "Upgrade paused. Your current version is still open.")
                    if not waiting:
                        app.after_successful_close = None
                        for child in controls.winfo_children():
                            child.configure(state="normal")
            try:
                app.root.after(0, complete)
            except tk.TclError:
                pass
        threading.Thread(target=work, daemon=True, name="Veil update download").start()

    app.button(controls, "Upgrade", upgrade, primary=True).pack(side="left", padx=app.p(4))
    app.button(controls, "Later", window.destroy).pack(side="left", padx=app.p(4))
    app.button(controls, "Skip this version", skip).pack(side="left", padx=app.p(4))
    window.protocol("WM_DELETE_WINDOW", window.destroy)
    window.grab_set()
