"""Small branded palette dialogs; cancellation never changes the library."""
from pathlib import Path
import tkinter as tk

from palette_core import builtin_palettes
from studio_controls import Button, Field, image
from window_chrome import theme_caption


def validate_name(value):
    name=value.strip()
    if not name:raise ValueError('Enter a palette name.')
    if len(name)>60:raise ValueError('Use 60 characters or fewer.')
    if any(ord(c)<32 for c in name):raise ValueError('Use visible characters in the name.')
    if name in builtin_palettes():raise ValueError('Choose a name different from the built-in palettes.')
    return name


class PaletteDialog:
    def __init__(self,app,kind,name='',colors=None):
        self.app,self.kind,self.name,self.colors=app,kind,name,colors
        self.result=None;self.closed=False;self.job=None;self.previous_grab=None
        self.window=tk.Toplevel(app.root);self.window.withdraw()
        self.window.title('');self.window.transient(app.root);self.window.resizable(False,False)
        icon=Path(__file__).resolve().parent/'veil-icon.ico'
        if icon.is_file():
            try:self.window.iconbitmap(str(icon))
            except tk.TclError:pass
        self.value=tk.StringVar(self.window,value=name)
        self.window.protocol('WM_DELETE_WINDOW',self.cancel)
        self.window.bind('<Escape>',lambda e:self.cancel())
        if kind=='save':self.window.bind('<Return>',lambda e:self.confirm())
        self.window.bind('<Map>',lambda e:self.window.after_idle(self.caption) if e.widget is self.window else None,add='+')
        self.trace=app.appearance.trace_add('write',self.appearance_changed)
        self.build()

    def appearance_changed(self,*_):
        if not self.closed and self.job is None:self.job=self.window.after_idle(self.build)

    def caption(self):
        if not self.closed:theme_caption(self.window,self.app.effective_mode()=='Dark',self.app.c['panel'],self.app.c['text'])

    def build(self):
        self.job=None
        if self.closed:return
        app,p,c=self.app,self.app.p,self.app.c
        for child in self.window.winfo_children():child.destroy()
        self.window.configure(bg=c['panel'])
        body=app.frame(self.window,c['panel']);body.pack(fill='both',expand=True,padx=p(24),pady=p(24))
        title={'save':'Save palette as','delete':'Delete palette?','replace':'Replace palette?'}[self.kind]
        app.label(body,title,size=18,bold=True,bg=c['panel']).pack(anchor='w')
        if self.kind=='save':
            app.label(body,'Palette name',size=10,muted=True,bg=c['panel']).pack(anchor='w',pady=(p(20),p(7)))
            self.field=Field(body,app,self.value,width=32,polished=True);self.field.pack(fill='x')
            self.field.entry.bind('<KeyRelease>',lambda e:self.validate())
        else:
            app.label(body,self.name,size=12,bold=True,bg=c['panel'],wraplength=p(390)).pack(anchor='w',pady=(p(14),p(12)))
        if self.colors:
            canvas=tk.Canvas(body,width=p(390),height=p(42),bg=c['panel'],bd=0,highlightthickness=0,takefocus=False)
            canvas.pack(fill='x',pady=(p(14) if self.kind=='save' else 0,p(14)))
            self.photos=[]
            for index,pair in enumerate(self.colors[:16]):
                photo=image(p(44),p(15),pair[0],pair[1],radius=p(7));self.photos.append(photo)
                canvas.create_image(p((index%8)*49),p((index//8)*23),image=photo,anchor='nw')
        if self.kind!='save':
            text=('Remove it from your library? Your active Resolve palette stays unchanged.' if self.kind=='delete'
                  else 'Replace the saved palette with your current edits?')
            app.label(body,text,size=10,muted=True,bg=c['panel'],wraplength=p(390)).pack(anchor='w',pady=(0,p(8)))
        self.error=app.label(body,'',size=9,bg=c['panel'],wraplength=p(390))
        self.error.pack(anchor='w',pady=(p(7),p(10)))
        actions=app.frame(body,c['panel']);actions.pack(fill='x')
        self.accept=Button(actions,app,{'save':'Save palette','delete':'Delete','replace':'Replace'}[self.kind],self.confirm,primary=True)
        self.accept.pack(side='right')
        self.cancel_button=Button(actions,app,'Cancel',self.cancel)
        self.cancel_button.pack(side='right',padx=(0,p(8)))
        self.caption()

    def validate(self):
        try:validate_name(self.value.get())
        except ValueError as error:
            self.error.configure(text=str(error));self.accept.configure(state='disabled');return False
        self.error.configure(text='');self.accept.configure(state='normal');return True

    def present(self):
        self.window.update_idletasks();root=self.app.root
        x=root.winfo_rootx()+(root.winfo_width()-self.window.winfo_reqwidth())//2
        y=root.winfo_rooty()+(root.winfo_height()-self.window.winfo_reqheight())//2
        x=max(0,min(x,self.window.winfo_screenwidth()-self.window.winfo_reqwidth()))
        y=max(0,min(y,self.window.winfo_screenheight()-self.window.winfo_reqheight()))
        self.window.geometry(f'+{x}+{y}');self.previous_grab=self.window.grab_current()
        self.window.deiconify();self.window.grab_set()
        if self.kind=='save':self.field.entry.focus_set();self.field.entry.selection_range(0,'end')
        else:self.cancel_button.focus_set()
        self.caption()

    def show(self):
        self.present();self.app.root.wait_window(self.window);return self.result

    def confirm(self):
        if self.kind=='save':
            if not self.validate():return
            self.result=validate_name(self.value.get())
        else:self.result=True
        self.close()

    def cancel(self):self.close()

    def close(self):
        if self.closed:return
        self.closed=True;self.app.appearance.trace_remove('write',self.trace)
        if self.job:self.window.after_cancel(self.job)
        self.window.grab_release();self.window.destroy()
        if self.previous_grab and self.previous_grab.winfo_exists():self.previous_grab.grab_set()
        if self.app.root.winfo_exists():self.app.root.focus_set()
