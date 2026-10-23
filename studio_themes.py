"""Read-only Cherry Blossom Fusion concept for the beta interface."""
from pathlib import Path
import tkinter as tk
from PIL import Image,ImageTk


ASSETS = Path(__file__).resolve().parent / 'Themes' / 'Fusion-preview'
SIZES = (288, 384, 480, 576, 672, 768, 864, 960, 1056, 1152, 1248, 1344, 1440, 1536)


def preview_asset(max_width, max_height=None):
    """Choose the largest shipped concept image that fits the available space."""
    available = [size for size in SIZES if (ASSETS / f'{size}.png').is_file()]
    if not available:
        raise FileNotFoundError('Cherry Blossom Fusion preview is missing')
    limit = max_width if max_height is None else min(max_width, max_height * 2)
    size = max((value for value in available if value <= limit), default=available[0])
    return ASSETS / f'{size}.png'


def preview_photo(max_width, max_height=None):
    return tk.PhotoImage(file=str(preview_asset(max_width, max_height)))


class ThemePreview(tk.Canvas):
    """Stable image item; coalesced live sizing plus a final quality render."""
    def __init__(self,parent,app):
        self.app=app;self.photo=None;self.asset_width=None
        self._frame_job=None;self._quality_job=None;self._target_width=None
        with Image.open(ASSETS/'1536.png') as source:self._source=source.convert('RGB')
        super().__init__(parent,height=app.p(420),bg=app.c['panel'],highlightthickness=0,bd=0,takefocus=False)
        self.image_item=self.create_image(0,0,anchor='n')
        self.bind('<Configure>',self.draw)
        self.bind('<Destroy>',self.dispose,add='+')

    def draw(self,event=None):
        width=max(2,self.winfo_width())
        if width==self._target_width:return
        self._target_width=width
        height=max(1,round(width*self._source.height/self._source.width))
        if int(self.cget('height'))!=height:self.configure(height=height)
        if self._frame_job is None:self._frame_job=self.after(16,self.render_frame)
        if self._quality_job is not None:self.after_cancel(self._quality_job)
        self._quality_job=self.after(120,self.render_final)

    def render_frame(self):
        self._frame_job=None;self.render(False)

    def render_final(self):
        self._quality_job=None;self.render(True)

    def render(self,quality):
        if not self.winfo_exists():return
        width=self._target_width
        height=max(1,round(width*self._source.height/self._source.width))
        method=Image.Resampling.LANCZOS if quality else Image.Resampling.BILINEAR
        with self._source.resize((width,height),method) as resized:
            photo=ImageTk.PhotoImage(resized,master=self)
        self.itemconfigure(self.image_item,image=photo)
        self.coords(self.image_item,width/2,0)
        self.photo=photo;self.asset_width=width

    def dispose(self,event):
        if event.widget is not self:return
        for job in (self._frame_job,self._quality_job):
            if job is not None:self.after_cancel(job)
        self._frame_job=self._quality_job=None
        self.photo=None;self._source.close()


def build_themes(app):
    # No capability checks, background polls, or native-theme operations in beta.
    from studio_ui import ScrollArea

    area = ScrollArea(app.page_content, app)
    area.keep_scrollbar=True
    area.pack(fill='both', expand=True)
    panel = app.card(area.body, padding=24)
    panel.pack(fill='x')
    app.label(panel, 'Cherry Blossom', size=20, bold=True,
              bg=app.c['panel']).pack(anchor='w')
    app.label(panel, 'Fusion workspace concept', size=10, muted=True,
              bg=app.c['panel']).pack(anchor='w', pady=(app.p(4), app.p(20)))
    app.theme_preview = ThemePreview(panel, app)
    app.theme_preview.pack(fill='x')
    app.label(panel, 'Coming soon', size=18, bold=True,
              bg=app.c['panel']).pack(anchor='w', pady=(app.p(22), app.p(4)))
    app.label(panel, 'Theme controls are unavailable in this beta.',
              size=10, muted=True, bg=app.c['panel']).pack(anchor='w')
