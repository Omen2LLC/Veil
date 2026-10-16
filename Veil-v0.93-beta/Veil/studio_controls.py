"""Rounded, keyboard-operable controls and exact-endpoint gradient previews."""
import math, struct, zlib
from functools import lru_cache
import tkinter as tk
from studio_fonts import REGULAR,MEDIUM,SEMIBOLD

def rgb(color):return tuple(int(color[i:i+2],16) for i in (1,3,5))
@lru_cache(maxsize=256)
def rounded_png(width,height,left,right,radius):
    width=max(1,width);height=max(1,height);radius=min(radius,width/2,height/2)
    a,b=rgb(left),rgb(right);rows=[];opaque=bytearray()
    for x in range(width):
        t=x/max(1,width-1);opaque.extend((*[round(u+(v-u)*t) for u,v in zip(a,b)],255))
    for y in range(height):
        if radius<=y+.5<=height-radius:
            rows.append(b'\0'+opaque);continue
        row=bytearray(opaque)
        for x in list(range(math.ceil(radius)))+list(range(max(math.ceil(radius),width-math.ceil(radius)),width)):
            cx=min(max(x+.5,radius),width-radius);cy=min(max(y+.5,radius),height-radius)
            distance=math.hypot(x+.5-cx,y+.5-cy)
            alpha=round(255*max(0,min(1,radius+.5-distance)))
            row[x*4+3]=alpha
        rows.append(b'\0'+row)
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')

def image(width,height,left,right=None,radius=10):
    return tk.PhotoImage(data=rounded_png(int(width),int(height),left,right or left,radius))

def surface_background(parent,app):
    # Rounded panels keep the page color on their outer Tk frame for the corners.
    # Controls inside them must blend with the panel's painted interior instead.
    if hasattr(parent,'back') and hasattr(parent,'app'):
        return app.c['selected'] if getattr(parent,'selected',False) else app.c['panel']
    return parent.cget('bg')

class Scrollbar(tk.Canvas):
    """Slim rounded scroll thumb; supports dragging, paging and keyboard focus."""
    def __init__(self,parent,app,command):
        self.app=app;self.command=command;self.first=0.;self.last=1.
        self.hover=False;self.focused=False;self.drag_offset=None;self.images=[]
        super().__init__(parent,width=app.p(16),bg=app.c['bg'],highlightthickness=0,bd=0,takefocus=True)
        self.bind('<Configure>',self.draw)
        self.bind('<Enter>',lambda e:self.toggle('hover',True))
        self.bind('<Leave>',lambda e:self.toggle('hover',False))
        self.bind('<FocusIn>',lambda e:self.toggle('focused',True))
        self.bind('<FocusOut>',lambda e:self.toggle('focused',False))
        self.bind('<Button-1>',self.press);self.bind('<B1-Motion>',self.drag)
        self.bind('<ButtonRelease-1>',lambda e:setattr(self,'drag_offset',None))
        for key,amount,unit in [('Up',-1,'units'),('Down',1,'units'),('Prior',-1,'pages'),('Next',1,'pages')]:
            self.bind('<'+key+'>',lambda e,a=amount,u=unit:self.scroll(a,u))
        self.bind('<Home>',lambda e:self.move(0));self.bind('<End>',lambda e:self.move(1))
        self.bind('<Destroy>',lambda e:setattr(self,'images',[]))
    def toggle(self,key,value):setattr(self,key,value);self.draw()
    def set(self,first,last):
        self.first=max(0,min(1,float(first)));self.last=max(self.first,min(1,float(last)));self.draw()
    def geometry(self):
        margin=self.app.p(3);track=max(1,self.winfo_height()-2*margin)
        size=min(track,max(self.app.p(28),track*(self.last-self.first)))
        travel=track-size;fraction=self.first/max(.000001,1-(self.last-self.first))
        return margin+travel*fraction,size,travel,margin
    def draw(self,event=None):
        self.delete('all');self.images=[]
        if self.last-self.first>=1:return
        top,size,travel,margin=self.geometry();width=self.app.p(8 if self.hover or self.focused else 6)
        left,right=('#7B7B7B','#AAAAAA') if self.app.effective_mode()=='Dark' else ('#929292','#6F6F6F')
        if self.focused:left=right=self.app.c['focus']
        self.images.append(image(width,max(2,size),left,right,radius=width/2))
        self.create_image(self.winfo_width()/2,top,image=self.images[-1],anchor='n')
    def press(self,event):
        self.focus_set();top,size,travel,margin=self.geometry()
        if top<=event.y<=top+size:self.drag_offset=event.y-top
        else:self.scroll(-1 if event.y<top else 1,'pages')
        return 'break'
    def drag(self,event):
        if self.drag_offset is not None:
            top,size,travel,margin=self.geometry()
            fraction=max(0,min(1,(event.y-margin-self.drag_offset)/max(1,travel)))
            self.move(fraction*(1-(self.last-self.first)))
        return 'break'
    def move(self,fraction):self.command('moveto',fraction);return 'break'
    def scroll(self,amount,unit):self.command('scroll',amount,unit);return 'break'

class Button(tk.Canvas):
    def __init__(self,parent,app,text,command,primary=False,selected=False,compact=False,navigation=False,**kwargs):
        self.app=app;self.text=text;self.command=command;self.primary=primary;self.selected=selected
        self.state=kwargs.pop('state','normal');self.hover=False;self.focused=False
        self.navigation=navigation;self.outlined=kwargs.pop('outlined',False);self.dropdown=kwargs.pop('dropdown',False);self.focus_outline=kwargs.pop('focus_outline',True);self.polished=kwargs.pop('polished',False);self.text_align=kwargs.pop('text_align','center')
        from tkinter.font import Font
        self.font=Font(family=SEMIBOLD if primary else MEDIUM if navigation else REGULAR,size=10 if compact else 11)
        width=self.font.measure(text)+app.p(24)+(app.p(16) if self.dropdown else 0);height=app.p(34 if compact else 38)
        super().__init__(parent,width=width,height=height,bg=surface_background(parent,app),highlightthickness=0,bd=0,
            takefocus=self.state!='disabled',cursor='hand2')
        self.bind('<Configure>',self.draw);self.bind('<Enter>',lambda e:self.toggle('hover',True))
        self.bind('<Leave>',lambda e:self.toggle('hover',False));self.bind('<FocusIn>',lambda e:self.toggle('focused',True))
        self.bind('<FocusOut>',lambda e:self.toggle('focused',False))
        self.bind('<Button-1>',self.activate);self.bind('<Return>',self.activate);self.bind('<space>',self.activate)
        self.bind('<Destroy>',lambda e:setattr(self,'images',[]))
    def toggle(self,key,value):setattr(self,key,value);self.draw()
    def activate(self,event=None):
        if self.state!='disabled':
            self.focus_set();self.draw();self.command()
        return 'break'
    def configure(self,cnf=None,**kwargs):
        for key in ('state','text','selected','outlined'):
            if key in kwargs:setattr(self,key,kwargs.pop(key))
        if kwargs or cnf:super().configure(cnf,**kwargs)
        if hasattr(self,'font'):
            super().configure(takefocus=self.state!='disabled');self.draw()
    config=configure
    def draw(self,event=None):
        c=self.app.c;disabled=self.state=='disabled'
        fill=c['field'] if disabled else c['accent'] if self.primary else c['selected'] if self.selected else c['hover'] if self.hover else self.cget('bg') if self.navigation else c['control']
        foreground=c['disabled'] if disabled else c['on_accent'] if self.primary else c['text']
        w=max(2,self.winfo_width());h=max(2,self.winfo_height());self.delete('all')
        self.images=[]
        ring=self.outlined or (self.focused and self.focus_outline)
        if ring:
            self.images.append(image(w,h,c['focus'],radius=self.app.p(10)));self.create_image(0,0,image=self.images[-1],anchor='nw')
        inset=self.app.p(2) if ring else 0
        if self.polished and not ring:
            self.images.append(image(w,h,c['border'],radius=self.app.p(9)));self.create_image(0,0,image=self.images[-1],anchor='nw');inset=self.app.p(1)
        top='#%02X%02X%02X' % tuple(min(255,v+7) for v in rgb(fill)) if self.polished and not disabled else fill
        self.images.append(image(w-2*inset,h-2*inset,top,fill,radius=self.app.p(9)))
        self.create_image(inset,inset,image=self.images[-1],anchor='nw')
        self.create_text(self.app.p(14) if self.text_align=='left' else (w-self.app.p(16))/2 if self.dropdown else w/2,h/2,text=self.text,font=self.font,fill=foreground,anchor='w' if self.text_align=='left' else 'center')
        if self.dropdown:
            x=w-self.app.p(14);y=h/2
            self.create_line(x-self.app.p(3),y-self.app.p(2),x,y+self.app.p(1),x+self.app.p(3),y-self.app.p(2),fill=foreground,width=self.app.p(1.5),capstyle='round',joinstyle='round')

class Field(tk.Frame):
    def __init__(self,parent,app,variable,width=18,polished=False):
        super().__init__(parent,bg=surface_background(parent,app))
        self.app=app;self.polished=polished;self.back=tk.Canvas(self,bg=app.c['field'],highlightthickness=0)
        self.back.place(relwidth=1,relheight=1)
        self.entry=tk.Entry(self,textvariable=variable,width=width,bg=app.c['field'],fg=app.c['text'],
            insertbackground=app.c['text'],selectbackground=app.c['selected'],selectforeground=app.c['text'],
            font=(REGULAR,11),bd=0,relief='flat',highlightthickness=0)
        self.entry.pack(fill='x',expand=True,padx=app.p(12),pady=app.p(9))
        self.focused=False;self.bind('<Configure>',self.draw)
        self.entry.bind('<FocusIn>',lambda e:self.focus(True));self.entry.bind('<FocusOut>',lambda e:self.focus(False))
        self.bind('<Destroy>',lambda e:setattr(self,'images',[]))
    def focus(self,value):self.focused=value;self.draw()
    def draw(self,event=None):
        self.back.delete('all');w,h=max(2,self.winfo_width()),max(2,self.winfo_height());self.images=[]
        inset=self.app.p(2) if self.focused else 0
        if inset:
            self.images.append(image(w,h,self.app.c['focus'],radius=self.app.p(8)));self.back.create_image(0,0,image=self.images[-1],anchor='nw')
        if self.polished and not self.focused:
            self.images.append(image(w,h,self.app.c['border'],radius=self.app.p(8)));self.back.create_image(0,0,image=self.images[-1],anchor='nw');inset=self.app.p(1)
        self.images.append(image(w-2*inset,h-2*inset,self.app.c['field'],radius=self.app.p(8)))
        self.back.create_image(inset,inset,image=self.images[-1],anchor='nw')

class Pill(tk.Canvas):
    def __init__(self,parent,app,left,right,height=32,command=None):
        self.app=app;self.left=left;self.right=right;self.command=command;self.selected=False;self.focused=False
        super().__init__(parent,height=app.p(height),width=app.p(140),bg=surface_background(parent,app),highlightthickness=0,
            takefocus=bool(command),cursor='hand2' if command else '')
        self.bind('<Configure>',self.draw)
        self.bind('<Destroy>',lambda e:setattr(self,'images',[]))
        if command:
            self.bind('<Button-1>',self.activate);self.bind('<Return>',self.activate);self.bind('<space>',self.activate)
            self.bind('<FocusIn>',lambda e:self.focus(True));self.bind('<FocusOut>',lambda e:self.focus(False))
    def focus(self,value):self.focused=value;self.draw()
    def activate(self,event=None):self.focus_set();self.command();return 'break'
    def draw(self,event=None):
        w,h=max(2,self.winfo_width()),max(2,self.winfo_height());self.delete('all');self.images=[]
        inset=self.app.p(4) if self.selected or self.focused else self.app.p(2)
        if self.selected or self.focused:
            self.images.append(image(w,h,self.app.c['focus'] if self.focused else self.app.c['muted'],radius=h/2))
            self.create_image(0,0,image=self.images[-1],anchor='nw')
            self.images.append(image(w-4,h-4,self.cget('bg'),radius=h/2));self.create_image(2,2,image=self.images[-1],anchor='nw')
        self.images.append(image(w-2*inset,h-2*inset,self.left,self.right,radius=h/2))
        self.create_image(inset,inset,image=self.images[-1],anchor='nw')

class ColorChip(Pill):
    """Endpoint preview with the same picker action as its labeled control."""
    def __init__(self,*args,label='Pick color',**kwargs):
        super().__init__(*args,**kwargs);self.accessible_name=label;self.hint=None;self.hint_job=None
        self.bind('<Enter>',lambda e:self.schedule_hint())
        self.bind('<Leave>',lambda e:self.hide_hint())
        self.bind('<Destroy>',lambda e:self.hide_hint(),add='+')
    def schedule_hint(self):
        self.hide_hint();self.hint_job=self.after(500,self.show_hint)
    def show_hint(self):
        self.hint_job=None
        if not self.winfo_exists():return
        self.hint=tk.Toplevel(self);self.hint.overrideredirect(True)
        self.hint.geometry(f'+{self.winfo_rootx()}+{self.winfo_rooty()+self.winfo_height()+6}')
        tk.Label(self.hint,text=self.accessible_name,bg=self.app.c['control'],fg=self.app.c['text'],font=(REGULAR,10),padx=8,pady=5).pack()
    def hide_hint(self):
        if self.hint_job:self.after_cancel(self.hint_job);self.hint_job=None
        if self.hint:self.hint.destroy();self.hint=None
    def draw(self,event=None):
        w,h=max(2,self.winfo_width()),max(2,self.winfo_height());self.delete('all');self.images=[]
        edge=self.app.c['focus'] if self.focused else self.app.c['border']
        self.images.append(image(w,h,edge,radius=self.app.p(7)));self.create_image(0,0,image=self.images[-1],anchor='nw')
        inset=self.app.p(4)
        self.images.append(image(max(1,w-2*inset),max(1,h-2*inset),self.left,radius=self.app.p(5)))
        self.create_image(inset,inset,image=self.images[-1],anchor='nw')
