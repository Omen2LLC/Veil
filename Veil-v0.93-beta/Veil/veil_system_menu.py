"""Expose About Veil in the Windows title-bar icon menu.

Use the supported common-controls subclass helper so Windows retains and
restores Tk's own window procedure during window teardown.
"""
import ctypes as c
from ctypes import wintypes as w


WM_SYSCOMMAND = 0x0112
ABOUT_COMMAND = 0x1E00
MF_BYPOSITION = 0x0400
MF_SEPARATOR = 0x0800
_SUBCLASS_ID = 0x5645494C
_CALLBACKS = []  # Native callbacks must remain alive through window teardown.


class SystemAboutMenu:
    def __init__(self, root, show_about):
        self.root = root
        self.show_about = show_about
        self.user32 = c.WinDLL('user32', use_last_error=True)
        self.comctl32 = c.WinDLL('comctl32', use_last_error=True)
        u, controls = self.user32, self.comctl32
        u.GetAncestor.argtypes = (w.HWND, w.UINT)
        u.GetAncestor.restype = w.HWND
        u.GetSystemMenu.argtypes = (w.HWND, w.BOOL)
        u.GetSystemMenu.restype = w.HMENU
        u.InsertMenuW.argtypes = (w.HMENU, w.UINT, w.UINT, c.c_size_t, w.LPCWSTR)
        u.InsertMenuW.restype = w.BOOL
        u.DeleteMenu.argtypes = (w.HMENU, w.UINT, w.UINT)
        u.DeleteMenu.restype = w.BOOL
        u.DrawMenuBar.argtypes = (w.HWND,)
        u.DrawMenuBar.restype = w.BOOL
        u.IsWindow.argtypes = (w.HWND,)
        u.IsWindow.restype = w.BOOL
        proc_type = c.WINFUNCTYPE(c.c_ssize_t, w.HWND, w.UINT, w.WPARAM,
                                  w.LPARAM, c.c_size_t, c.c_size_t)
        controls.SetWindowSubclass.argtypes = (w.HWND, proc_type, c.c_size_t, c.c_size_t)
        controls.SetWindowSubclass.restype = w.BOOL
        controls.RemoveWindowSubclass.argtypes = (w.HWND, proc_type, c.c_size_t)
        controls.RemoveWindowSubclass.restype = w.BOOL
        controls.DefSubclassProc.argtypes = (w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        controls.DefSubclassProc.restype = c.c_ssize_t
        self.hwnd = u.GetAncestor(root.winfo_id(), 2)
        if not self.hwnd:
            raise OSError('Could not find Veil title-bar window')
        self.menu = u.GetSystemMenu(self.hwnd, False)
        if not self.menu:
            raise OSError('Windows title-bar menu is unavailable')
        self.callback = proc_type(self._window_proc)
        _CALLBACKS.append(self.callback)
        self.installed = False
        if not u.InsertMenuW(self.menu, 0, MF_BYPOSITION, ABOUT_COMMAND, 'About Veil'):
            raise c.WinError(c.get_last_error())
        if not u.InsertMenuW(self.menu, 1, MF_BYPOSITION | MF_SEPARATOR, 0, None):
            u.DeleteMenu(self.menu, 0, MF_BYPOSITION)
            raise c.WinError(c.get_last_error())
        if not controls.SetWindowSubclass(self.hwnd, self.callback, _SUBCLASS_ID, 0):
            u.DeleteMenu(self.menu, 1, MF_BYPOSITION)
            u.DeleteMenu(self.menu, 0, MF_BYPOSITION)
            raise c.WinError(c.get_last_error())
        self.installed = True
        u.DrawMenuBar(self.hwnd)
        root.bind('<Destroy>', self._on_destroy, add='+')

    def _window_proc(self, hwnd, message, wparam, lparam, subclass_id, data):
        if message == WM_SYSCOMMAND and (wparam & 0xFFF0) == ABOUT_COMMAND:
            try:
                self.root.after_idle(self.show_about)
            except Exception:
                pass
            return 0
        return self.comctl32.DefSubclassProc(hwnd, message, wparam, lparam)

    def _on_destroy(self, event):
        if event.widget is self.root:
            self.close()

    def close(self):
        if not self.installed:
            return
        if self.user32.IsWindow(self.hwnd):
            self.comctl32.RemoveWindowSubclass(self.hwnd, self.callback, _SUBCLASS_ID)
            self.user32.DeleteMenu(self.menu, 1, MF_BYPOSITION)
            self.user32.DeleteMenu(self.menu, 0, MF_BYPOSITION)
            self.user32.DrawMenuBar(self.hwnd)
        self.installed = False
