"""Bounded administrator handoff. The broker never writes Resolve resources."""
from pathlib import Path
import json,sys,uuid,time,subprocess,ctypes,traceback,logging
from theme_transaction import atomic_bytes
TIMEOUT=90

def paths(folder,nonce):
    base=Path(folder)/'Themes/Operations';base.mkdir(exist_ok=True)
    return base/(nonce+'.request.json'),base/(nonce+'.result.json'),base/(nonce+'.phase.json'),base/(nonce+'.log')

def write_json(path,data):atomic_bytes(path,(json.dumps(data)+'\n').encode())

def read_json(path,timeout=.5):
    """Mandatory control data: tolerate a short Windows sharing/read race."""
    deadline=time.monotonic()+timeout
    while True:
        try:
            data=json.loads(Path(path).read_text())
            if not isinstance(data,dict):raise ValueError('Invalid theme control file.')
            return data
        except (PermissionError,FileNotFoundError,json.JSONDecodeError):
            if time.monotonic()>=deadline:raise
            time.sleep(.01)

def poll_json(path):
    """Nonblocking IPC poll; a locked/replacing file is not an operation error."""
    try:return read_json(path,timeout=0)
    except (PermissionError,FileNotFoundError,json.JSONDecodeError):return None

def guard_request(folder,nonce,action):
    request,_,_,_=paths(folder,nonce)
    if not request.exists():raise RuntimeError('The theme request was cancelled or has expired.')
    data=read_json(request)
    if data.get('action')!=action or data.get('cancelled') or time.time()>=data['expires']:
        raise RuntimeError('The theme request was cancelled or timed out. Check the installed skin status before retrying.')

def cancel_request(folder,nonce):
    request,_,_,_=paths(folder,nonce)
    if request.exists():
        data=read_json(request);data['cancelled']=True;write_json(request,data)

def cancel_quietly(folder,nonce):
    # Request expiry remains enforced by every worker guard even when Windows
    # temporarily prevents writing the cancellation flag. Preserve the real
    # operation error and continue to stop the owned broker on timeout.
    try:cancel_request(folder,nonce)
    except (OSError,ValueError):logging.exception('Could not record theme cancellation; worker guards remain active')

def phase(folder,nonce,message):
    try:
        _,_,status,_=paths(folder,nonce);write_json(status,{'message':message})
    except OSError:
        # Progress is advisory. Its sharing/antivirus/ACL failure must never
        # cancel a verified Apply/Restore transaction or replace its result.
        logging.warning('Theme progress update unavailable',exc_info=True)

def wait_for_broker(folder,nonce,process,progress,timeout):
    request,result,status,_=paths(folder,nonce);deadline=time.monotonic()+timeout;last=None;exit_deadline=None
    while True:
        # An authoritative result wins even if progress cannot be read.
        data=poll_json(result)
        if data is not None:
            if not data['ok']:raise RuntimeError(data['message'])
            return data['message']
        update=poll_json(status)
        message=update.get('message') if update else None
        if message and message!=last:progress(message);last=message
        if process.poll() is not None:
            # Give the terminal result a finite read grace after process exit.
            # A briefly locked final JSON must not turn success into failure.
            if exit_deadline is None:exit_deadline=min(deadline,time.monotonic()+1)
            if time.monotonic()>=exit_deadline:
                raise RuntimeError('The administrator helper exited without a result that could be read. See Themes/Operations for its log. Check the installed skin status before retrying.')
        if time.monotonic()>=deadline:
            cancel_quietly(folder,nonce)
            process.terminate()
            try:process.wait(timeout=2)
            except subprocess.TimeoutExpired:process.kill()
            raise RuntimeError('Theme operation timed out at: '+str(last or 'starting the helper')+'. The request is cancelled; reopen Themes to check the installed skin status before retrying. See Themes/Operations for its log.')
        time.sleep(.05)

def run_elevated(folder,action,progress=lambda message:None,timeout=TIMEOUT):
    if action not in ('apply','restore','probe'):raise ValueError('Unknown administrator action.')
    folder=Path(folder).resolve();nonce=uuid.uuid4().hex;request,result,status,log=paths(folder,nonce)
    write_json(request,{'action':action,'expires':time.time()+timeout,'cancelled':False})
    phase(folder,nonce,'Waiting for Windows administrator approval…')
    executable=Path(sys.executable).with_name('pythonw.exe')
    if not executable.exists():executable=Path(sys.executable)
    command=[str(executable),str(folder/'theme_elevation.py'),'--broker',str(folder),action,nonce]
    try:
        with log.open('w',encoding='utf-8') as output:
            process=subprocess.Popen(command,cwd=folder,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),close_fds=True)
            return wait_for_broker(folder,nonce,process,progress,timeout)
    except Exception:
        cancel_quietly(folder,nonce);raise

def run_direct(folder,action,progress=lambda message:None,timeout=TIMEOUT,worker_script=None):
    """Even an already elevated writer runs in a bounded, owned child process."""
    if action not in ('apply','restore','probe'):raise ValueError('Unknown theme action.')
    folder=Path(folder).resolve();nonce=uuid.uuid4().hex;request,result,status,log=paths(folder,nonce)
    write_json(request,{'action':action,'expires':time.time()+timeout,'cancelled':False})
    phase(folder,nonce,'Starting the isolated theme worker…')
    executable=Path(sys.executable).with_name('pythonw.exe')
    if not executable.exists():executable=Path(sys.executable)
    command=[str(executable),str(worker_script or folder/'resolve_theme.py'),'--theme-worker',action,nonce]
    try:
        with log.open('w',encoding='utf-8') as output:
            process=subprocess.Popen(command,cwd=folder,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),close_fds=True)
            return wait_for_broker(folder,nonce,process,progress,timeout)
    except Exception:
        cancel_quietly(folder,nonce);raise

def broker(folder,action,nonce):
    """ShellExecute runs in a fresh COM STA process, never in the Tk worker."""
    from ctypes import wintypes as w
    folder=Path(folder).resolve();_,result,_,_=paths(folder,nonce)
    ole=ctypes.WinDLL('ole32');ole.CoInitializeEx.argtypes=[ctypes.c_void_p,w.DWORD];ole.CoInitializeEx.restype=ctypes.c_long
    initialized=False;handle=None;kernel=None
    try:
        guard_request(folder,nonce,action)
        hr=ole.CoInitializeEx(None,2)
        if hr<0:raise RuntimeError('Could not initialize the Windows administrator handoff.')
        initialized=True
        class Info(ctypes.Structure):
            _fields_=[('cbSize',w.DWORD),('fMask',w.ULONG),('hwnd',w.HWND),('lpVerb',w.LPCWSTR),('lpFile',w.LPCWSTR),('lpParameters',w.LPCWSTR),('lpDirectory',w.LPCWSTR),('nShow',ctypes.c_int),('hInstApp',w.HINSTANCE),('lpIDList',ctypes.c_void_p),('lpClass',w.LPCWSTR),('hkeyClass',w.HKEY),('dwHotKey',w.DWORD),('hIcon',w.HANDLE),('hProcess',w.HANDLE)]
        executable=Path(sys.executable).with_name('pythonw.exe')
        if not executable.exists():executable=Path(sys.executable)
        info=Info();info.cbSize=ctypes.sizeof(info);info.fMask=0x40|0x100|0x400;info.lpVerb='runas';info.lpFile=str(executable)
        info.lpParameters=subprocess.list2cmdline([str(folder/'resolve_theme.py'),'--theme-worker',action,nonce]);info.lpDirectory=str(folder);info.nShow=0
        shell=ctypes.WinDLL('shell32',use_last_error=True);shell.ShellExecuteExW.argtypes=[ctypes.POINTER(Info)];shell.ShellExecuteExW.restype=w.BOOL
        if not shell.ShellExecuteExW(ctypes.byref(info)):
            code=ctypes.get_last_error()
            if code==1223:raise RuntimeError('Windows administrator approval was cancelled. The skin was not changed by this request.')
            raise RuntimeError('Windows could not start the administrator helper (error 0x'+format(code & 0xffffffff,'08X')+'). No theme operation was launched. Restart Veil from its normal shortcut and retry; see Themes/Operations for the log.')
        handle=info.hProcess
        if not handle:raise RuntimeError('Windows did not return a handle for the administrator helper.')
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];kernel.WaitForSingleObject.restype=w.DWORD
        kernel.CloseHandle.argtypes=[w.HANDLE];kernel.CloseHandle.restype=w.BOOL
        phase(folder,nonce,'Administrator access granted; waiting for the theme operation…')
        while True:
            guard_request(folder,nonce,action)
            outcome=kernel.WaitForSingleObject(handle,100)
            if outcome==0:break
            if outcome!=258:raise RuntimeError('Windows could not monitor the administrator helper.')
        if not result.exists():raise RuntimeError('The administrator helper exited without a result. Check the operation log.')
    except Exception as exc:
        traceback.print_exc();cancel_quietly(folder,nonce)
        if not result.exists():write_json(result,{'ok':False,'message':str(exc)})
    finally:
        if handle and kernel:kernel.CloseHandle(handle)
        if initialized:ole.CoUninitialize()

if __name__=='__main__':
    import re
    if len(sys.argv)!=5 or sys.argv[1]!='--broker' or sys.argv[3] not in ('apply','restore','probe') or not re.fullmatch('[0-9a-f]{32}',sys.argv[4]):raise SystemExit(2)
    if Path(sys.argv[2]).resolve()!=Path(__file__).resolve().parent:raise SystemExit(2)
    broker(sys.argv[2],sys.argv[3],sys.argv[4])
