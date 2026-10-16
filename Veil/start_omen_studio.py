"""Find a usable GUI interpreter, then start Veil without a console."""
import argparse
import os
from pathlib import Path
import struct
import subprocess
import sys

def verify_runtime():
    if os.name!='nt' or struct.calcsize('P')!=8 or sys.version_info<(3,11):
        raise RuntimeError('Veil needs Windows and 64-bit Python 3.11 or newer.')
    import tkinter as tk
    root=tk.Tk();root.withdraw();root.update_idletasks();root.destroy()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--check-runtime',action='store_true')
    ap.add_argument('--check',action='store_true')
    args=ap.parse_args()
    verify_runtime()
    if args.check_runtime:return 0
    from studio_launcher import newest_release
    folder=newest_release(Path(__file__).resolve().parent)
    entry=folder/'omen_studio.py'
    if not entry.is_file():raise RuntimeError('Extract the entire ZIP and keep all Veil files together.')
    if args.check:
        return subprocess.call([sys.executable,str(entry),'--check'],cwd=str(folder))
    windowed=Path(sys.executable).with_name('pythonw.exe')
    executable=str(windowed) if windowed.is_file() else sys.executable
    subprocess.Popen([executable,str(entry)],cwd=str(folder),creationflags=subprocess.CREATE_NO_WINDOW)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        (Path(__file__).resolve().parent/'launcher-error.txt').write_text(str(exc),encoding='utf-8')
        print('Veil could not start:',exc,file=sys.stderr)
        sys.exit(1)
