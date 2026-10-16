"""Theme the native Windows caption without replacing standard window controls."""
import ctypes
import sys

def colorref(value):
    return int(value[1:3],16)|(int(value[3:5],16)<<8)|(int(value[5:7],16)<<16)

def theme_caption(root,dark,background,foreground):
    if sys.platform!='win32':return {}
    user32=ctypes.WinDLL('user32',use_last_error=True)
    dwm=ctypes.WinDLL('dwmapi')
    user32.GetAncestor.argtypes=(ctypes.c_void_p,ctypes.c_uint)
    user32.GetAncestor.restype=ctypes.c_void_p
    set_attribute=dwm.DwmSetWindowAttribute
    set_attribute.argtypes=(ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint)
    set_attribute.restype=ctypes.c_long
    hwnd=user32.GetAncestor(root.winfo_id(),2)
    if not hwnd:return {}
    results={}
    for attribute,value in ((20,int(dark)),(35,colorref(background)),(36,colorref(foreground)),(34,colorref(background))):
        data=ctypes.c_uint(value)
        results[attribute]=set_attribute(hwnd,attribute,ctypes.byref(data),ctypes.sizeof(data))
    if results[20]<0:
        data=ctypes.c_uint(int(dark));results[19]=set_attribute(hwnd,19,ctypes.byref(data),ctypes.sizeof(data))
    # Caption colors are supported on Windows 11; older builds retain native dark-mode chrome.
    return results
