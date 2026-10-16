"""Build-locked default fills for unassigned Resolve timeline clips.

Ordinary audio and video clips use built-in Green and Blue pairs when they have
no explicit color ID. These pairs are separate from the 16-entry table. This
component changes only the RGB operands of the four verified instructions.
"""
import ctypes
import ctypes.wintypes as w
import hashlib
import json
import struct

from palette_core import DISPLAY_ORDER, LABELS, STOCK, atomic_json, validate_palette


RESOLVER_RVA = 0x24A3510
RESOLVER_SIZE = 0x238
RESOLVER_SHA256 = '286132f1b8f73cf421013d0a8d65cd381ce7eaa20cafd4846f21ccf458f8265b'
VIDEO_CALLSITE_RVA = 0x262D94B
VIDEO_CALLSITE = bytes.fromhex('458b8dc0020000450fb6c78bd3488d4df7e8af5be7ff')
VIDEO_VTABLE_ENTRY_RVA = 0x7CB5DE8 + 34 * 8
VIDEO_FUNCTION_RVA = 0x262D620
AUDIO_CALLSITE_RVA = 0x25FEF5F
AUDIO_CALLSITE = bytes.fromhex('8bbec0020000488bcee833ecffff448bcf440fb6c08bd3488d4c2478e89045eaff')
AUDIO_VTABLE_ENTRY_RVA = 0x7CB2DA0 + 34 * 8
AUDIO_FUNCTION_RVA = 0x25FED70
INSTRUCTION_RVAS = (0x24A35BF, 0x24A35CB, 0x24A35F1, 0x24A35F8)
STOCK_INSTRUCTIONS = (bytes.fromhex('ba4d693800'), bytes.fromhex('ba648f4400'),
                      bytes.fromhex('ba81654400'), bytes.fromhex('baa1764300'))
PAGE_SIZE = 4096
GREEN_ID = LABELS.index('Green')
BLUE_ID = LABELS.index('Blue')
assert DISPLAY_ORDER[5] == 'Green' and GREEN_ID == 0
assert DISPLAY_ORDER[8] == 'Blue' and BLUE_ID == 2


def _compatible(current, previous, target):
    """Accept only the recorded operand bytes, including an interrupted write."""
    if not all(len(x) == 5 and x[0] == 0xBA for x in (current, previous, target)):
        return False
    return all(value in (before, after)
               for value, before, after in zip(current[1:], previous[1:], target[1:]))


class CodeProtectionError(RuntimeError):
    """The target code page may no longer have its original protection."""


class DefaultTimelineFills:
    def __init__(self, session):
        self.s = session
        self.k = session.k
        self.recovery = session.folder / 'timeline_default_recovery.json'
        self.original = STOCK_INSTRUCTIONS
        self.expected = STOCK_INSTRUCTIONS
        self.recovered = False
        self.failed = False
        self._configure_code_apis()
        self._verify_context()
        current = self._read_entries()
        self._verify_resolver()
        if current != self.original:
            if not self.s.writable:
                raise RuntimeError('An interrupted default-fill change needs recovery. Restart Resolve or connect in normal mode.')
            journal = self._read_journal()
            if not self._valid_journal(journal, current):
                raise RuntimeError('Timeline default fills differ from the verified build and recovery record. Restart Resolve.')
            previous, target = self._journal_entries(journal)
            self._write_entries(self.original, previous, target, allow_partial=True)
            self.recovered = True
        self.check()

    def _configure_code_apis(self):
        self.k.VirtualProtectEx.argtypes = [w.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                                             w.DWORD, ctypes.POINTER(w.DWORD)]
        self.k.VirtualProtectEx.restype = w.BOOL
        self.k.FlushInstructionCache.argtypes = [w.HANDLE, ctypes.c_void_p, ctypes.c_size_t]
        self.k.FlushInstructionCache.restype = w.BOOL

    def _verify_context(self):
        if not self.s.alive():
            raise RuntimeError('Resolve closed. Reconnect after opening it again.')
        if self.s.signature['version'] != '21.1.0.14':
            raise RuntimeError('Unsupported Resolve build for timeline default fills.')
        if self.s.read(self.s.base + VIDEO_CALLSITE_RVA, len(VIDEO_CALLSITE)) != VIDEO_CALLSITE:
            raise RuntimeError('Ordinary video-clip color callsite changed. Restart Resolve.')
        function = struct.unpack('<Q', self.s.read(self.s.base + VIDEO_VTABLE_ENTRY_RVA, 8))[0]
        if function != self.s.base + VIDEO_FUNCTION_RVA:
            raise RuntimeError('Ordinary video-clip class layout changed. Restart Resolve.')
        if self.s.read(self.s.base + AUDIO_CALLSITE_RVA, len(AUDIO_CALLSITE)) != AUDIO_CALLSITE:
            raise RuntimeError('Ordinary audio-clip color callsite changed. Restart Resolve.')
        function = struct.unpack('<Q', self.s.read(self.s.base + AUDIO_VTABLE_ENTRY_RVA, 8))[0]
        if function != self.s.base + AUDIO_FUNCTION_RVA:
            raise RuntimeError('Ordinary audio-clip class layout changed. Restart Resolve.')

    def _read_entries(self):
        return tuple(self.s.read(self.s.base + rva, 5) for rva in INSTRUCTION_RVAS)

    def _verify_resolver(self):
        blob = bytearray(self.s.read(self.s.base + RESOLVER_RVA, RESOLVER_SIZE))
        for rva, stock in zip(INSTRUCTION_RVAS, self.original):
            offset = rva - RESOLVER_RVA
            if blob[offset] != 0xBA:
                raise RuntimeError('Timeline default instruction opcode changed. Restart Resolve.')
            blob[offset + 1:offset + 5] = stock[1:]
        if hashlib.sha256(blob).hexdigest() != RESOLVER_SHA256:
            raise RuntimeError('Timeline default resolver differs from the verified build. Restart Resolve.')

    def _read_journal(self):
        try:
            return json.loads(self.recovery.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise RuntimeError('Timeline default recovery record is missing or unreadable. Restart Resolve.') from exc

    @staticmethod
    def _journal_entries(journal):
        return (tuple(bytes.fromhex(x) for x in journal['previous']),
                tuple(bytes.fromhex(x) for x in journal['target']))

    def _valid_journal(self, journal, current):
        try:
            if journal.get('schema') != 1 or journal.get('identity') != self.s.identity():
                return False
            if tuple(bytes.fromhex(x) for x in journal['original']) != self.original:
                return False
            previous, target = self._journal_entries(journal)
            if len(previous) != 4 or len(target) != 4:
                return False
            if any(entry[4] != 0 for entry in (*previous, *target)):
                return False
            return all(_compatible(now, before, after)
                       for now, before, after in zip(current, previous, target))
        except (KeyError, TypeError, ValueError, IndexError):
            return False

    def _journal(self, previous, target):
        return dict(schema=1, identity=self.s.identity(),
                    original=[x.hex() for x in self.original],
                    previous=[x.hex() for x in previous],
                    target=[x.hex() for x in target])

    @property
    def dirty(self):
        return self.expected != self.original

    def check(self):
        if self.failed:
            raise CodeProtectionError('Resolve code-page protection needs a Resolve restart.')
        self._verify_context()
        self._verify_resolver()
        if self._read_entries() != self.expected:
            raise RuntimeError('Timeline default fill changed outside Veil. Restart Resolve.')

    def plan(self, palette):
        colors = validate_palette(palette)
        shades = colors[GREEN_ID] + colors[BLUE_ID]
        return tuple(b'\xBA' + struct.pack('<I', int(color[1:], 16)) for color in shades)

    def _write_entries(self, target, previous, attempted, allow_partial=False):
        if not self.s.writable:
            raise RuntimeError('This connection is read-only.')
        self._verify_context()
        self._verify_resolver()
        current = self._read_entries()
        allowed = (_compatible if allow_partial else lambda now, before, after: now == before)
        if not all(allowed(now, before, after)
                   for now, before, after in zip(current, previous, attempted)):
            raise RuntimeError('Timeline default source changed during update. Restart Resolve.')
        page = (self.s.base + RESOLVER_RVA) & ~(PAGE_SIZE - 1)
        if any((self.s.base + rva) & ~(PAGE_SIZE - 1) != page for rva in INSTRUCTION_RVAS):
            raise RuntimeError('Timeline default instructions no longer share the verified code page.')
        old_protection = w.DWORD()
        if not self.k.VirtualProtectEx(self.s.handle, page, PAGE_SIZE, 0x40,
                                       ctypes.byref(old_protection)):
            raise ctypes.WinError(ctypes.get_last_error())
        write_error = None
        flush_error = None
        protection_error = None
        try:
            for rva, new, before, after in zip(INSTRUCTION_RVAS, target, previous, attempted):
                now = self.s.read(self.s.base + rva, 5)
                if not allowed(now, before, after):
                    raise RuntimeError('Timeline default source changed while writing. Restart Resolve.')
                if now != new:
                    self.s.write(self.s.base + rva + 1, new[1:])
            if self._read_entries() != target:
                raise RuntimeError('Timeline default source write did not verify.')
        except Exception as exc:
            write_error = exc
        finally:
            if not self.k.FlushInstructionCache(self.s.handle, page, PAGE_SIZE):
                flush_error = ctypes.WinError(ctypes.get_last_error())
            restored = w.DWORD()
            if not self.k.VirtualProtectEx(self.s.handle, page, PAGE_SIZE,
                                           old_protection.value, ctypes.byref(restored)):
                protection_error = ctypes.WinError(ctypes.get_last_error())
        if protection_error:
            self.failed = True
            raise CodeProtectionError('Resolve code-page protection could not be restored. Restart Resolve.') from protection_error
        if flush_error:
            raise RuntimeError('Resolve instruction cache could not be refreshed. Restart Resolve.') from flush_error
        if write_error:
            raise write_error
        self._verify_resolver()

    def transition(self, target):
        target = tuple(target)
        if len(target) != 4 or any(len(x) != 5 or x[0] != 0xBA or x[4] != 0 for x in target):
            raise ValueError('Timeline default colors must be four RGB instructions.')
        self.check()
        previous = self.expected
        if target == previous:
            return
        # A matching recovery record exists before any instruction is changed.
        atomic_json(self.recovery, self._journal(previous, target))
        try:
            self._write_entries(target, previous, target)
            self.expected = target
        except Exception as error:
            if isinstance(error, CodeProtectionError):
                raise
            try:
                self._write_entries(previous, previous, target, allow_partial=True)
                self.expected = previous
                atomic_json(self.recovery, self._journal(previous, previous))
            except Exception as rollback:
                raise RuntimeError(f'Timeline default-fill rollback could not be verified. Restart Resolve. {error}; {rollback}') from error
            raise RuntimeError(f'Timeline default-fill change failed; previous colors restored. {error}') from error

    def apply(self, palette):
        self.transition(self.plan(palette))

    def restore(self):
        self.transition(self.original)
