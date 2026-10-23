"""Expose About Veil in the Windows title-bar icon menu.

Use the supported common-controls subclass helper so Windows retains and
restores Tk's own window procedure during window teardown.
"""
import ctypes as c
from ctypes import wintypes as w


WM_SYSCOMMAND = 0x0112
SC_KEYMENU = 0xF100
WM_NCLBUTTONDOWN = 0x00A1
WM_NCRBUTTONUP = 0x00A5
ABOUT_COMMAND = 0x1E00
MF_BYPOSITION = 0x0400
MF_SEPARATOR = 0x0800
_SUBCLASS_ID = 0x5645494C
_CALLBACKS = []  # Native callbacks must remain alive through window teardown.


class SystemAboutMenu:
    def __init__(self, root, show_about, app=None):
        self.root = root
        self.show_about = show_about
        self.app=app;self.popup=None;self._pending_menu=False
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
        u.PostMessageW.argtypes=(w.HWND,w.UINT,w.WPARAM,w.LPARAM)
        u.PostMessageW.restype=w.BOOL
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
        self._pending_about = False
        self._poll_job = root.after(40, self._poll)
        root.bind('<Destroy>', self._on_destroy, add='+')
        self.theme_trace=app.appearance.trace_add('write',self._appearance_changed) if app else None

    def _window_proc(self, hwnd, message, wparam, lparam, subclass_id, data):
        if self.app and ((message==WM_NCLBUTTONDOWN and wparam==3)
                         or (message==WM_NCRBUTTONUP and wparam in (2,3))
                         or (message==WM_SYSCOMMAND and (wparam & 0xFFF0)==SC_KEYMENU and lparam in (0,32))):
            self._pending_menu=True
            return 0
        if message == WM_SYSCOMMAND and (wparam & 0xFFF0) == ABOUT_COMMAND:
            # A native window procedure must not call into Tcl/Tk. Let the
            # ordinary Tk event loop open About after the system menu closes.
            self._pending_about = True
            return 0
        return self.comctl32.DefSubclassProc(hwnd, message, wparam, lparam)

    def _poll(self):
        self._poll_job = None
        if not self.installed:
            return
        if self._pending_menu:
            self._pending_menu=False
            try:self.show_menu()
            except Exception:
                import logging
                logging.exception('Could not open the Veil window menu')
        if self._pending_about:
            self._pending_about = False
            try:
                self.show_about()
            finally:
                if self.installed:
                    self._poll_job = self.root.after(40, self._poll)
        elif self.installed:
            self._poll_job = self.root.after(40, self._poll)

    def _appearance_changed(self,*_):
        self.close_popup()

    def close_popup(self):
        if self.popup and not self.popup.closed:self.popup.close(restore=False)
        self.popup=None

    def show_menu(self):
        if not self.app:return
        if self.popup and not self.popup.closed:
            self.close_popup();return
        other=getattr(self.app,'editor_menu',None)
        if other and not other.closed:other.close(restore=False)
        from studio_menu import RoundedMenu
        owner=self.root;app=self.app
        class Anchor:
            def winfo_width(self):return app.p(230)
            def winfo_height(self):return 0
            def winfo_rootx(self):return owner.winfo_rootx()+app.p(6)
            def winfo_rooty(self):return owner.winfo_rooty()
            def winfo_exists(self):return owner.winfo_exists()
            def focus_set(self):return owner.focus_set()
        normal=owner.state()=='normal';sizable=all(owner.resizable())
        def system(command):
            return lambda:self.user32.PostMessageW(self.hwnd,WM_SYSCOMMAND,command,0)
        self.popup=RoundedMenu(app,Anchor(),[
            ('About Veil',self.show_about,True),None,
            ('Restore',system(0xF120),not normal),
            ('Move',system(0xF010),normal),
            ('Size',system(0xF000),normal and sizable),
            ('Minimize',system(0xF020),True),
            ('Maximize',system(0xF030),normal and sizable),None,
            ('Close  ·  Alt+F4',app.close,True)])

    def _on_destroy(self, event):
        if event.widget is self.root:
            self.close()

    def close(self):
        if not self.installed:
            return
        self.close_popup()
        if self.theme_trace:
            self.app.appearance.trace_remove('write',self.theme_trace);self.theme_trace=None
        if self._poll_job is not None:
            self.root.after_cancel(self._poll_job)
            self._poll_job = None
        if self.user32.IsWindow(self.hwnd):
            self.comctl32.RemoveWindowSubclass(self.hwnd, self.callback, _SUBCLASS_ID)
            self.user32.DeleteMenu(self.menu, 1, MF_BYPOSITION)
            self.user32.DeleteMenu(self.menu, 0, MF_BYPOSITION)
            self.user32.DrawMenuBar(self.hwnd)
        self.installed = False
