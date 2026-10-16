"""Load bundled fonts privately for this process; no Windows installation needed."""
import ctypes
import logging
from pathlib import Path
from tkinter import font

REGULAR='DM Sans'
MEDIUM='DM Sans Medium'
SEMIBOLD='DM Sans SemiBold'
_loaded=False

def load_fonts(root):
    global _loaded
    if not _loaded:
        gdi=ctypes.WinDLL('gdi32',use_last_error=True)
        add=gdi.AddFontResourceExW
        add.argtypes=(ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_void_p);add.restype=ctypes.c_int
        for weight in ('Regular','Medium','SemiBold','Bold'):
            path=Path(__file__).resolve().parent/'fonts'/f'DMSans-{weight}.ttf'
            if not add(str(path),0x10,None):raise RuntimeError(f'Could not load bundled font: {path.name}')
        _loaded=True
    available=set(font.families(root))
    if not {REGULAR,MEDIUM,SEMIBOLD}<=available:
        raise RuntimeError('Bundled DM Sans font families are unavailable to the interface.')
    for name in ('TkDefaultFont','TkTextFont','TkMenuFont','TkHeadingFont','TkCaptionFont','TkSmallCaptionFont','TkIconFont','TkTooltipFont','TkFixedFont'):
        try:font.nametofont(name,root=root).configure(family=REGULAR)
        except Exception:logging.debug('Named font not present: %s',name)
