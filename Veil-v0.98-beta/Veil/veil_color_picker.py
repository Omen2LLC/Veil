"""Veil's local color editor. No palette mutation until the user confirms."""
import colorsys
import re
import tkinter as tk
from pathlib import Path

from studio_controls import Button, Field, image
from window_chrome import theme_caption
from studio_menu import clip_rounded


def parse_hex(text):
    value = text.strip().lstrip('#')
    if not re.fullmatch(r'[0-9a-fA-F]{6}', value):
        raise ValueError('Enter a six-digit HEX color.')
    return '#' + value.upper()


def color_rgb(color):
    color = parse_hex(color)
    return tuple(int(color[i:i+2], 16) for i in (1, 3, 5))


def rgb_hex(values):
    if len(values) != 3 or any(not str(v).strip().isdigit() for v in values):
        raise ValueError('RGB values must be whole numbers from 0 to 255.')
    channels = tuple(int(v) for v in values)
    if any(v < 0 or v > 255 for v in channels):
        raise ValueError('RGB values must be whole numbers from 0 to 255.')
    return '#%02X%02X%02X' % channels


class ColorPicker:
    def __init__(self, app, initial, name, endpoint):
        self.app = app
        self.original = parse_hex(initial)
        self.result = None
        self.closed = False
        self.h, self.s, self.v = colorsys.rgb_to_hsv(*(v/255 for v in color_rgb(initial)))
        self.window = tk.Toplevel(app.root)
        self.window.withdraw()
        self.window.title('')
        icon=Path(__file__).resolve().parent/'veil-icon.ico'
        if icon.is_file():
            try:self.window.iconbitmap(str(icon))
            except tk.TclError:pass
        self.window.transient(app.root)
        self.window.resizable(False, False)
        self.window.protocol('WM_DELETE_WINDOW', self.cancel)
        self.window.bind('<Escape>', lambda e: self.cancel())
        self.window.bind('<Return>', lambda e: self.confirm())
        self.window.bind('<Map>', lambda e: self.window.after_idle(self.caption)
                         if e.widget is self.window else None, add='+')
        self.name, self.endpoint = name, endpoint
        self.trace = app.appearance.trace_add('write', self.appearance_changed)
        self.rebuild_job = None
        self.previous_grab = None
        self.build()

    @property
    def color(self):
        return '#%02X%02X%02X' % tuple(round(v*255) for v in colorsys.hsv_to_rgb(self.h, self.s, self.v))

    def caption(self):
        if not self.closed:
            theme_caption(self.window, self.app.effective_mode() == 'Dark',
                          self.app.c['panel'], self.app.c['text'])

    def appearance_changed(self, *_):
        if not self.closed and self.rebuild_job is None:
            self.rebuild_job = self.window.after_idle(self.build)

    def build(self):
        self.rebuild_job = None
        if self.closed:
            return
        app, p, c = self.app, self.app.p, self.app.c
        for child in self.window.winfo_children():
            child.destroy()
        self.window.configure(bg=c['panel'])
        body = app.frame(self.window, c['panel'])
        body.pack(fill='both', expand=True, padx=p(24), pady=p(22))
        app.label(body, self.name, size=18, bold=True, bg=c['panel'],
                  wraplength=p(500)).pack(anchor='w')
        app.label(body, self.endpoint + ' color', size=10, muted=True,
                  bg=c['panel']).pack(anchor='w', pady=(p(3), p(18)))
        workspace = app.frame(body, c['panel']); workspace.pack(fill='x')
        left = app.frame(workspace, c['panel']); left.pack(side='left', anchor='n')
        right = app.frame(workspace, c['panel']); right.pack(side='left', anchor='n', padx=(p(20), 0))
        self.w, self.height = p(310), p(220)
        self.field = tk.Canvas(left, width=self.w, height=self.height, bd=0,
                               highlightthickness=0, bg=c['panel'], takefocus=True,
                               cursor='crosshair')
        self.field.pack()
        self.field.bind('<Configure>',lambda e:clip_rounded(self.field,e.width,e.height,p(10)))
        self.field.bind('<Button-1>', self.select_sv)
        self.field.bind('<B1-Motion>', self.select_sv)
        self.field.bind('<Key>', self.sv_key)
        self.field.bind('<FocusIn>', lambda e: self.draw_markers())
        self.field.bind('<FocusOut>', lambda e: self.draw_markers())
        self.hue = tk.Canvas(left, width=self.w, height=p(26), bd=0,
                             highlightthickness=0, bg=c['panel'], takefocus=True,
                             cursor='hand2')
        self.hue.pack(pady=(p(12), 0))
        self.hue.bind('<Configure>',lambda e:clip_rounded(self.hue,e.width,e.height,p(13)))
        self.hue.bind('<Button-1>', self.select_hue)
        self.hue.bind('<B1-Motion>', self.select_hue)
        self.hue.bind('<Key>', self.hue_key)
        self.hue.bind('<FocusIn>', lambda e: self.draw_markers())
        self.hue.bind('<FocusOut>', lambda e: self.draw_markers())
        self.preview = tk.Canvas(right, width=p(160), height=p(82), bd=0,
                                 highlightthickness=0, bg=c['panel'])
        self.preview.pack()
        captions = app.frame(right, c['panel']); captions.pack(fill='x', pady=(p(6),p(16)))
        app.label(captions, 'Original', size=9, muted=True, bg=c['panel']).pack(side='left')
        app.label(captions, 'New', size=9, muted=True, bg=c['panel']).pack(side='right')
        app.label(right, 'HEX', size=9, muted=True, bg=c['panel']).pack(anchor='w')
        self.hex_var = tk.StringVar(self.window)
        self.hex_field = Field(right, app, self.hex_var, width=12, polished=True)
        self.hex_field.pack(fill='x', pady=(p(5),p(13)))
        self.hex_field.entry.bind('<KeyRelease>', lambda e: self.edit_hex())
        rgb = app.frame(right, c['panel']); rgb.pack(fill='x')
        self.rgb_vars = [tk.StringVar(self.window) for _ in range(3)]
        for i, (label, variable) in enumerate(zip(('R','G','B'), self.rgb_vars)):
            column = app.frame(rgb,c['panel']); column.pack(side='left',fill='x',expand=True,padx=(0,p(5) if i<2 else 0))
            app.label(column,label,size=9,muted=True,bg=c['panel']).pack(anchor='w')
            field = Field(column, app, variable, width=3, polished=True)
            field.pack(fill='x',pady=(p(5),0))
            field.entry.bind('<KeyRelease>',lambda e:self.edit_rgb())
        self.error = app.label(body, '', size=9, bg=c['panel'], wraplength=p(490))
        self.error.pack(anchor='w',pady=(p(14),p(8)))
        actions = app.frame(body,c['panel']); actions.pack(fill='x')
        Button(actions,app,'Reset',self.reset,compact=True).pack(side='left')
        self.apply = Button(actions,app,'Use color',self.confirm,primary=True)
        self.apply.pack(side='right')
        Button(actions,app,'Cancel',self.cancel).pack(side='right',padx=(0,p(8)))
        self.draw_hue();self.draw_field();self.sync();self.caption()

    def present(self):
        self.window.update_idletasks()
        root = self.app.root
        x = root.winfo_rootx() + (root.winfo_width()-self.window.winfo_reqwidth())//2
        y = root.winfo_rooty() + (root.winfo_height()-self.window.winfo_reqheight())//2
        x = max(0,min(x,self.window.winfo_screenwidth()-self.window.winfo_reqwidth()))
        y = max(0,min(y,self.window.winfo_screenheight()-self.window.winfo_reqheight()))
        self.window.geometry(f'+{x}+{y}')
        self.previous_grab = self.window.grab_current()
        self.window.deiconify();self.window.grab_set();self.field.focus_set()
        self.caption()

    def show(self):
        self.present()
        self.app.root.wait_window(self.window)
        return self.result

    def draw_field(self):
        # Exact pixel dimensions keep the pointer and sampled color aligned at every DPI.
        width, height = self.w, self.height
        hue = colorsys.hsv_to_rgb(self.h,1,1)
        columns = [tuple(1-x/(width-1)*(1-channel) for channel in hue) for x in range(width)]
        rows = []
        for y in range(height):
            v = 1-y/(height-1)
            row = ['#%02X%02X%02X' % tuple(round(a*v*255) for a in column) for column in columns]
            rows.append('{'+' '.join(row)+'}')
        base = tk.PhotoImage(master=self.window,width=width,height=height)
        base.put(' '.join(rows))
        self.sv_image = base
        self.field.delete('gradient')
        self.field.create_image(0,0,image=self.sv_image,anchor='nw',tags='gradient')
        self.field.tag_lower('gradient')

    def draw_hue(self):
        colors = ['#%02X%02X%02X' % tuple(round(a*255) for a in colorsys.hsv_to_rgb(x/(self.w-1),1,1)) for x in range(self.w)]
        self.hue_image = tk.PhotoImage(master=self.window,width=self.w,height=self.app.p(26))
        self.hue_image.put(' '.join('{'+' '.join(colors)+'}' for _ in range(self.app.p(26))))
        self.hue.create_image(0,0,image=self.hue_image,anchor='nw',tags='gradient')

    def draw_markers(self):
        p = self.app.p
        self.field.delete('marker');self.hue.delete('marker')
        x,y = self.s*(self.w-1),(1-self.v)*(self.height-1)
        radius = p(6)
        for color, width in (('#111111',4),('#FFFFFF',2)):
            self.field.create_oval(x-radius,y-radius,x+radius,y+radius,outline=color,width=p(width),tags='marker')
        x = self.h*(self.w-1)
        self.hue.create_line(x,p(5),x,p(21),fill='#111111',width=p(7),capstyle='round',tags='marker')
        self.hue.create_line(x,p(5),x,p(21),fill='#FFFFFF',width=p(3),capstyle='round',tags='marker')
        for widget in (self.field,self.hue):
            if self.window.focus_get() is widget:
                w,h=int(widget.cget('width'))-1,int(widget.cget('height'))-1
                r=p(10) if widget is self.field else h/2
                widget.create_polygon(r,1,w-r,1,w,1,w,r,w,h-r,w,h,w-r,h,r,h,1,h,1,h-r,1,r,1,1,
                                      smooth=True,splinesteps=24,fill='',outline=self.app.c['focus'],
                                      width=p(2),tags='marker')

    def sync(self, source=None):
        color = self.color
        if source != 'hex':self.hex_var.set(color)
        if source != 'rgb':
            for var,value in zip(self.rgb_vars,color_rgb(color)):var.set(str(value))
        self.error.configure(text='');self.apply.configure(state='normal')
        self.preview.delete('all')
        p = self.app.p
        self.preview_images = [image(p(78),p(82),self.original,radius=p(8)),image(p(78),p(82),color,radius=p(8))]
        for index,photo in enumerate(self.preview_images):self.preview.create_image(p(index*82),0,image=photo,anchor='nw')
        self.draw_markers()

    def set_color(self,color,source=None):
        r,g,b = color_rgb(color)
        h,s,v = colorsys.rgb_to_hsv(r/255,g/255,b/255)
        if s:self.h=h  # Keep a meaningful hue when editing neutral colors.
        self.s,self.v=s,v
        self.draw_field();self.sync(source)

    def invalid(self,error):
        self.error.configure(text=str(error));self.apply.configure(state='disabled')

    def edit_hex(self):
        try:self.set_color(parse_hex(self.hex_var.get()),'hex')
        except ValueError as error:self.invalid(error)

    def edit_rgb(self):
        try:self.set_color(rgb_hex([v.get() for v in self.rgb_vars]),'rgb')
        except ValueError as error:self.invalid(error)

    def select_sv(self,event):
        self.field.focus_set()
        self.s=max(0,min(1,event.x/(self.w-1)))
        self.v=1-max(0,min(1,event.y/(self.height-1)))
        self.sync()

    def select_hue(self,event):
        self.hue.focus_set();self.h=max(0,min(1,event.x/(self.w-1)))
        self.draw_field();self.sync()

    def sv_key(self,event):
        step=.1 if event.state & 1 else .01
        if event.keysym in ('Left','Right'):self.s=max(0,min(1,self.s+(-step if event.keysym=='Left' else step)))
        elif event.keysym in ('Up','Down'):self.v=max(0,min(1,self.v+(step if event.keysym=='Up' else -step)))
        else:return
        self.sync();return 'break'

    def hue_key(self,event):
        if event.keysym not in ('Left','Right','Up','Down'):return
        self.h=(self.h+(-1 if event.keysym in ('Left','Down') else 1)*(10 if event.state & 1 else 1)/360)%1
        self.draw_field();self.sync();return 'break'

    def reset(self):self.set_color(self.original)

    def confirm(self):
        if self.apply.state=='disabled':return
        self.result=self.color;self.close()

    def cancel(self):self.close()

    def close(self):
        if self.closed:return
        self.closed=True
        self.app.appearance.trace_remove('write',self.trace)
        if self.rebuild_job:self.window.after_cancel(self.rebuild_job)
        self.window.grab_release();self.window.destroy()
        if self.previous_grab and self.previous_grab.winfo_exists():self.previous_grab.grab_set()
        if self.app.root.winfo_exists():self.app.root.focus_set()
