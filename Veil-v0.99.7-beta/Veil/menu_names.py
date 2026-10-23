"""Build-locked first-frame native Clip Color names for Resolve 21.1.0.14."""
import ctypes
import json
import struct
from pathlib import Path

from palette_core import LABELS, atomic_json
from palette_names import validate_names
from resolve_palette import MODULEENTRY32W
from resolve_profiles import component_layout

SOURCE_RVAS = {
    'Green': 0x248EE3A, 'Teal': 0x248EE46, 'Blue': 0x248EE52,
    'Purple': 0x248EE5B, 'Pink': 0x248EE64, 'Tan': 0x248EE6D,
    'Brown': 0x248EE76, 'Apricot': 0x248EE7F, 'Beige': 0x248EE88,
    'Chocolate': 0x248EE91, 'Lime': 0x248EE9A, 'Navy': 0x248EEA3,
    'Olive': 0x248EEAC, 'Orange': 0x248EEB5, 'Violet': 0x248EEBE,
    'Yellow': 0x248EEC7,
}
SOURCE_STOCK = {
    'Green': bytes.fromhex('4c8d054b046805'),
    'Teal': bytes.fromhex('4c8d0567748005'),
    'Blue': bytes.fromhex('4c8d053b046805'),
    'Purple': bytes.fromhex('4c8d0566cf7805'),
    'Pink': bytes.fromhex('4c8d0555cf7805'),
    'Tan': bytes.fromhex('4c8d0548748005'),
    'Brown': bytes.fromhex('4c8d0543748005'),
    'Apricot': bytes.fromhex('4c8d0542748005'),
    'Beige': bytes.fromhex('4c8d0541748005'),
    'Chocolate': bytes.fromhex('4c8d0540748005'),
    'Lime': bytes.fromhex('4c8d0543748005'),
    'Navy': bytes.fromhex('4c8d0542748005'),
    'Olive': bytes.fromhex('4c8d0541748005'),
    'Orange': bytes.fromhex('4c8d05fcce7805'),
    'Violet': bytes.fromhex('4c8d0537748005'),
    'Yellow': bytes.fromhex('4c8d05a67f6b05'),
}
HELPER_RVA = 0x248EE10
HELPER_SIGNATURE = bytes.fromhex('40534883ec40ffc2488bd983fa100f87')
PAGE_SIZE = 4096
STOCK_NAMES = list(LABELS)


class NativeMenuNames:
    def __init__(self, session):
        self.s = session
        self.k = session.k
        self.layout = component_layout(session.signature, 'menu_names', {
            name: globals()[name] for name in ('SOURCE_RVAS', 'SOURCE_STOCK', 'HELPER_RVA', 'HELPER_SIGNATURE')},
            byte_fields=('HELPER_SIGNATURE',), byte_maps=('SOURCE_STOCK',))
        self.names = list(STOCK_NAMES)
        self.page = None
        self.offsets = {}
        self.redirected = False
        self.failed = False
        self.recovery = self.s.folder / 'menu_name_recovery.json'

        self.k.VirtualAllocEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                         ctypes.c_size_t, ctypes.c_ulong,
                                         ctypes.c_ulong]
        self.k.VirtualAllocEx.restype = ctypes.c_void_p
        self.k.VirtualFreeEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                        ctypes.c_size_t, ctypes.c_ulong]
        self.k.VirtualFreeEx.restype = ctypes.c_int
        self.k.VirtualProtectEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                           ctypes.c_size_t, ctypes.c_ulong,
                                           ctypes.POINTER(ctypes.c_ulong)]
        self.k.VirtualProtectEx.restype = ctypes.c_int
        self.k.FlushInstructionCache.argtypes = [ctypes.c_void_p,
                                                ctypes.c_void_p,
                                                ctypes.c_size_t]
        self.k.FlushInstructionCache.restype = ctypes.c_int

        if self.s.read(self.s.base + self.layout.HELPER_RVA, len(self.layout.HELPER_SIGNATURE)) != self.layout.HELPER_SIGNATURE:
            raise RuntimeError('Resolve native menu name helper differs from the verified build.')
        self._recover_interrupted_session()
        self._verify_stock_sources()

        snap = self.k.CreateToolhelp32Snapshot(0x18, session.pid)
        if snap == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        entry = MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        modules = {}
        try:
            ok = self.k.Module32FirstW(snap, ctypes.byref(entry))
            while ok:
                modules[entry.szModule.lower()] = entry.modBaseAddr
                ok = self.k.Module32NextW(snap, ctypes.byref(entry))
        finally:
            self.k.CloseHandle(snap)
        self.widgets = modules.get('qt5widgets.dll')
        if not self.widgets:
            raise RuntimeError('Resolve Qt menu module is missing.')
        for rva, signature in {
            0xEA70: '4883ec28488b0d053153004885c97438',
            0x331E0: '40534883ec20488bda488b51084881c290010000',
            0xBDC0: '48895c24184889542410574883ec40488bda',
            0x4EC30: '488b5108488b8210010000',
        }.items():
            if self.s.read(self.widgets + rva, len(bytes.fromhex(signature))) != bytes.fromhex(signature):
                raise RuntimeError('Qt menu layout signature changed. Restart Resolve.')

    def _verify_stock_sources(self):
        if self.s.read(self.s.base + self.layout.HELPER_RVA, len(self.layout.HELPER_SIGNATURE)) != self.layout.HELPER_SIGNATURE:
            raise RuntimeError('Resolve native menu name helper differs from the verified build.')
        for label in LABELS:
            if self.s.read(self.s.base + self.layout.SOURCE_RVAS[label], 7) != self.layout.SOURCE_STOCK[label]:
                raise RuntimeError('Resolve menu name source changed. Restart Resolve before continuing.')

    def _read_instruction(self, label):
        return self.s.read(self.s.base + self.layout.SOURCE_RVAS[label], 7)

    def _code_page_write(self, entries, use_original=False):
        start = min(self.layout.SOURCE_RVAS.values())
        end = max(self.layout.SOURCE_RVAS.values()) + 7
        page_start = (self.s.base + start) & ~0xFFF
        length = ((self.s.base + end - page_start + 0xFFF) & ~0xFFF)
        old = ctypes.c_ulong()
        back = ctypes.c_ulong()
        if not self.k.VirtualProtectEx(self.s.handle, page_start, length, 0x40,
                                       ctypes.byref(old)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            for label in LABELS:
                original = bytes.fromhex(entries[label]['original'])
                replacement = bytes.fromhex(entries[label]['replacement'])
                current = self._read_instruction(label)
                allowed = (original, replacement) if use_original else (original,)
                if current not in allowed:
                    raise RuntimeError('Native menu source changed during update.')
            for label in LABELS:
                value = entries[label]['original' if use_original else 'replacement']
                self.s.write(self.s.base + self.layout.SOURCE_RVAS[label] + 3, bytes.fromhex(value)[3:7])
            if not self.k.FlushInstructionCache(self.s.handle, page_start, length):
                raise ctypes.WinError(ctypes.get_last_error())
            for label in LABELS:
                value = bytes.fromhex(entries[label]['original' if use_original else 'replacement'])
                if self._read_instruction(label) != value:
                    raise RuntimeError('Native menu name source verification failed.')
        finally:
            if not self.k.VirtualProtectEx(self.s.handle, page_start, length,
                                           old.value, ctypes.byref(back)):
                raise RuntimeError('Could not restore Resolve code-page protection. Restart Resolve.')

    def _validate_journal(self, data):
        if data.get('schema') != 1 or data.get('identity') != self.s.identity():
            return False
        page = data.get('page')
        if not isinstance(page, int) or not page:
            return False
        entries = data.get('entries')
        if not isinstance(entries, dict) or set(entries) != set(LABELS):
            return False
        for label in LABELS:
            try:
                original = bytes.fromhex(entries[label]['original'])
                replacement = bytes.fromhex(entries[label]['replacement'])
                current = self._read_instruction(label)
            except (KeyError, TypeError, ValueError):
                return False
            if original != self.layout.SOURCE_STOCK[label] or len(replacement) != 7:
                return False
            if replacement[:3] != original[:3] or current not in (original, replacement):
                return False
            displacement = struct.unpack('<i', replacement[3:])[0]
            target = self.s.base + self.layout.SOURCE_RVAS[label] + 7 + displacement
            if not page <= target < page + PAGE_SIZE:
                return False
        return True

    def _recover_interrupted_session(self):
        if not self.recovery.exists():
            return
        try:
            data = json.loads(self.recovery.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raise RuntimeError('Native menu recovery record is unreadable. Restart Resolve.')
        if data.get('identity') != self.s.identity():
            return
        if data.get('schema') is None:
            # Older previews saved only temporary menu-widget headers here.
            return
        if not self.s.writable:
            raise RuntimeError('Interrupted native name change found. Restart Resolve or reconnect in normal mode to restore it.')
        if not self._validate_journal(data):
            raise RuntimeError('Native menu recovery values do not match Resolve. Restart Resolve.')
        entries = data['entries']
        originals = {label: dict(original=entries[label]['original'],
                                 replacement=entries[label]['replacement'])
                     for label in LABELS}
        self._code_page_write(originals, use_original=True)
        if not self.k.VirtualFreeEx(self.s.handle, data['page'], 0, 0x8000):
            raise ctypes.WinError(ctypes.get_last_error())
        self.recovery.unlink(missing_ok=True)

    def _pack_names(self, names):
        result = bytearray(PAGE_SIZE)
        offsets = {}
        for index, (label, name) in enumerate(zip(LABELS, names)):
            encoded = name.encode('utf-8')
            if len(encoded) >= 256:
                raise ValueError('A native menu name exceeds its UTF-8 buffer.')
            offset = index * 256
            offsets[label] = offset
            result[offset:offset + len(encoded)] = encoded
        return bytes(result), offsets

    def _allocate_near_helper(self):
        origin = self.s.base + self.layout.HELPER_RVA
        for delta in range(0x26000000, 0x70000000, 0x1000000):
            candidate = self.k.VirtualAllocEx(self.s.handle, self.s.base + delta,
                                              PAGE_SIZE, 0x3000, 0x04)
            address = candidate or 0
            if address and -(1 << 31) <= address - origin < (1 << 31):
                return address
            if address:
                self.k.VirtualFreeEx(self.s.handle, address, 0, 0x8000)
        raise RuntimeError('Resolve has no nearby memory available for custom menu names.')

    def _make_journal(self, page, offsets, names):
        entries = {}
        for label, name in zip(LABELS, names):
            rva = self.layout.SOURCE_RVAS[label]
            original = self.layout.SOURCE_STOCK[label]
            target = page + offsets[label]
            displacement = target - (self.s.base + rva + 7)
            if not -(1 << 31) <= displacement < (1 << 31):
                raise RuntimeError('Custom name buffer is outside the native instruction range.')
            entries[label] = {
                'original': original.hex(),
                'replacement': original[:3] + struct.pack('<i', displacement),
                'name': name,
            }
            entries[label]['replacement'] = entries[label]['replacement'].hex()
        return dict(schema=1, identity=self.s.identity(), page=page, entries=entries)

    def _redirect_sources(self, names):
        blob, offsets = self._pack_names(names)
        page = self._allocate_near_helper()
        try:
            self.s.write(page, blob)
            journal = self._make_journal(page, offsets, names)
            atomic_json(self.recovery, journal)
            try:
                self._code_page_write(journal['entries'])
            except Exception as exc:
                try:
                    self._code_page_write(journal['entries'], use_original=True)
                    if not self.k.VirtualFreeEx(self.s.handle, page, 0, 0x8000):
                        raise ctypes.WinError(ctypes.get_last_error())
                    self.recovery.unlink(missing_ok=True)
                except Exception as rollback:
                    self.failed = True
                    raise RuntimeError(f'Native name redirect failed and rollback could not be verified. Restart Resolve. {exc}; {rollback}') from exc
                raise
        except Exception:
            if not self.recovery.exists():
                self.k.VirtualFreeEx(self.s.handle, page, 0, 0x8000)
            raise
        self.page = page
        self.offsets = offsets
        self.redirected = True

    def require_closed(self):
        popup = self.ptr(self.widgets + 0x541B80)
        roots = self.qlist(popup, 16) if popup else []
        if len(roots) >= 2:
            raise RuntimeError('Close the native Clip Color submenu before applying a palette.')

    def ptr(self, address):
        return struct.unpack('<Q', self.s.read(address, 8))[0]

    def qlist(self, address, limit=128):
        data = self.ptr(address)
        if not data:
            return []
        ref, alloc, begin, end = struct.unpack('<4i', self.s.read(data, 16))
        if not 0 <= begin <= end <= alloc <= 100000 or end - begin > limit:
            raise ValueError('Unexpected Qt menu list layout.')
        return [self.ptr(data + 16 + i * 8) for i in range(begin, end)]

    def set_names(self, names):
        if getattr(self, 'failed', False):
            raise RuntimeError('Native menu names need recovery. Restart Resolve before continuing.')
        names = validate_names(list(names))
        self.require_closed()
        if names == self.names:
            return
        if self.redirected:
            self.check()
        else:
            self._verify_stock_sources()
        if not self.redirected:
            if names == STOCK_NAMES:
                self.names = names
                return
            self._redirect_sources(names)
        else:
            blob, offsets = self._pack_names(names)
            if offsets != self.offsets:
                raise RuntimeError('Native name buffer layout changed unexpectedly.')
            self.s.write(self.page, blob)
        self.names = names

    def check(self):
        if getattr(self, 'failed', False):
            raise RuntimeError('Native menu name source is unsafe. Restart Resolve before continuing.')
        if self.redirected:
            data = json.loads(self.recovery.read_text(encoding='utf-8'))
            if not self._validate_journal(data):
                self.failed = True
                raise RuntimeError('Native menu name source changed. Restart Resolve before continuing.')
        else:
            self._verify_stock_sources()

    def close(self):
        if not self.s.alive() or not self.redirected:
            return
        self.require_closed()
        data = json.loads(self.recovery.read_text(encoding='utf-8'))
        if not self._validate_journal(data):
            raise RuntimeError('Native menu recovery values changed. Restart Resolve before continuing.')
        entries = data['entries']
        self._code_page_write(entries, use_original=True)
        if not self.k.VirtualFreeEx(self.s.handle, self.page, 0, 0x8000):
            raise ctypes.WinError(ctypes.get_last_error())
        self.recovery.unlink(missing_ok=True)
        self.page = None
        self.redirected = False
