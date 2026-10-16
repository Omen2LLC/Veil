"""The original Veil splash artwork, retained as a nonmodal About window."""
from pathlib import Path
import tkinter as tk
from studio_fonts import REGULAR
from studio_version import VERSION
from window_chrome import theme_caption
HERE=Path(__file__).resolve().parent

def show_about(app):
    root=app.root
    existing=getattr(app,"about_window",None)
    if existing is not None and existing.winfo_exists():
        existing.deiconify();existing.lift();existing.focus_set();return existing

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
    splash.title('About Veil')
    splash.transient(root)
    splash.resizable(False,False)
    splash.iconbitmap(str(HERE/'veil-icon.ico'))
    splash.geometry(f'{width}x{height}+{(screen_w-width)//2}+{(screen_h-height)//2}')

    canvas=tk.Canvas(splash,width=width,height=height,bg='black',highlightthickness=0,borderwidth=0)
    canvas.pack()
    canvas.create_image(0,0,anchor='nw',image=image)
    # Overlay the supplied mark as an untouched brand asset, never a redraw.
    logo_path=HERE/f'veil-splash-logo-{width}.png'
    if logo_path.exists():
        logo=tk.PhotoImage(file=str(logo_path))
    else:
        logo=tk.PhotoImage(file=str(HERE/'veil-splash-logo-640.png')).subsample(2,2)
    canvas.create_image(round(width*.5),round(height*.5),image=logo,anchor='center',tags='veil-logo')
    splash._logo=logo
    canvas.create_text(round(width*.041),round(height*.85),anchor='nw',
                       text=VERSION.split()[0],fill='#C7C7C7',
                       font=(REGULAR,-max(12,round(height*.029))))
    splash._image=image
    splash.update_idletasks()

    splash.deiconify()
    splash.lift()
    canvas.create_text(round(width*.5),round(height*.88),text='Theme and color palette editor for DaVinci Resolve',
                       fill='#F5EDED',font=(REGULAR,-max(10,round(height*.035))),anchor='center')
    app.about_window=splash
    splash._canvas=canvas
    def update_caption(*_):
        if splash.winfo_exists():
            theme_caption(splash,app.effective_mode()=='Dark',app.c['panel'],app.c['text'])
    def schedule_caption(*_):
        if splash.winfo_exists():splash.after_idle(update_caption)
    appearance_trace=app.appearance.trace_add('write',schedule_caption)
    splash.bind('<Map>',lambda event:schedule_caption() if event.widget is splash else None,add='+')
    def cleanup(event):
        if event.widget is splash:
            app.appearance.trace_remove('write',appearance_trace)
            if app.about_window is splash:app.about_window=None
    splash.bind('<Destroy>',cleanup,add='+')
    update_caption()
    def close(event=None):
        app.about_window=None
        splash.destroy()
        if root.winfo_exists():root.focus_set()
        return 'break'
    splash.protocol('WM_DELETE_WINDOW',close)
    splash.bind('<Escape>',close);splash.bind('<Return>',close)
    splash.focus_set()
    return splash
