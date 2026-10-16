"""Veil â€” experimental, build-locked Windows prototype."""
import argparse
import ctypes
import hashlib
import json
import logging
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk,colorchooser,messagebox,simpledialog,filedialog
from pathlib import Path
from palette_core import (LABELS,DISPLAY_ORDER,STOCK,atomic_json,builtin_palettes,
                          hex_color,load_user_palettes,validate_palette)
from resolve_palette import kernel
from dot_palette import PaletteSession
from palette_names import validate_names,decode,encode
from menu_names import NativeMenuNames
from media_pool_refresh import MediaPoolRefresh
from win_taskbar import APP_ID,configure_window
from veil_startup import show_startup

HERE=Path(__file__).resolve().parent
from studio_version import VERSION
from studio_fonts import load_fonts,REGULAR

from studio_ui import App

def complete_update(instructions):
    """Run from a separate Veil process after the GUI exits."""
    from veil_update import UpdateError, install_staged
    data=json.loads(instructions.read_text(encoding='utf-8'))
    root=Path(data['root']).resolve()
    archive=Path(data['archive']).resolve()
    pointer=Path(data['pointer']).resolve()
    current=Path(data['current']).resolve()
    if (data.get('schema')!=1 or archive.parent!=root/'Veil-Updates'
            or pointer!=root/'Veil-Launcher'/'current-release.txt'
            or current.parent.parent!=root):
        raise UpdateError('Invalid update instructions.')
    k=kernel()
    process=k.OpenProcess(0x100000,False,int(data['wait_pid']))
    if process:
        try:
            if k.WaitForSingleObject(process,90000)!=0:
                raise UpdateError('Veil did not close; update was not installed.')
        finally:k.CloseHandle(process)
    with archive.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=data['sha256']:
            raise UpdateError('Staged release checksum changed; update was not installed.')
    def command(app,extra=()):
        if (app/'Veil.exe').is_file():return [str(app/'Veil.exe'),*extra]
        entry=app/'omen_studio.py' if (app/'omen_studio.py').is_file() else app/'veil_app.py'
        return [sys.executable,str(entry),*extra]
    def smoke(app):
        result=subprocess.run(command(app,['--update-smoke','--expected-version',data['version']]),cwd=str(app),timeout=20,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if result.returncode:raise UpdateError('The new Veil program failed its startup check.')
    previous=pointer.read_bytes() if pointer.exists() else None
    new_app=install_staged(archive,data['version'],current,root,pointer,smoke_check=smoke)
    try:
        launched=subprocess.Popen(command(new_app),cwd=str(new_app),
                                  creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        time.sleep(5)
        if launched.poll() is not None:
            raise UpdateError('The new Veil program exited during startup; launcher restored.')
        threading.Thread(target=launched.wait,daemon=True,name='Veil update launch').start()
    except Exception:
        if previous is None:pointer.unlink(missing_ok=True)
        else:pointer.write_bytes(previous)
        raise
    instructions.unlink(missing_ok=True)
    return 0

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--demo',action='store_true');ap.add_argument('--check',action='store_true')
    ap.add_argument('--update-smoke',action='store_true')
    ap.add_argument('--expected-version')
    ap.add_argument('--apply-update',metavar='INSTRUCTIONS')
    args=ap.parse_args()
    if args.update_smoke:
        if args.expected_version and args.expected_version!=VERSION:
            raise RuntimeError('Executable version does not match the release tag.')
        root=tk.Tk();root.withdraw();app=None
        try:
            load_fonts(root)
            app=App(root,demo=True)
            root.update_idletasks()
            if app.storage_error or app.preference_error:
                raise RuntimeError(app.storage_error or app.preference_error)
        finally:
            if app:app.worker.shutdown()
            root.destroy()
        return 0
    if args.apply_update:
        return complete_update(Path(args.apply_update))
    if getattr(sys,'frozen',False) and not args.check and not args.demo:
        # A Windows taskbar pin may point directly at an older standalone EXE.
        # Follow only a complete release beside this one; never run an arbitrary
        # path from a modified pointer file.
        from studio_launcher import release_version
        root=HERE.parent.parent
        pointer=root/'Veil-Launcher'/'current-release.txt'
        if HERE.name=='Veil' and HERE.parent.name.startswith('Veil-v') and pointer.is_file():
            chosen=Path(pointer.read_text(encoding='utf-8').strip()).resolve()
            if (chosen!=HERE and chosen.parent.parent==root and release_version(chosen)
                    and (chosen/'Veil.exe').is_file()):
                subprocess.Popen([str(chosen/'Veil.exe')],cwd=str(chosen),
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                return 0
    logging.basicConfig(filename=HERE/'veil.log',level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    if args.check:
        session=PaletteSession(HERE,writable=False)
        try:
            palette=session.connect()
            NativeMenuNames(session)
            print('PASS: process discovery, version, live code fingerprint, table layout, and 16 palette entries verified. Read-only.')
            print('PASS: audio/video default-fill sources, native menu modules, and text-layout signatures verified. Read-only.')
            print('Blue:',palette[LABELS.index('Blue')])
        finally:session.close()
        return
    try:ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(APP_ID))
    except Exception:logging.exception('Could not set Windows app identity')
    try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:pass
    root=tk.Tk();root.withdraw()
    load_fonts(root)
    try:root.iconbitmap(default=str(HERE/'veil-icon.ico'))
    except Exception:
        logging.exception('Could not load Windows window icon; using PNG fallback')
        try:
            root._veil_icon=tk.PhotoImage(file=str(HERE/'veil-icon.png'))
            root.iconphoto(True,root._veil_icon)
        except Exception:logging.exception('Could not load Tk window icon')
    k=kernel();mutex=None
    if not args.demo:
        mutex=k.CreateMutexW(None,False,'Local\\ResolvePaletteSwitcher_v1')
        if not mutex or ctypes.get_last_error()==183:
            messagebox.showerror('Veil','An Veil window is already open, or its session lock is unavailable.',parent=root)
            root.destroy()
            if mutex:k.CloseHandle(mutex)
            return
    app=None
    def callback_error(cls,value,tb):
        logging.error('Interface callback failed',exc_info=(cls,value,tb))
        if app is not None:app.error(value)
        else:messagebox.showerror('Veil',str(value),parent=root)
    root.report_callback_exception=callback_error
    try:
        # Build and lay out the workspace while withdrawn, before playback starts.
        # Completion only reveals this ready window; it never holds the last logo
        # frame while constructing the application.
        app=App(root,demo=args.demo)
        root.update_idletasks()
        try:root._taskbar_identity=configure_window(root,HERE)
        except Exception:
            logging.exception('Could not configure Veil taskbar pin identity')
            root.after(3500,lambda:messagebox.showwarning('Veil taskbar icon',
                       'Windows could not set Veil pin name and icon. See veil.log.',parent=root))
        def open_main_window():
            root.deiconify()
            root.update_idletasks()
            try:app.install_system_about()
            except Exception:logging.exception('Could not add About Veil to the title-bar icon menu')
        show_startup(root,open_main_window,HERE)
        root.mainloop()
    finally:
        if app:app.worker.shutdown()
        if app and app.session:
            errors=[]
            if app.session.alive() and app.session.dirty:
                try:app.session.restore()
                except Exception as exc:errors.append(f'Palette and dots: {exc}')
            if app.menu_names and app.session.alive():
                try:app.menu_names.close()
                except Exception as exc:errors.append(f'Native menu names: {exc}')
            if errors:logging.error('Exit restoration incomplete; restart Resolve. %s','; '.join(errors))
            app.session.close()
        identity=getattr(root,'_taskbar_identity',None)
        if identity:
            try:identity.close()
            except Exception:logging.exception('Could not clear taskbar properties on exit')
        if mutex:k.CloseHandle(mutex)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        logging.exception('Startup failed')
        if '--check' in sys.argv or '--update-smoke' in sys.argv:
            print('Connection check failed:',exc,file=sys.stderr)
            sys.exit(1)
        try:messagebox.showerror('Veil','Could not start. See veil.log in this folder.')
        except Exception:pass
        raise

