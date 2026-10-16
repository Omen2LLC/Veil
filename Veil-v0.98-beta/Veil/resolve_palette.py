"""Build-specific Windows backend for the 16-entry palette table."""
import ctypes
import ctypes.wintypes as w
import hashlib
import json
import struct
from pathlib import Path
from palette_core import (STOCK,RGB_OFFSETS,atomic_json,compatible_partial,
                          encode_palette,palette_from_blob,validate_palette)

class PROCESSENTRY32W(ctypes.Structure):
    _fields_=[('dwSize',w.DWORD),('cntUsage',w.DWORD),('th32ProcessID',w.DWORD),
              ('th32DefaultHeapID',ctypes.c_size_t),('th32ModuleID',w.DWORD),
              ('cntThreads',w.DWORD),('th32ParentProcessID',w.DWORD),
              ('pcPriClassBase',w.LONG),('dwFlags',w.DWORD),('szExeFile',w.WCHAR*260)]

class MODULEENTRY32W(ctypes.Structure):
    _fields_=[('dwSize',w.DWORD),('th32ModuleID',w.DWORD),('th32ProcessID',w.DWORD),
              ('GlblcntUsage',w.DWORD),('ProccntUsage',w.DWORD),
              ('modBaseAddr',ctypes.c_void_p),('modBaseSize',w.DWORD),('hModule',w.HMODULE),
              ('szModule',w.WCHAR*256),('szExePath',w.WCHAR*260)]

def kernel():
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    specs={
        'CreateToolhelp32Snapshot':([w.DWORD,w.DWORD],w.HANDLE),
        'Process32FirstW':([w.HANDLE,ctypes.POINTER(PROCESSENTRY32W)],w.BOOL),
        'Process32NextW':([w.HANDLE,ctypes.POINTER(PROCESSENTRY32W)],w.BOOL),
        'Module32FirstW':([w.HANDLE,ctypes.POINTER(MODULEENTRY32W)],w.BOOL),
        'Module32NextW':([w.HANDLE,ctypes.POINTER(MODULEENTRY32W)],w.BOOL),
        'OpenProcess':([w.DWORD,w.BOOL,w.DWORD],w.HANDLE),
        'ReadProcessMemory':([w.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)],w.BOOL),
        'WriteProcessMemory':([w.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)],w.BOOL),
        'GetProcessTimes':([w.HANDLE]+[ctypes.POINTER(w.FILETIME)]*4,w.BOOL),
        'GetExitCodeProcess':([w.HANDLE,ctypes.POINTER(w.DWORD)],w.BOOL),
        'WaitForSingleObject':([w.HANDLE,w.DWORD],w.DWORD),
        'CloseHandle':([w.HANDLE],w.BOOL),
        'CreateMutexW':([ctypes.c_void_p,w.BOOL,w.LPCWSTR],w.HANDLE),
    }
    for name,(args,ret) in specs.items():
        fn=getattr(k,name);fn.argtypes=args;fn.restype=ret
    return k

def discover(k):
    snap=k.CreateToolhelp32Snapshot(2,0)
    if snap==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    entry=PROCESSENTRY32W();entry.dwSize=ctypes.sizeof(entry);pids=[]
    try:
        ok=k.Process32FirstW(snap,ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower()=='resolve.exe':pids.append(entry.th32ProcessID)
            ok=k.Process32NextW(snap,ctypes.byref(entry))
    finally:k.CloseHandle(snap)
    # Snapshot entries may outlive exited processes when another app retains handles.
    # Use the same read-only live-process check as the theme shutdown guard.
    from theme_transaction import process_is_running
    pids=[pid for pid in pids if process_is_running(k,pid)]
    if not pids:raise RuntimeError('Open Resolve and a timeline first, then Connect.')
    if len(pids)!=1:raise RuntimeError('Multiple live Resolve processes were found (PIDs: '+', '.join(map(str,pids))+'). Close extra sessions or leftover background Resolve processes, then Connect again.')
    pid=pids[0];snap=k.CreateToolhelp32Snapshot(0x18,pid)
    if snap==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    entry=MODULEENTRY32W();entry.dwSize=ctypes.sizeof(entry)
    try:
        ok=k.Module32FirstW(snap,ctypes.byref(entry))
        while ok:
            if entry.szModule.lower()=='resolve.exe':return pid,entry.modBaseAddr,entry.szExePath
            ok=k.Module32NextW(snap,ctypes.byref(entry))
    finally:k.CloseHandle(snap)
    raise RuntimeError('Could not locate the Resolve module.')

def file_version(path):
    v=ctypes.WinDLL('version',use_last_error=True)
    v.GetFileVersionInfoSizeW.argtypes=[w.LPCWSTR,ctypes.POINTER(w.DWORD)]
    v.GetFileVersionInfoSizeW.restype=w.DWORD
    v.GetFileVersionInfoW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,ctypes.c_void_p]
    v.GetFileVersionInfoW.restype=w.BOOL
    v.VerQueryValueW.argtypes=[ctypes.c_void_p,w.LPCWSTR,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(w.UINT)]
    v.VerQueryValueW.restype=w.BOOL
    unused=w.DWORD();size=v.GetFileVersionInfoSizeW(path,ctypes.byref(unused))
    if not size:raise RuntimeError('Unable to verify Resolve file version.')
    buf=ctypes.create_string_buffer(size)
    if not v.GetFileVersionInfoW(path,0,size,buf):raise ctypes.WinError(ctypes.get_last_error())
    ptr=ctypes.c_void_p();length=w.UINT()
    if not v.VerQueryValueW(buf,'\\',ctypes.byref(ptr),ctypes.byref(length)) or length.value<16:
        raise RuntimeError('Unable to verify Resolve version fields.')
    signature,_,ms,ls=struct.unpack('<IIII',ctypes.string_at(ptr,16))
    if signature!=0xFEEF04BD:raise RuntimeError('Invalid version signature.')
    return '.'.join(map(str,[ms>>16,ms&65535,ls>>16,ls&65535]))

class UnsupportedResolveVersion(RuntimeError):
    """The app may run, but its native palette writer is not verified for this build."""
    def __init__(self,detected,supported):
        self.detected=detected;self.supported=supported
        super().__init__(
            f'DaVinci Resolve {detected} detected. Palette editing and export remain available; '
            f'Apply is disabled because this build has no verified native profile. '
            f'Verified build: {supported}. No changes made.')

def require_supported_version(detected,signature):
    """Fail before opening a writable process handle for an unverified build."""
    supported=signature['version']
    if detected!=supported:raise UnsupportedResolveVersion(detected,supported)

class PaletteSession:
    def __init__(self,folder,writable=True):
        self.folder=Path(folder);self.signature=json.loads((self.folder/'build_signature.json').read_text())
        self.profiles={self.signature['version']:self.signature}
        additional=self.folder/'compatibility_profiles.json'
        if additional.is_file():
            for version,profile in json.loads(additional.read_text(encoding='utf-8')).items():
                if profile.get('native_verified') is True and profile.get('version')==version:
                    self.profiles[version]=profile
        self.recovery=self.folder/'session_recovery.json'
        self.k=kernel();self.handle=None;self.writable=writable
        self.original=None;self.expected=None;self.recovered=False

    def connect(self):
        if self.handle:raise RuntimeError('Already connected. Close this session before reconnecting.')
        self.pid,self.base,path=discover(self.k)
        self.version=file_version(path)
        profiles=getattr(self,'profiles',{self.signature['version']:self.signature})
        if self.version not in profiles:
            raise UnsupportedResolveVersion(self.version,', '.join(sorted(profiles)))
        self.signature=profiles[self.version]
        require_supported_version(self.version,self.signature)
        expected_hash=self.signature.get('executable_sha256')
        if expected_hash:
            with Path(path).open('rb') as executable:
                if hashlib.file_digest(executable,'sha256').hexdigest()!=expected_hash:
                    raise RuntimeError('Resolve executable hash differs from the verified profile. No changes made.')
        self.handle=self.k.OpenProcess(0x1010|(0x28 if self.writable else 0),False,self.pid)
        if not self.handle:
            raise RuntimeError('Windows denied access to Resolve. Run this app locally, using the same Windows account and privilege level as Resolve.')
        try:
            times=[w.FILETIME() for _ in range(4)]
            if not self.k.GetProcessTimes(self.handle,*(ctypes.byref(x) for x in times)):
                raise ctypes.WinError(ctypes.get_last_error())
            self.started=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime
            sig=self.signature
            if hashlib.sha256(self.read(self.base+sig['function_rva'],sig['length'])).hexdigest()!=sig['sha256']:
                raise RuntimeError('Resolve code does not match the verified build. No changes made.')
            self.slot=self.base+sig['table_slot_rva']
            self.pointer=struct.unpack('<Q',self.read(self.slot,8))[0]
            ref,size,alloc,pad,offset=struct.unpack('<iiIIq',self.read(self.pointer,24))
            if ref!=1 or size!=16 or not 24<=offset<=128:
                raise RuntimeError('Palette is not ready or its layout changed. Open a timeline and reconnect.')
            self.offset=offset;self.address=self.pointer+offset
            current=self.read(self.address,512)
            current_palette=palette_from_blob(current)
            if current_palette==validate_palette(STOCK):
                self.original=current
            else:
                journal=json.loads(self.recovery.read_text()) if self.recovery.exists() else {}
                if journal.get('identity')!=self.identity():
                    raise RuntimeError('The active palette is not stock and has no matching recovery record. Close other palette tools and restart Resolve.')
                original=bytes.fromhex(journal['original']);previous=bytes.fromhex(journal['previous']);target=bytes.fromhex(journal['target'])
                if palette_from_blob(original)!=validate_palette(STOCK) or not compatible_partial(current,previous,target):
                    raise RuntimeError('Recovery values do not match the running palette. Restart Resolve before reconnecting.')
                self.original=original;self.recovered=True
            self.expected=current
            return current_palette
        except Exception:
            self.close();raise

    def identity(self):
        return dict(pid=self.pid,started=self.started,base=self.base,pointer=self.pointer,address=self.address,build=self.signature['sha256'])

    def read(self,address,count):
        buf=ctypes.create_string_buffer(count);n=ctypes.c_size_t()
        if not self.k.ReadProcessMemory(self.handle,address,buf,count,ctypes.byref(n)) or n.value!=count:
            raise RuntimeError('Could not read Resolve memory. It may have closed or restarted.')
        return buf.raw

    def write(self,address,data):
        if not self.writable:raise RuntimeError('This connection is read-only.')
        data=bytes(data);buf=ctypes.create_string_buffer(data);n=ctypes.c_size_t()
        if not self.k.WriteProcessMemory(self.handle,address,buf,len(data),ctypes.byref(n)) or n.value!=len(data):
            raise RuntimeError('Windows denied or interrupted the palette write.')
        if self.read(address,len(data))!=data:raise RuntimeError('Palette write did not verify.')

    def alive(self):
        if not self.handle:return False
        code=w.DWORD()
        return bool(self.k.GetExitCodeProcess(self.handle,ctypes.byref(code))) and code.value==259

    @property
    def dirty(self):return self.original is not None and self.expected!=self.original

    def check(self):
        if not self.alive():raise RuntimeError('Resolve closed. Reconnect after opening it again.')
        if self.read(self.slot,8)!=struct.pack('<Q',self.pointer):
            raise RuntimeError('Resolve replaced the color table. Restart Resolve before reconnecting.')
        ref,size,alloc,pad,offset=struct.unpack('<iiIIq',self.read(self.pointer,24))
        if (ref,size,offset)!=(1,16,self.offset):raise RuntimeError('Palette ownership or layout changed. No further writes are safe.')
        if self.read(self.address,512)!=self.expected:
            raise RuntimeError('Another action changed the palette. Restart Resolve before reconnecting.')

    def apply(self,palette):
        target=encode_palette(self.original,palette)
        self._transition(target)

    def restore(self):
        self._transition(self.original)

    def _transition(self,target):
        self.check()
        previous=self.expected
        if previous==target:return
        # Persist a recovery record BEFORE the first write. Disk failure aborts the change.
        atomic_json(self.recovery,dict(identity=self.identity(),original=self.original.hex(),previous=previous.hex(),target=target.hex()))
        try:
            for off in RGB_OFFSETS:
                if previous[off:off+6]!=target[off:off+6]:self.write(self.address+off,target[off:off+6])
            if self.read(self.address,512)!=target:raise RuntimeError('Full palette verification failed.')
            self.expected=target
        except Exception as error:
            try:
                if self.read(self.slot,8)!=struct.pack('<Q',self.pointer):raise RuntimeError('Palette allocation changed.')
                for off in RGB_OFFSETS:self.write(self.address+off,previous[off:off+6])
                if self.read(self.address,512)!=previous:raise RuntimeError('Rollback did not verify.')
                self.expected=previous
                atomic_json(self.recovery,dict(identity=self.identity(),original=self.original.hex(),previous=previous.hex(),target=previous.hex()))
            except Exception as rollback:
                raise RuntimeError(f'Apply failed and restoration could not be verified. Restart Resolve. Details: {error}; {rollback}') from error
            raise RuntimeError(f'Apply failed; previous palette restored. {error}') from error

    def close(self):
        if self.handle:self.k.CloseHandle(self.handle);self.handle=None
