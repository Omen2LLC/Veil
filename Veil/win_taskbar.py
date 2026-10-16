"""Give the hosted Tk window its own Windows taskbar pin identity."""

import ctypes
import uuid
import os
from pathlib import Path


APP_ID = 'Veil.Desktop'
_FORMAT_ID = uuid.UUID('9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3')
_STORE_ID = uuid.UUID('886d8eeb-8cf2-4446-8d02-cdba1dbdcf99')
_VT_LPWSTR = 31


def round_splash_window(window, width, height, radius):
    """Clip the native window itself, including the artwork's corner pixels."""
    user32=ctypes.WinDLL('user32',use_last_error=True)
    gdi32=ctypes.WinDLL('gdi32',use_last_error=True)
    user32.GetAncestor.argtypes=(ctypes.c_void_p,ctypes.c_uint)
    user32.GetAncestor.restype=ctypes.c_void_p
    gdi32.CreateRoundRectRgn.argtypes=(ctypes.c_int,)*6
    gdi32.CreateRoundRectRgn.restype=ctypes.c_void_p
    user32.SetWindowRgn.argtypes=(ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int)
    user32.SetWindowRgn.restype=ctypes.c_int
    gdi32.DeleteObject.argtypes=(ctypes.c_void_p,)
    gdi32.DeleteObject.restype=ctypes.c_int
    hwnd=user32.GetAncestor(window.winfo_id(),2)
    if not hwnd:
        raise ctypes.WinError(ctypes.get_last_error())
    region=gdi32.CreateRoundRectRgn(0,0,width+1,height+1,radius*2,radius*2)
    if not region:
        raise ctypes.WinError(ctypes.get_last_error())
    if not user32.SetWindowRgn(hwnd,region,True):
        error=ctypes.get_last_error()
        gdi32.DeleteObject(region)
        raise ctypes.WinError(error)
    # Windows owns the region after a successful SetWindowRgn call.


class _Guid(ctypes.Structure):
    _fields_ = [('data1', ctypes.c_uint32), ('data2', ctypes.c_uint16),
                ('data3', ctypes.c_uint16), ('data4', ctypes.c_ubyte * 8)]

    @classmethod
    def from_uuid(cls, value):
        return cls.from_buffer_copy(value.bytes_le)


class _PropertyKey(ctypes.Structure):
    _fields_ = [('fmtid', _Guid), ('pid', ctypes.c_uint32)]


class _PropVariant(ctypes.Structure):
    _fields_ = [('vt', ctypes.c_ushort), ('reserved', ctypes.c_ushort * 3),
                ('data', ctypes.c_ubyte * 16)]


def _check(hr, action):
    if hr < 0:
        raise OSError(f'{action} failed: HRESULT 0x{hr & 0xffffffff:08X}')


class WindowTaskbarIdentity:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        shell32 = ctypes.WinDLL('shell32')
        get_store = shell32.SHGetPropertyStoreForWindow
        get_store.argtypes = (ctypes.c_void_p, ctypes.POINTER(_Guid), ctypes.POINTER(ctypes.c_void_p))
        get_store.restype = ctypes.c_long
        self._store = ctypes.c_void_p()
        iid = _Guid.from_uuid(_STORE_ID)
        _check(get_store(hwnd, ctypes.byref(iid), ctypes.byref(self._store)), 'SHGetPropertyStoreForWindow')
        table = ctypes.cast(self._store, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        self._release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[2])
        self._set_value = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                             ctypes.POINTER(_PropertyKey),
                                             ctypes.POINTER(_PropVariant))(table[6])

    def _set(self, pid, value):
        key = _PropertyKey(_Guid.from_uuid(_FORMAT_ID), pid)
        prop = _PropVariant()
        if value is not None:
            wide = ctypes.create_unicode_buffer(value)
            prop.vt = _VT_LPWSTR
            ctypes.c_void_p.from_buffer(prop, 8).value = ctypes.addressof(wide)
        _check(self._set_value(self._store, ctypes.byref(key), ctypes.byref(prop)), f'AppUserModel property {pid}')

    def configure(self, folder):
        folder = Path(folder).resolve()
        from studio_launcher import ensure_launcher
        launcher=ensure_launcher(folder)
        wscript=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32'/'wscript.exe'
        self._set(2, f'"{wscript}" "{launcher}"')
        self._set(3, f'{folder / "veil-icon.ico"},0')
        self._set(4, 'Veil')
        # Set the ID last: this tells the taskbar to refresh the window's pin data.
        self._set(5, APP_ID)

    def close(self):
        if self._store:
            try:
                is_window = ctypes.WinDLL('user32').IsWindow
                is_window.argtypes = (ctypes.c_void_p,)
                is_window.restype = ctypes.c_int
                if is_window(self.hwnd):
                    for pid in (5, 4, 3, 2):
                        self._set(pid, None)
            finally:
                self._release(self._store)
                self._store = None


def configure_window(root, folder):
    user32 = ctypes.WinDLL('user32')
    user32.GetAncestor.argtypes = (ctypes.c_void_p, ctypes.c_uint)
    user32.GetAncestor.restype = ctypes.c_void_p
    hwnd = user32.GetAncestor(root.winfo_id(), 2)  # GA_ROOT: Tk's outer taskbar window.
    if not hwnd:
        raise OSError('Could not find Veil taskbar window')
    identity = WindowTaskbarIdentity(hwnd)
    try:
        identity.configure(folder)
    except Exception:
        identity.close()
        raise
    return identity
