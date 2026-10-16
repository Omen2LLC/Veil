"""Veil â€” experimental, build-locked Windows prototype."""
import argparse
import ctypes
import json
import logging
import sys
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
from win_taskbar import APP_ID,configure_window,round_splash_window

HERE=Path(__file__).resolve().parent
from studio_version import VERSION
from studio_fonts import load_fonts,REGULAR
SPLASH_DURATION_MS=3000

def show_splash(root, on_done):
    """Display the versionless artwork, then open the app after three seconds."""
    screen_w, screen_h = root.winfo_screenwidth(), root.winfo_screenheight()
    image=None
    for width in (960, 800, 640):
        candidate=HERE/f'splash-{width}.png'
        if not candidate.exists():continue
        photo=tk.PhotoImage(file=str(candidate))
        if photo.width()<=screen_w*.65 and photo.height()<=screen_h*.55:
            image=photo
            break
    if image is None:
        smallest=HERE/'splash-640.png'
        if not smallest.exists():
            raise FileNotFoundError('Splash artwork is missing')
        source=tk.PhotoImage(file=str(smallest))
        image=source.subsample(2,2)
    width,height=image.width(),image.height()
    splash=tk.Toplevel(root)
    splash.withdraw()
    splash.overrideredirect(True)
    splash.geometry(f'{width}x{height}+{(screen_w-width)//2}+{(screen_h-height)//2}')
    splash.attributes('-topmost',True)
    canvas=tk.Canvas(splash,width=width,height=height,bg='black',highlightthickness=0,borderwidth=0)
    canvas.pack()
    canvas.create_image(0,0,anchor='nw',image=image)
    # Overlay the supplied mark as an untouched brand asset, never a redraw.
    logo_path=HERE/f'veil-splash-logo-{width}.png'
    if logo_path.exists():
        logo=tk.PhotoImage(file=str(logo_path))
    else:
        logo=tk.PhotoImage(file=str(HERE/'veil-splash-logo-640.png')).subsample(2,2)
    canvas.create_image(round(width*.5),round(height*.39),image=logo,anchor='center',tags='veil-logo')
    canvas.create_text(round(width*.5),round(height*.71),text='Veil',fill='#F5EDED',
                       font=(REGULAR,-max(18,round(height*.12))),anchor='center',tags='veil-wordmark')
    splash._logo=logo
    canvas.create_text(round(width*.041),round(height*.85),anchor='nw',
                       text=VERSION.split()[0],fill='#C7C7C7',
                       font=(REGULAR,-max(12,round(height*.029))))
    splash._image=image
    splash.update_idletasks()
    round_splash_window(splash,width,height,max(12,round(width*.019)))
    splash.deiconify()
    splash.lift()
    root.after(SPLASH_DURATION_MS,lambda:(splash.destroy(),on_done()))
from studio_ui import App

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--demo',action='store_true');ap.add_argument('--check',action='store_true')
    args=ap.parse_args()
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
            root._omen_studio_icon=tk.PhotoImage(file=str(HERE/'veil-icon.png'))
            root.iconphoto(True,root._omen_studio_icon)
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
        def open_main_window():
            nonlocal app
            try:
                app=App(root,demo=args.demo)
                root.update_idletasks()
                try:root._taskbar_identity=configure_window(root,HERE)
                except Exception:
                    logging.exception('Could not configure Veil taskbar pin identity')
                    root.after(200,lambda:messagebox.showwarning('Veil taskbar icon',
                               'Windows could not set Veilâ€™s pin name and icon. See veil.log.',parent=root))
                root.deiconify()
            except Exception:
                logging.exception('Could not open main window after splash')
                root.destroy()
                raise
        show_splash(root,open_main_window)
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
        if '--check' in sys.argv:
            print('Connection check failed:',exc,file=sys.stderr)
            sys.exit(1)
        try:messagebox.showerror('Veil','Could not start. See veil.log in this folder.')
        except Exception:pass
        raise

