"""Expose About Veil in the native Windows title-bar icon menu."""
import ctypes as c
from ctypes import wintypes as w


WM_SYSCOMMAND = 0x0112
GWLP_WNDPROC = -4
ABOUT_COMMAND = 0x1E00
MF_BYPOSITION = 0x0400
MF_SEPARATOR = 0x0800


class SystemAboutMenu:
    def __init__(self, root, show_about):
        self.root = root
        self.show_about = show_about
        self.user32 = c.WinDLL('user32', use_last_error=True)
        u = self.user32
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
        u.GetWindowLongPtrW.argtypes = (w.HWND, c.c_int)
        u.GetWindowLongPtrW.restype = c.c_ssize_t
        u.SetWindowLongPtrW.argtypes = (w.HWND, c.c_int, c.c_ssize_t)
        u.SetWindowLongPtrW.restype = c.c_ssize_t
        u.CallWindowProcW.argtypes = (c.c_void_p, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        u.CallWindowProcW.restype = c.c_ssize_t
        u.IsWindow.argtypes = (w.HWND,)
        u.IsWindow.restype = w.BOOL
        self.hwnd = u.GetAncestor(root.winfo_id(), 2)
        if not self.hwnd:
            raise OSError('Could not find Veil title-bar window')
        self.menu = u.GetSystemMenu(self.hwnd, False)
        if not self.menu:
            raise c.WinError(c.get_last_error())
        self.old_proc = None
        self.callback = None
        self.callback_address = None
        if not u.InsertMenuW(self.menu, 0, MF_BYPOSITION, ABOUT_COMMAND, 'About Veil'):
            raise c.WinError(c.get_last_error())
        if not u.InsertMenuW(self.menu, 1, MF_BYPOSITION | MF_SEPARATOR, 0, None):
            u.DeleteMenu(self.menu, ABOUT_COMMAND, 0)
            raise c.WinError(c.get_last_error())
        try:
            proc_type = c.WINFUNCTYPE(c.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
            self.callback = proc_type(self._window_proc)
            self.callback_address = c.cast(self.callback, c.c_void_p).value
            c.set_last_error(0)
            self.old_proc = u.SetWindowLongPtrW(self.hwnd, GWLP_WNDPROC, self.callback_address)
            if not self.old_proc and c.get_last_error():
                raise c.WinError(c.get_last_error())
        except Exception:
            u.DeleteMenu(self.menu, 1, MF_BYPOSITION)
            u.DeleteMenu(self.menu, 0, MF_BYPOSITION)
            raise
        u.DrawMenuBar(self.hwnd)
        root.bind('<Destroy>', self._on_destroy, add='+')

    def _window_proc(self, hwnd, message, wparam, lparam):
        if message == WM_SYSCOMMAND and (wparam & 0xFFF0) == ABOUT_COMMAND:
            try:
                self.root.after_idle(self.show_about)
            except (RuntimeError, c.ArgumentError):
                pass
            return 0
        return self.user32.CallWindowProcW(self.old_proc, hwnd, message, wparam, lparam)

    def _on_destroy(self, event):
        if event.widget is self.root:
            self.close()

    def close(self):
        if self.old_proc is None:
            return
        u = self.user32
        if u.IsWindow(self.hwnd):
            if u.GetWindowLongPtrW(self.hwnd, GWLP_WNDPROC) == self.callback_address:
                u.SetWindowLongPtrW(self.hwnd, GWLP_WNDPROC, self.old_proc)
            u.DeleteMenu(self.menu, 1, MF_BYPOSITION)
            u.DeleteMenu(self.menu, 0, MF_BYPOSITION)
            u.DrawMenuBar(self.hwnd)
        self.old_proc = None
        self.callback = None
