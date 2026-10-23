"""Read-only Cherry Blossom Fusion concept for the beta interface."""
from pathlib import Path
import tkinter as tk


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
    def __init__(self, parent, app):
        self.app = app
        self.photo = None
        self.asset_width = None
        super().__init__(parent, height=app.p(420), bg=app.c['panel'],
                         highlightthickness=0, bd=0, takefocus=False)
        self.bind('<Configure>', self.draw)

    def draw(self, event=None):
        width = max(2, self.winfo_width())
        asset = preview_asset(width)
        if int(asset.stem) != self.asset_width:
            self.photo = tk.PhotoImage(file=str(asset))
            self.asset_width = int(asset.stem)
        if int(self.cget('height')) != self.photo.height():
            self.configure(height=self.photo.height())
        self.delete('all')
        self.create_image(width / 2, 0, image=self.photo, anchor='n')


def build_themes(app):
    # No capability checks, background polls, or native-theme operations in beta.
    from studio_ui import ScrollArea

    area = ScrollArea(app.page_content, app)
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
