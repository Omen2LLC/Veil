"""Rounded in-window overlay menus, with one focus owner and keyboard navigation."""
import tkinter as tk
import ctypes,sys
from tkinter.font import Font
from studio_fonts import REGULAR
from studio_controls import image

def clip_rounded(widget,width,height,radius):
    """Clip the rectangular native child window, so corner pixels expose
    the content beneath the overlay rather than its opaque Tk background.
    Windows owns the region after a successful SetWindowRgn call.
    """
    if sys.platform!='win32':return
    gdi=ctypes.WinDLL('gdi32');user=ctypes.WinDLL('user32')
    gdi.CreateRoundRectRgn.argtypes=(ctypes.c_int,)*6;gdi.CreateRoundRectRgn.restype=ctypes.c_void_p
    gdi.DeleteObject.argtypes=(ctypes.c_void_p,);gdi.DeleteObject.restype=ctypes.c_int
    user.SetWindowRgn.argtypes=(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int);user.SetWindowRgn.restype=ctypes.c_int
    region=gdi.CreateRoundRectRgn(0,0,width+1,height+1,radius*2,radius*2)
    if not region:return
    if not user.SetWindowRgn(widget.winfo_id(),region,True):gdi.DeleteObject(region)

class RoundedMenu:
    def __init__(self, app, trigger, entries, checked=None):
        self.app=app; self.trigger=trigger; self.entries=entries; self.closed=False; self.checked=checked; self.offset=0
        self.font=Font(family=REGULAR,size=11); self.margin=app.p(8); self.row_height=app.p(34)
        self.width=max(trigger.winfo_width(),max((self.font.measure(e[0])+app.p(48 if checked is not None else 40) for e in entries if e),default=0))
        self.rows=[]; y=self.margin
        for entry in entries:
            height=self.row_height if entry else app.p(9)
            self.rows.append((y,y+height,entry)); y+=height
        self.content_height=y+self.margin; self.height=self.content_height; self.selected=next((i for i,e in enumerate(entries) if e and e[2]),None)
        # Keep menus in the existing native window. Separate override-redirect
        # Windows popups can lose focus or map behind their owner when opened.
        available=max(2,app.root.winfo_width()-app.p(16))
        self.width=min(self.width,available)
        self.window=tk.Frame(app.root,bg=app.c['bg'],bd=0,highlightthickness=0)
        x=trigger.winfo_rootx()-app.root.winfo_rootx()
        trigger_y=trigger.winfo_rooty()-app.root.winfo_rooty()
        below=app.root.winfo_height()-trigger_y-trigger.winfo_height()-app.p(12)
        above=trigger_y-app.p(12)
        down=self.content_height<=below or below>=above
        self.height=max(2,min(self.content_height,max(above,below)))
        y=trigger_y+trigger.winfo_height()+app.p(4) if down else trigger_y-self.height-app.p(4)
        y=max(app.p(4),min(y,app.root.winfo_height()-self.height-app.p(4)))
        x=max(app.p(4),min(x,app.root.winfo_width()-self.width-app.p(4)))
        self.canvas=tk.Canvas(self.window,width=self.width,height=self.height,bg=app.c['bg'],bd=0,highlightthickness=0,takefocus=True)
        self.canvas.pack(); self.photos=[]
        self.window.place(x=x,y=y,width=self.width,height=self.height)
        self.background_ready=False
        self.canvas.bind('<MouseWheel>',self.wheel)
        self.canvas.bind('<Button-4>',lambda e:self.scroll(-1))
        self.canvas.bind('<Button-5>',lambda e:self.scroll(1))
        self.canvas.bind('<Home>',lambda e:self.jump(False))
        self.canvas.bind('<End>',lambda e:self.jump(True))
        self.canvas.bind('<Prior>',lambda e:self.page(-1))
        self.canvas.bind('<Next>',lambda e:self.page(1))
        self.window.bind('<Configure>',self.clip_corners)
        self.canvas.bind('<Motion>',self.motion); self.canvas.bind('<Button-1>',self.click)
        # A local Tk grab sends clicks outside the popup to the Toplevel, not
        # its Canvas. Handle that delivery path or the grab traps the app.
        self.window.bind('<Button-1>',self.window_click)
        self.canvas.bind('<Escape>',lambda e:self.close()); self.canvas.bind('<Up>',lambda e:self.move(-1)); self.canvas.bind('<Down>',lambda e:self.move(1))
        self.canvas.bind('<Return>',lambda e:self.invoke()); self.canvas.bind('<space>',lambda e:self.invoke())
        self.canvas.bind('<Tab>',lambda e:self.close())
        self.canvas.bind('<FocusOut>',lambda e:self.app.root.after_idle(self.check_focus))
        self.window.bind('<Destroy>',self.destroyed)
        self.root_geometry=self.owner_geometry()
        self.root_binding=app.root.bind('<Configure>',self.root_changed,add='+')
        self.draw(); self.window.lift(); self.canvas.grab_set(); self.canvas.focus_set()
    def clip_corners(self,event):
        if not self.closed and event.widget is self.window:
            clip_rounded(self.window,event.width,event.height,self.app.p(12))
    def draw(self):
        c=self.app.c; p=self.app.p
        self.canvas.delete('rows')
        if not self.background_ready:
            self.photos=[image(self.width,self.height,c['border'],radius=p(12)),
                         image(max(2,self.width-2),max(2,self.height-2),c['panel'],radius=p(11)),
                         image(max(2,self.width-2*self.margin),self.row_height,c['hover'],radius=p(7))]
            self.canvas.create_image(0,0,image=self.photos[0],anchor='nw')
            self.canvas.create_image(1,1,image=self.photos[1],anchor='nw')
            self.background_ready=True
        for i,(top,bottom,entry) in enumerate(self.rows):
            top-=self.offset;bottom-=self.offset
            # Only complete rows are interactive/rendered; preserve corner padding.
            if top<self.margin or bottom>self.height-self.margin:continue
            if not entry:
                self.canvas.create_line(p(14),(top+bottom)/2,self.width-p(14),(top+bottom)/2,fill=c['border'],tags='rows');continue
            text,command,enabled=entry
            if i==self.selected and enabled:self.canvas.create_image(self.margin,top,image=self.photos[2],anchor='nw',tags='rows')
            # Elide unusually long labels without expanding beyond the owner.
            available=max(0,self.width-p(48 if self.checked is not None else 36));label=text
            while label and self.font.measure(label)>available:label=label[:-1]
            if label!=text:label=label[:-1]+'…'
            self.canvas.create_text(p(18),(top+bottom)/2,text=label,font=self.font,anchor='w',fill=c['text'] if enabled else c['disabled'],tags='rows')
            if i==self.checked:
                mid=(top+bottom)/2
                self.canvas.create_line(self.width-p(25),mid,self.width-p(22),mid+p(3),self.width-p(17),mid-p(3),fill=c['text'],width=max(1,p(1.5)),capstyle='round',joinstyle='round',tags=('rows','checkmark'))
        if self.content_height>self.height:
            track=self.height-2*self.margin
            thumb=max(p(14),track*self.height/self.content_height)
            top=self.margin+(track-thumb)*self.offset/(self.content_height-self.height)
            self.canvas.create_line(self.width-p(5),top,self.width-p(5),top+thumb,fill=c['muted'],width=max(2,p(2)),capstyle='round',tags='rows')
    def scroll(self,steps):
        previous=self.offset
        self.offset=max(0,min(self.content_height-self.height,self.offset+steps*self.row_height))
        if self.offset!=previous:self.selected=None
        self.draw();return 'break'
    def wheel(self,event):
        if event.delta:return self.scroll(-event.delta/120)
        return 'break'
    def ensure_visible(self):
        if self.selected is None:return
        top,bottom,_=self.rows[self.selected]
        if top-self.offset<self.margin:self.offset=top-self.margin
        elif bottom-self.offset>self.height-self.margin:self.offset=bottom-self.height+self.margin
        self.offset=max(0,min(self.content_height-self.height,self.offset))
    def jump(self,last):
        enabled=[i for i,e in enumerate(self.entries) if e and e[2]]
        if enabled:self.selected=enabled[-1 if last else 0];self.ensure_visible();self.draw()
        return 'break'
    def page(self,step):
        for _ in range(max(1,(self.height-2*self.margin)//self.row_height-1)):self.move(step)
        return 'break'
    def motion(self,event):
        selected=next((i for i,(a,b,e) in enumerate(self.rows) if self.margin<=event.y<self.height-self.margin and a<=event.y+self.offset<b and a-self.offset>=self.margin and b-self.offset<=self.height-self.margin and e and e[2]),None)
        if selected!=self.selected:self.selected=selected; self.draw()
    def click(self,event):
        if not (0<=event.x<self.width and 0<=event.y<self.height):self.close(); return 'break'
        self.motion(event); self.invoke(); return 'break'
    def window_click(self,event):
        x=event.x_root-self.canvas.winfo_rootx(); y=event.y_root-self.canvas.winfo_rooty()
        if not (0<=x<self.width and 0<=y<self.height):return self.close()
        return self.click(type('Click',(),{'x':x,'y':y})())
    def move(self,step):
        enabled=[i for i,e in enumerate(self.entries) if e and e[2]]
        if enabled:
            if self.selected not in enabled:
                visible=[i for i in enabled if self.rows[i][0]-self.offset>=self.margin and self.rows[i][1]-self.offset<=self.height-self.margin]
                self.selected=(visible or enabled)[0 if step>0 else -1]
                self.ensure_visible();self.draw();return 'break'
            current=enabled.index(self.selected) if self.selected in enabled else (-1 if step>0 else 0)
            self.selected=enabled[(current+step)%len(enabled)]; self.ensure_visible(); self.draw()
        return 'break'
    def invoke(self):
        if self.selected is not None:
            command=self.entries[self.selected][1]; self.close(); command()
        return 'break'
    def check_focus(self):
        if self.closed:return
        focus=self.app.root.focus_get()
        if focus is not self.canvas:self.close(restore=False)
    def owner_geometry(self):
        root=self.app.root
        return root.winfo_x(),root.winfo_y(),root.winfo_width(),root.winfo_height()
    def root_changed(self,event):
        # Mapping a transient popup can emit unrelated root Configure events.
        # Only dismiss for an actual owner move/resize.
        if event.widget is self.app.root and self.owner_geometry()!=self.root_geometry:self.close(restore=False)
    def destroyed(self,event):
        if event.widget is self.window and not self.closed:self.close(restore=False)
    def close(self,restore=True):
        if self.closed:return 'break'
        self.closed=True
        try:self.app.root.unbind('<Configure>',self.root_binding)
        except tk.TclError:pass
        try:self.canvas.grab_release(); self.window.destroy()
        except tk.TclError:pass
        self.photos=[]
        try:
            if restore and self.trigger.winfo_exists():self.trigger.focus_set()
        except tk.TclError:pass
        return 'break'
