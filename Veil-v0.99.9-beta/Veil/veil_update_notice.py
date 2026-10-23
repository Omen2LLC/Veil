"""Compact Veil update notices with themed content, caption and controls."""
from pathlib import Path
import tkinter as tk
from window_chrome import theme_caption

def show_notice(app,title,message,parent=None):
    existing=getattr(app,'update_notice_window',None)
    if existing is not None:
        try:
            if existing.winfo_exists():existing.notice_close()
        except tk.TclError:pass
    owner=parent or app.root
    window=tk.Toplevel(app.root);window.withdraw()
    window.title('Veil updates');window.transient(owner);window.resizable(False,False)
    app.update_notice_window=window
    previous=window.grab_current();closed=False;trace=None
    icon=Path(__file__).with_name('veil-icon.ico')
    if icon.is_file():window.iconbitmap(str(icon))

    def close():
        nonlocal closed
        if closed:return 'break'
        closed=True
        try:window.grab_release();window.destroy()
        except tk.TclError:pass
        try:
            if previous is not None and previous.winfo_exists():previous.grab_set()
        except tk.TclError:pass
        return 'break'

    def caption():
        if not closed:theme_caption(window,app.effective_mode()=='Dark',app.c['panel'],app.c['text'])

    def build():
        if closed:return
        for child in window.winfo_children():child.destroy()
        p,c=app.p,app.c
        window.configure(bg=c['panel'])
        body=app.frame(window,c['panel']);body.pack(fill='both',expand=True,padx=p(24),pady=p(22))
        header=app.frame(body,c['panel']);header.pack(fill='x')
        photo=tk.PhotoImage(file=str(Path(__file__).with_name('veil-icon.png')))
        window.notice_logo=photo.subsample(max(1,round(photo.width()/p(28))))
        tk.Label(header,image=window.notice_logo,bg=c['panel'],bd=0).pack(side='left',padx=(0,p(12)))
        app.label(header,title,size=17,bold=True,bg=c['panel'],wraplength=p(330)).pack(side='left',anchor='w')
        app.label(body,message[:700],size=11,muted=True,bg=c['panel'],wraplength=p(350)).pack(anchor='w',pady=(p(16),p(22)))
        actions=app.frame(body,c['panel']);actions.pack(fill='x')
        window.notice_button=app.button(actions,'Done',close,primary=True)
        window.notice_button.pack(side='right')
        window.update_idletasks()
        width,height=window.winfo_reqwidth(),window.winfo_reqheight()
        x=max(0,min(app.root.winfo_rootx()+(app.root.winfo_width()-width)//2,window.winfo_screenwidth()-width))
        y=max(0,min(app.root.winfo_rooty()+(app.root.winfo_height()-height)//2,window.winfo_screenheight()-height))
        window.geometry(f'+{x}+{y}');caption()

    def destroyed(event):
        nonlocal closed
        if event.widget is not window:return
        closed=True
        if trace is not None:
            try:app.appearance.trace_remove('write',trace)
            except tk.TclError:pass
    window.notice_close=close
    window.protocol('WM_DELETE_WINDOW',close)
    window.bind('<Escape>',lambda event:close())
    window.bind('<Return>',lambda event:close())
    window.bind('<Destroy>',destroyed,add='+')
    window.bind('<Map>',lambda event:window.after_idle(caption) if event.widget is window else None,add='+')
    trace=app.appearance.trace_add('write',lambda *args:window.after_idle(build) if not closed else None)
    build();window.deiconify();caption();window.grab_set();window.notice_button.focus_set()
    return window
