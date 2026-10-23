"""Guarded, automatic Qt repaint trigger for Media Pool thumbnail markers.

Resolve Studio 21.1.0.14 sometimes retains a painted thumbnail after its
verified 11x12 color resource changes. A posted click on verified empty Media
Pool background makes the thumbnail redraw without moving the cursor.
"""
import ctypes
import ctypes.wintypes as w
import json
import time

from palette_core import atomic_json

SCHEMA = 1
BACKGROUND_MAX = 80
PATTERN = ((0, 0), (-6, 0), (6, 0), (0, -6), (0, 6))
WIDE_PATTERN = ((-18, -18), (18, -18), (-18, 18), (18, 18))


class MediaPoolRefresh:
    def __init__(self, folder):
        self.path = folder / 'media_pool_refresh_point.json'
        self.pending_pid = None
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.gdi32 = ctypes.WinDLL('gdi32', use_last_error=True)
        u, g = self.user32, self.gdi32
        u.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM), w.LPARAM]
        u.EnumWindows.restype = w.BOOL
        u.GetWindowThreadProcessId.argtypes = [w.HWND, ctypes.POINTER(w.DWORD)]
        u.GetWindowThreadProcessId.restype = w.DWORD
        u.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
        u.GetWindowTextW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
        u.IsWindowVisible.argtypes = [w.HWND]
        u.IsWindowVisible.restype = w.BOOL
        u.GetClientRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
        u.GetClientRect.restype = w.BOOL
        u.GetCursorPos.argtypes = [ctypes.POINTER(w.POINT)]
        u.GetCursorPos.restype = w.BOOL
        u.WindowFromPoint.argtypes = [w.POINT]
        u.WindowFromPoint.restype = w.HWND
        u.ScreenToClient.argtypes = [w.HWND, ctypes.POINTER(w.POINT)]
        u.ScreenToClient.restype = w.BOOL
        u.ClientToScreen.argtypes = [w.HWND, ctypes.POINTER(w.POINT)]
        u.ClientToScreen.restype = w.BOOL
        u.GetDC.argtypes = [w.HWND]
        u.GetDC.restype = w.HDC
        u.ReleaseDC.argtypes = [w.HWND, w.HDC]
        u.ReleaseDC.restype = ctypes.c_int
        g.GetPixel.argtypes = [w.HDC, ctypes.c_int, ctypes.c_int]
        g.GetPixel.restype = w.COLORREF
        u.GetForegroundWindow.argtypes = []
        u.GetForegroundWindow.restype = w.HWND
        u.RedrawWindow.argtypes = [w.HWND, ctypes.POINTER(w.RECT), w.HANDLE, w.UINT]
        u.RedrawWindow.restype = w.BOOL
        u.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        u.PostMessageW.restype = w.BOOL

    @staticmethod
    def _check(value, operation):
        if not value:
            raise ctypes.WinError(ctypes.get_last_error(), operation)
        return value

    def _pid(self, hwnd):
        result = w.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(result))
        return result.value

    def _window(self, pid):
        callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        found = []

        @callback_type
        def collect(hwnd, unused):
            if self._pid(hwnd) != pid or not self.user32.IsWindowVisible(hwnd):
                return True
            name = ctypes.create_unicode_buffer(256)
            title = ctypes.create_unicode_buffer(256)
            self.user32.GetClassNameW(hwnd, name, 256)
            self.user32.GetWindowTextW(hwnd, title, 256)
            if 'QWindowIcon' in name.value and title.value.startswith('DaVinci Resolve'):
                found.append(hwnd)
            return True

        self._check(self.user32.EnumWindows(collect, 0), 'EnumWindows')
        if len(found) != 1:
            raise RuntimeError('Expected one visible Resolve main window. Recalibrate when its layout is stable.')
        return found[0]

    def _size(self, hwnd):
        rect = w.RECT()
        self._check(self.user32.GetClientRect(hwnd, ctypes.byref(rect)), 'GetClientRect')
        return [rect.right - rect.left, rect.bottom - rect.top]

    def _screen(self, hwnd, xy):
        point = w.POINT(*xy)
        self._check(self.user32.ClientToScreen(hwnd, ctypes.byref(point)), 'ClientToScreen')
        return point

    def _pattern(self, screen):
        dc = self._check(self.user32.GetDC(None), 'GetDC')
        try:
            samples = []
            for dx, dy in PATTERN:
                pixel = self.gdi32.GetPixel(dc, screen.x + dx, screen.y + dy)
                if pixel == 0xFFFFFFFF:
                    raise RuntimeError('Cannot inspect the refresh point on screen.')
                samples.append('#%02X%02X%02X' % (pixel & 255, (pixel >> 8) & 255, (pixel >> 16) & 255))
            return samples
        finally:
            self.user32.ReleaseDC(None, dc)

    def _wide_blank(self, screen, color):
        dc = self._check(self.user32.GetDC(None), 'GetDC')
        try:
            expected = int(color[5:7] + color[3:5] + color[1:3], 16)
            return all(self.gdi32.GetPixel(dc, screen.x + dx, screen.y + dy) == expected
                       for dx, dy in WIDE_PATTERN)
        finally:
            self.user32.ReleaseDC(None, dc)

    @staticmethod
    def _blank(samples):
        if (not isinstance(samples, list) or len(samples) != len(PATTERN) or
            not all(isinstance(v, str) for v in samples) or len(set(samples)) != 1):
            return False
        color = samples[0]
        if not isinstance(color, str) or len(color) != 7 or not color.startswith('#'):
            return False
        try:rgb = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
        except ValueError:return False
        return max(rgb) <= BACKGROUND_MAX and max(rgb) - min(rgb) <= 12

    def discover(self, pid):
        """Find a broad, uniform blank region in the upper-left Media Pool area."""
        hwnd = self._window(pid)
        size = self._size(hwnd)
        width, height = size
        if width < 900 or height < 600:
            raise RuntimeError('Resolve window is too small for automatic Media Pool repaint.')
        # Resolve's Media Pool is the upper-left pane in this supported Edit layout.
        # Search its middle/lower area, not its toolbar or the timeline.
        deadline=time.monotonic()+0.4
        for y in range(int(height * .60), int(height * .28), -18):
            for x in range(int(width * .29), int(width * .12), -18):
                if time.monotonic()>=deadline:
                    raise RuntimeError('Media Pool refresh search timed out. Expose empty bin space and apply again.')
                client = [x, y]
                screen = self._screen(hwnd, client)
                if self.user32.WindowFromPoint(screen) != hwnd:
                    continue
                samples = self._pattern(screen)
                if samples[0] != '#28282E' or not self._blank(samples) or not self._wide_blank(screen, samples[0]):
                    continue
                record = {'schema': SCHEMA, 'client_xy': client,
                          'client_size': size, 'background_samples': samples}
                atomic_json(self.path, record)
                return record
        raise RuntimeError('No verified empty Media Pool background was visible. Move Veil clear of the Media Pool or expand the bin.')

    def load(self):
        if not self.path.exists():
            return None
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if (data.get('schema') != SCHEMA or
            not isinstance(data.get('client_xy'), list) or
            len(data['client_xy']) != 2 or
            not all(isinstance(v, int) for v in data['client_xy']) or
            not isinstance(data.get('client_size'), list) or
            len(data['client_size']) != 2 or
            not all(isinstance(v, int) for v in data['client_size']) or
            not all(0 < v < 32768 for v in data['client_size']) or
            not all(8 <= p < bound - 8 for p, bound in zip(data['client_xy'], data['client_size'])) or
            not self._blank(data.get('background_samples'))):
            raise RuntimeError('Refresh-point file is invalid. Recalibrate in Veil.')
        return data

    def _verified_screen(self, hwnd, record):
        if self._size(hwnd) != record['client_size']:
            raise RuntimeError('Resolve window size changed.')
        screen = self._screen(hwnd, record['client_xy'])
        if self.user32.WindowFromPoint(screen) != hwnd:
            raise RuntimeError('Refresh point is covered or outside Resolve.')
        if self._pattern(screen) != record['background_samples'] or not self._wide_blank(screen, record['background_samples'][0]):
            raise RuntimeError('Media Pool layout changed at the refresh point.')
        return screen

    def refresh_pending(self, pid):
        """Only retry a deferred cache refresh after the user returns to Resolve."""
        return self.pending_pid == pid and self.user32.GetForegroundWindow() == self._window(pid)

    def repaint(self, pid):
        """Request redraw without activation; guarded cache click only in foreground."""
        hwnd = self._window(pid)
        # Queue invalidation without synchronous painting or any z-order changes.
        self._check(self.user32.RedrawWindow(hwnd, None, None, 0x0001 | 0x0080), 'Resolve redraw')
        if self.user32.GetForegroundWindow() != hwnd:
            self.pending_pid = pid
            return False
        self.pending_pid = None
        try:
            record = self.load()
            if record is None:
                raise RuntimeError('No saved refresh point.')
            self._verified_screen(hwnd, record)
        except (OSError, ValueError, RuntimeError, KeyError, TypeError):
            record = self.discover(pid)
            self._verified_screen(hwnd, record)
        # The user may switch away while the bounded search is running.
        if self.user32.GetForegroundWindow() != hwnd:
            self.pending_pid = pid
            return False
        client = record['client_xy']
        self._verified_screen(hwnd, record)
        packed = (client[0] & 0xFFFF) | ((client[1] & 0xFFFF) << 16)
        self._check(self.user32.PostMessageW(hwnd, 0x0201, 1, packed), 'Media Pool WM_LBUTTONDOWN')
        self._check(self.user32.PostMessageW(hwnd, 0x0202, 0, packed), 'Media Pool WM_LBUTTONUP')
        return True
