"""Approved alpha animation on a per-pixel Windows layered window; no video dependency."""
import ctypes as c
from ctypes import wintypes as w
import json
import logging
from pathlib import Path
import time
import tkinter as tk
import zipfile


class AnimationAsset:
    def __init__(self,path,screen_width):
        self.cache=None
        self.archive=zipfile.ZipFile(path)
        try:
            self.info=json.loads(self.archive.read('manifest.json'))
            if (self.info.get('schema')!=1 or self.info.get('fps')!=30 or
                self.info.get('count')!=90 or self.info.get('duration_ms')!=3000 or
                self.info.get('pixel_format')!='premultiplied BGRA' or self.info.get('sizes')!=[320,480]):
                raise ValueError('Unsupported startup animation manifest')
            self.size=480 if screen_width>=900 else 320
            expected={f'{self.size}/{i:03}.bgra' for i in range(90)}
            if not expected.issubset(self.archive.namelist()):raise ValueError('Incomplete startup animation')
            self.frame(0)
        except Exception:
            self.close();raise
    def prepare(self):
        self.cache=[self.frame(index) for index in range(90)]
    def frame(self,index):
        if self.cache is not None:return self.cache[index]
        data=self.archive.read(f'{self.size}/{index:03}.bgra')
        if len(data)!=self.size*self.size*4:raise ValueError('Invalid animation frame size')
        return data
    def close(self):
        self.cache=None
        self.archive.close()


class _BitmapHeader(c.Structure):
    _fields_=[('size',w.DWORD),('width',w.LONG),('height',w.LONG),('planes',w.WORD),
              ('bits',w.WORD),('compression',w.DWORD),('image_size',w.DWORD),
              ('x',w.LONG),('y',w.LONG),('used',w.DWORD),('important',w.DWORD)]


class _Blend(c.Structure):
    _fields_=[('operation',c.c_ubyte),('flags',c.c_ubyte),('opacity',c.c_ubyte),('format',c.c_ubyte)]


class LayeredSurface:
    def __init__(self,window,size,x,y):
        self.dc=self.bitmap=self.previous=None;self.bits=c.c_void_p()
        self.u=c.WinDLL('user32',use_last_error=True);self.g=c.WinDLL('gdi32',use_last_error=True)
        u,g=self.u,self.g
        u.GetAncestor.argtypes=[w.HWND,w.UINT];u.GetAncestor.restype=w.HWND
        u.GetWindowLongPtrW.argtypes=[w.HWND,c.c_int];u.GetWindowLongPtrW.restype=c.c_ssize_t
        u.SetWindowLongPtrW.argtypes=[w.HWND,c.c_int,c.c_ssize_t];u.SetWindowLongPtrW.restype=c.c_ssize_t
        u.UpdateLayeredWindow.argtypes=[w.HWND,w.HDC,c.POINTER(w.POINT),c.POINTER(w.SIZE),w.HDC,c.POINTER(w.POINT),w.DWORD,c.POINTER(_Blend),w.DWORD]
        u.UpdateLayeredWindow.restype=w.BOOL
        g.CreateCompatibleDC.argtypes=[w.HDC];g.CreateCompatibleDC.restype=w.HDC
        g.CreateDIBSection.argtypes=[w.HDC,c.c_void_p,w.UINT,c.POINTER(c.c_void_p),w.HANDLE,w.DWORD]
        g.CreateDIBSection.restype=w.HBITMAP
        g.SelectObject.argtypes=[w.HDC,w.HGDIOBJ];g.SelectObject.restype=w.HGDIOBJ
        g.DeleteObject.argtypes=[w.HGDIOBJ];g.DeleteDC.argtypes=[w.HDC]
        self.hwnd=u.GetAncestor(window.winfo_id(),2)
        self.position=w.POINT(x,y);self.extent=w.SIZE(size,size);self.origin=w.POINT(0,0)
        self.blend=_Blend(0,0,255,1)
        self.byte_count=size*size*4
        try:
            style=u.GetWindowLongPtrW(self.hwnd,-20)
            # Real alpha, not a color-key cutout. Keep the startup out of Alt+Tab.
            c.set_last_error(0)
            u.SetWindowLongPtrW(self.hwnd,-20,style|0x80000|0x80|0x8000000)
            if c.get_last_error():raise c.WinError(c.get_last_error())
            self.dc=g.CreateCompatibleDC(None)
            if not self.dc:raise c.WinError(c.get_last_error())
            header=_BitmapHeader(c.sizeof(_BitmapHeader),size,-size,1,32,0,0,0,0,0,0)
            self.bitmap=g.CreateDIBSection(self.dc,c.byref(header),0,c.byref(self.bits),None,0)
            if not self.bitmap or not self.bits.value:raise c.WinError(c.get_last_error())
            self.previous=g.SelectObject(self.dc,self.bitmap)
            if not self.previous or self.previous==c.c_void_p(-1).value:raise c.WinError(c.get_last_error())
        except Exception:
            self.close();raise
    def present(self,data):
        if len(data)!=self.byte_count:raise ValueError('Incorrect animation buffer size')
        c.memmove(self.bits,data,len(data))
        if not self.u.UpdateLayeredWindow(self.hwnd,None,c.byref(self.position),c.byref(self.extent),
                self.dc,c.byref(self.origin),0,c.byref(self.blend),2):
            raise c.WinError(c.get_last_error())
    def close(self):
        if self.dc and self.previous:self.g.SelectObject(self.dc,self.previous)
        if self.bitmap:self.g.DeleteObject(self.bitmap)
        if self.dc:self.g.DeleteDC(self.dc)
        self.dc=self.bitmap=self.previous=None


class StartupAnimation:
    def __init__(self,root,on_done,folder):
        self.root=root;self.on_done=on_done;self.done=False;self.job=None
        self.window=None;self.surface=None;self.asset=None;self.last_frame=-1
        try:
            sw,sh=root.winfo_screenwidth(),root.winfo_screenheight()
            self.asset=AnimationAsset(Path(folder)/'veil-startup.vaf',min(sw,sh*1.5))
            self.asset.prepare()
            size=self.asset.size;x=(sw-size)//2;y=(sh-size)//2
            self.window=tk.Toplevel(root);self.window.withdraw();self.window.overrideredirect(True)
            self.window.geometry(f'{size}x{size}+{x}+{y}')
            self.window.attributes('-topmost',True);self.window.update_idletasks()
            self.surface=LayeredSurface(self.window,size,x,y)
            self.window.bind('<Destroy>',self.destroyed)
            # The user requested the approved reveal, independently of Windows'
            # animation setting. Decode before starting its clock, then play once.
            self.duration=self.asset.info['duration_ms']/1000
            self.window.deiconify()
            self.window.update_idletasks()
            self.surface.present(self.asset.frame(0))
            self.last_frame=0
            self.started=time.perf_counter()
            self.tick()
        except Exception:
            logging.exception('Startup animation unavailable; opening Veil directly')
            self.finish()
    def tick(self):
        self.job=None
        if self.done:return
        elapsed=time.perf_counter()-self.started
        if elapsed>=self.duration:self.finish();return
        index=min(89,int(elapsed*self.asset.info['fps']))
        try:
            if index!=self.last_frame:
                self.surface.present(self.asset.frame(index));self.last_frame=index
            self.job=self.root.after(8,self.tick)
        except Exception:
            logging.exception('Startup playback failed; opening Veil directly');self.finish()
    def destroyed(self,event):
        if event.widget is self.window and not self.done:self.finish(open_main=False)
    def finish(self,open_main=True):
        if self.done:return
        self.done=True
        if self.job is not None:
            try:self.root.after_cancel(self.job)
            except tk.TclError:pass
            self.job=None
        # End the animation completely before exposing the prepared main window.
        if self.window:
            try:self.window.destroy()
            except tk.TclError:pass
        if self.surface:self.surface.close()
        if self.asset:self.asset.close()
        if open_main:self.on_done()



def show_startup(root,on_done,folder):
    animation=StartupAnimation(root,on_done,folder)
    root._veil_startup=animation
    return animation
