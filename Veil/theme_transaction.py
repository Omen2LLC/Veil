"""Guarded first-install test. Manual Resolve close/restart only; no UI activation."""
from pathlib import Path
import os,json,hashlib,uuid,sys,ctypes,time,logging
HERE=Path(__file__).resolve().parent
INSTALL=Path('C:/Program Files/Blackmagic Design/DaVinci Resolve')
class ResolveRunning(RuntimeError):pass

def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def atomic_bytes(target,contents,before_replace=lambda:None,progress=lambda message:None):
    target=Path(target);temporary=None
    try:
        # NamedTemporaryFile can repeatedly retry Access Denied on Windows
        # because os.access does not reliably reflect NTFS write permissions.
        # Exclusive UUID staging fails immediately on a permissions error.
        staged=target.parent/('.omen-theme-'+uuid.uuid4().hex+'.tmp')
        with staged.open('xb') as f:
            temporary=staged
            progress('Writing the staged Fusion skin…')
            f.write(contents);f.flush()
            progress('Flushing the staged Fusion skin to disk…')
            os.fsync(f.fileno())
        before_replace()
        progress('Replacing the verified Fusion skin…')
        # Windows readers may briefly hold JSON/status files without delete
        # sharing. Retry that sharing race with a short, finite deadline.
        deadline=time.monotonic()+.5
        while True:
            try:os.replace(temporary,target);temporary=None;break
            except PermissionError:
                if time.monotonic()>=deadline:raise
                time.sleep(.01)
                before_replace()
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)

class SkinTransaction:
    def __init__(self,target,original,candidate,journal,original_hash,candidate_hash,closed,progress=lambda message:None):
        self.target=Path(target);self.original=Path(original);self.candidate=Path(candidate)
        self.journal=Path(journal);self.original_hash=original_hash;self.candidate_hash=candidate_hash;self.closed=closed;self.progress=progress
    def record(self,state):
        atomic_bytes(self.journal,(json.dumps({'state':state,'target':str(self.target),
            'original_sha256':self.original_hash,'candidate_sha256':self.candidate_hash},indent=2)+'\n').encode())
    def execute(self,action):
        if action not in ('apply','restore'):raise ValueError('Use apply or restore.')
        self.closed()
        # Every run checks the backup. Never capture a modified or unknown file
        # as the original, and never overwrite an unrecognized installation.
        if digest(self.original)!=self.original_hash:raise RuntimeError('Original backup is missing or has changed. Refusing to write.')
        current=digest(self.target)
        if current not in (self.original_hash,self.candidate_hash):raise RuntimeError('Installed skin changed or belongs to another build. Refusing to overwrite it.')
        if action=='apply':
            if digest(self.candidate)!=self.candidate_hash:raise RuntimeError('Candidate changed. Refusing to apply.')
            source,wanted=self.candidate,self.candidate_hash
        else:source,wanted=self.original,self.original_hash
        if current==wanted:self.record('theme-installed' if action=='apply' else 'original-restored');return 'Already '+('applied' if action=='apply' else 'restored')
        self.progress('Recording the prepared theme transaction…')
        self.record(action+'-prepared')
        self.progress('Rechecking that Resolve is closed…')
        self.closed() # Recheck immediately before the file replacement.
        self.progress('Staging the verified skin for installation…')
        atomic_bytes(self.target,source.read_bytes(),self.closed,self.progress)
        self.progress('Verifying the installed skin…')
        if digest(self.target)!=wanted:raise RuntimeError('Post-write verification failed. Keep Resolve closed and restore the original.')
        self.record('theme-installed' if action=='apply' else 'original-restored')
        return 'Theme installed' if action=='apply' else 'Original restored'

def active_resolve_pids():
    sys.path.insert(0,str(HERE))
    from resolve_palette import kernel,PROCESSENTRY32W
    k=kernel();snapshot=k.CreateToolhelp32Snapshot(2,0)
    if snapshot==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    from ctypes import wintypes as w
    k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];k.WaitForSingleObject.restype=w.DWORD
    entry=PROCESSENTRY32W();entry.dwSize=ctypes.sizeof(entry);candidates=[]
    try:
        ok=k.Process32FirstW(snapshot,ctypes.byref(entry))
        while ok:
            if entry.szExeFile.casefold()=='resolve.exe':candidates.append(entry.th32ProcessID)
            ok=k.Process32NextW(snapshot,ctypes.byref(entry))
    finally:k.CloseHandle(snapshot)
    # A snapshot/name match alone is insufficient: the process can exit while
    # the snapshot is being read, or remain listed while handles are retained.
    return [pid for pid in candidates if process_is_running(k,pid)]

def process_is_running(k,pid):
    handle=k.OpenProcess(0x100000,False,pid) # SYNCHRONIZE: observe, never terminate.
    if not handle:
        error=ctypes.get_last_error()
        if error==87:return False # PID already disappeared after the snapshot.
        raise ctypes.WinError(error)
    try:
        result=k.WaitForSingleObject(handle,0)
        if result==0:return False # Signalled process handle means exit completed.
        if result==258:return True
        raise ctypes.WinError(ctypes.get_last_error())
    finally:k.CloseHandle(handle)

def require_resolve_closed():
    pids=active_resolve_pids()
    if pids:
        logging.info('Resolve remains active: %s',pids)
        raise ResolveRunning('DaVinci Resolve is still running or finishing shutdown. Close it completely and wait for it to exit, then try again. Start Resolve manually after installation.')

def wait_for_resolve_closed(progress=lambda message:None,timeout=20):
    deadline=time.monotonic()+timeout;reported=False
    while True:
        pids=active_resolve_pids()
        if not pids:return
        if not reported:
            logging.info('Waiting for Resolve processes to exit: %s',pids)
            progress('Waiting for Resolve to finish closing…');reported=True
        if time.monotonic()>=deadline:
            raise ResolveRunning('Resolve has not finished exiting. Wait for shutdown to complete, then try again. No theme resource was changed by this request.')
        time.sleep(.2)


