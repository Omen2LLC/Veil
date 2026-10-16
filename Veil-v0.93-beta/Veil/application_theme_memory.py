"""Change data in a newly created, suspended child only. Never attach to a running app."""
import ctypes as c,ctypes.wintypes as w,struct,subprocess

class StartupInfo(c.Structure):
    _fields_=[('cb',w.DWORD),('lpReserved',w.LPWSTR),('lpDesktop',w.LPWSTR),('lpTitle',w.LPWSTR),
      ('dwX',w.DWORD),('dwY',w.DWORD),('dwXSize',w.DWORD),('dwYSize',w.DWORD),
      ('dwXCountChars',w.DWORD),('dwYCountChars',w.DWORD),('dwFillAttribute',w.DWORD),
      ('dwFlags',w.DWORD),('wShowWindow',w.WORD),('cbReserved2',w.WORD),('lpReserved2',c.c_void_p),
      ('hStdInput',w.HANDLE),('hStdOutput',w.HANDLE),('hStdError',w.HANDLE)]
class ProcessInfo(c.Structure):
    _fields_=[('hProcess',w.HANDLE),('hThread',w.HANDLE),('pid',w.DWORD),('tid',w.DWORD)]
class BasicInfo(c.Structure):
    _fields_=[('ExitStatus',w.LONG),('PebBaseAddress',c.c_void_p),('AffinityMask',c.c_size_t),
              ('BasePriority',w.LONG),('UniqueProcessId',c.c_size_t),('InheritedFromUniqueProcessId',c.c_size_t)]
class MemoryInfo(c.Structure):
    _fields_=[('BaseAddress',c.c_void_p),('AllocationBase',c.c_void_p),('AllocationProtect',w.DWORD),
              ('PartitionId',w.WORD),('RegionSize',c.c_size_t),('State',w.DWORD),('Protect',w.DWORD),('Type',w.DWORD)]

class SuspendedChild:
    def __init__(self,exe,args=()):
        if c.sizeof(c.c_void_p)!=8:raise RuntimeError('64-bit launcher required.')
        self.k=c.WinDLL('kernel32',use_last_error=True);self.n=c.WinDLL('ntdll')
        specs={
          'CreateProcessW':([w.LPCWSTR,w.LPWSTR,c.c_void_p,c.c_void_p,w.BOOL,w.DWORD,c.c_void_p,w.LPCWSTR,c.POINTER(StartupInfo),c.POINTER(ProcessInfo)],w.BOOL),
          'ReadProcessMemory':([w.HANDLE,c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(c.c_size_t)],w.BOOL),
          'WriteProcessMemory':([w.HANDLE,c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(c.c_size_t)],w.BOOL),
          'VirtualQueryEx':([w.HANDLE,c.c_void_p,c.POINTER(MemoryInfo),c.c_size_t],c.c_size_t),
          'VirtualProtectEx':([w.HANDLE,c.c_void_p,c.c_size_t,w.DWORD,c.POINTER(w.DWORD)],w.BOOL),
          'ResumeThread':([w.HANDLE],w.DWORD),'TerminateProcess':([w.HANDLE,w.UINT],w.BOOL),
          'WaitForSingleObject':([w.HANDLE,w.DWORD],w.DWORD),'CloseHandle':([w.HANDLE],w.BOOL)}
        for name,(args_,ret) in specs.items():
            f=getattr(self.k,name);f.argtypes=args_;f.restype=ret
        self.n.NtQueryInformationProcess.argtypes=[w.HANDLE,w.ULONG,c.c_void_p,w.ULONG,c.POINTER(w.ULONG)]
        self.n.NtQueryInformationProcess.restype=w.LONG
        self.info=ProcessInfo();self.resumed=False;self.created=False;self.closed=False
        si=StartupInfo();si.cb=c.sizeof(si)
        # A GUI application's ordinary window behavior is preserved. No inherited handles.
        command=c.create_unicode_buffer(subprocess.list2cmdline([str(exe),*map(str,args)]))
        from pathlib import Path
        if not self.k.CreateProcessW(str(exe),command,None,None,False,0x4|0x08000000,None,str(Path(exe).parent),c.byref(si),c.byref(self.info)):
            raise c.WinError(c.get_last_error())
        self.created=True

    def read(self,address,size):
        buf=c.create_string_buffer(size);count=c.c_size_t()
        if not self.k.ReadProcessMemory(self.info.hProcess,address,buf,size,c.byref(count)) or count.value!=size:
            raise c.WinError(c.get_last_error())
        return buf.raw

    def image_base(self):
        basic=BasicInfo();returned=w.ULONG()
        status=self.n.NtQueryInformationProcess(self.info.hProcess,0,c.byref(basic),c.sizeof(basic),c.byref(returned))
        if status<0:raise RuntimeError('Cannot query suspended child: NTSTATUS %08x'%(status&0xffffffff))
        if not basic.PebBaseAddress or basic.UniqueProcessId!=self.info.pid:raise RuntimeError('Unexpected process information.')
        # PEB layout is build-dependent: validate the resulting image rather than trusting it.
        base=struct.unpack('<Q',self.read(basic.PebBaseAddress+0x10,8))[0]
        dos=self.read(base,64)
        if dos[:2]!=b'MZ':raise RuntimeError('Image base validation failed.')
        at=struct.unpack_from('<I',dos,0x3c)[0]
        if not 0x40<=at<=0x10000 or self.read(base+at,6)!=b'PE\0\0d\x86':raise RuntimeError('Child is not a validated x64 PE image.')
        return base

    def patch_data(self,rva,original,proposed,checkpoint=lambda phase,child:None):
        if self.resumed:raise RuntimeError('Only a suspended child can be patched.')
        if len(original)!=len(proposed) or not original or len(original)>65536:raise ValueError('Invalid resource slot size.')
        base=self.image_base();address=base+rva
        self.verify_data_range(base,rva,len(original))
        if self.read(address,len(original))!=original:raise RuntimeError('Mapped original resource differs; refusing to write.')
        regions=[];cursor=address;end=address+len(original)
        while cursor<end:
            mi=MemoryInfo()
            if self.k.VirtualQueryEx(self.info.hProcess,cursor,c.byref(mi),c.sizeof(mi))!=c.sizeof(mi):raise c.WinError(c.get_last_error())
            if mi.AllocationBase!=base or mi.State!=0x1000 or mi.Type!=0x1000000 or mi.Protect not in (2,4,8):
                raise RuntimeError('Resource is not committed, non-executable image data.')
            extent=min(end,mi.BaseAddress+mi.RegionSize)-cursor
            if extent<=0:raise RuntimeError('Invalid mapped region.')
            regions.append((cursor,extent));cursor+=extent
        changed=[]
        try:
            for start,size in regions:
                old=w.DWORD()
                if not self.k.VirtualProtectEx(self.info.hProcess,start,size,8,c.byref(old)):raise c.WinError(c.get_last_error())
                changed.append((start,size,old.value))
            checkpoint('before_write',self)
            self.write(address,proposed)
            checkpoint('after_write',self)
            if self.read(address,len(proposed))!=proposed:raise RuntimeError('Resource readback failed.')
        finally:
            for start,size,protection in reversed(changed):
                scratch=w.DWORD()
                if not self.k.VirtualProtectEx(self.info.hProcess,start,size,protection,c.byref(scratch)):
                    raise c.WinError(c.get_last_error())
        if self.read(address,len(proposed))!=proposed:raise RuntimeError('Resource changed after restoring protection.')
        for start,_,protection in changed:
            mi=MemoryInfo()
            if self.k.VirtualQueryEx(self.info.hProcess,start,c.byref(mi),c.sizeof(mi))!=c.sizeof(mi) or mi.Protect!=protection:
                raise RuntimeError('Original resource memory protection did not verify.')
        return {'pid':self.info.pid,'image_base':hex(base),'resource_address':hex(address),'bytes_verified':len(proposed)}

    def verify_data_range(self,base,rva,size):
        # Some images initially map code read-only before runtime initialization.
        # Page protection alone does not prove a range is resource data. Check
        # the mapped PE section characteristics as well, before any write.
        if not isinstance(rva,int) or rva<0:raise ValueError('Invalid resource RVA.')
        dos=self.read(base,64);nt=struct.unpack_from('<I',dos,60)[0]
        header=self.read(base+nt,24)
        count=struct.unpack_from('<H',header,6)[0];opt_size=struct.unpack_from('<H',header,20)[0]
        if not 1<=count<=96 or not 112<=opt_size<=4096:raise RuntimeError('Invalid mapped image section table.')
        optional=self.read(base+nt+24,opt_size)
        if optional[:2]!=b'\x0b\x02':raise RuntimeError('Mapped image is not PE32+.')
        image_size=struct.unpack_from('<I',optional,56)[0]
        sections=self.read(base+nt+24+opt_size,count*40);matches=[]
        for at in range(0,len(sections),40):
            virtual_size,start=struct.unpack_from('<II',sections,at+8)
            flags=struct.unpack_from('<I',sections,at+36)[0]
            if start<=rva and rva+size<=min(image_size,start+virtual_size):matches.append(flags)
        if len(matches)!=1 or matches[0]&0x20000000 or not matches[0]&0x40000000:
            raise RuntimeError('Resource range is not mapped non-executable image data.')

    def write(self,address,data):
        count=c.c_size_t();buffer=c.create_string_buffer(data)
        if not self.k.WriteProcessMemory(self.info.hProcess,address,buffer,len(data),c.byref(count)) or count.value!=len(data):
            raise c.WinError(c.get_last_error())

    def resume(self):
        prior=self.k.ResumeThread(self.info.hThread)
        if prior==0:self.resumed=True;raise RuntimeError('Unexpected already-running thread; left running.')
        if prior!=1:raise RuntimeError('Unable to resume validated suspended child.')
        self.resumed=True

    def dispose(self):
        if self.closed:return
        if self.created and not self.resumed:
            # This handle belongs only to our fresh child, whose primary thread has never run.
            state=self.k.WaitForSingleObject(self.info.hProcess,0)
            if state==258:
                if not self.k.TerminateProcess(self.info.hProcess,1):raise c.WinError(c.get_last_error())
                if self.k.WaitForSingleObject(self.info.hProcess,5000)!=0:raise RuntimeError('Suspended-child cleanup did not finish.')
            elif state!=0:raise RuntimeError('Cannot observe suspended-child exit state.')
        for handle in (self.info.hThread,self.info.hProcess):
            if handle:self.k.CloseHandle(handle)
        self.closed=True


class NativeContext:
    """Observe startup and retain exact ownership identity without activating UI."""
    def __init__(self):
        if c.sizeof(c.c_void_p)!=8:raise RuntimeError('64-bit Veil is required.')
        self.k=c.WinDLL('kernel32',use_last_error=True)
        self.a=c.WinDLL('advapi32',use_last_error=True)
        self.u=c.WinDLL('user32',use_last_error=True)
        specs={
            'OpenProcess':([w.DWORD,w.BOOL,w.DWORD],w.HANDLE),
            'GetProcessTimes':([w.HANDLE]+[c.POINTER(w.FILETIME)]*4,w.BOOL),
            'GetExitCodeProcess':([w.HANDLE,c.POINTER(w.DWORD)],w.BOOL),
            'QueryFullProcessImageNameW':([w.HANDLE,w.DWORD,w.LPWSTR,c.POINTER(w.DWORD)],w.BOOL),
            'GetProcessId':([w.HANDLE],w.DWORD),
            'ProcessIdToSessionId':([w.DWORD,c.POINTER(w.DWORD)],w.BOOL),
            'WaitForSingleObject':([w.HANDLE,w.DWORD],w.DWORD),
            'TerminateProcess':([w.HANDLE,w.UINT],w.BOOL),
            'CreateMutexW':([c.c_void_p,w.BOOL,w.LPCWSTR],w.HANDLE),
            'ReleaseMutex':([w.HANDLE],w.BOOL),
            'CloseHandle':([w.HANDLE],w.BOOL)}
        for name,(arguments,result) in specs.items():
            api=getattr(self.k,name);api.argtypes=arguments;api.restype=result
        self.a.GetUserNameW.argtypes=[w.LPWSTR,c.POINTER(w.DWORD)]
        self.a.GetUserNameW.restype=w.BOOL
        self.enum_callback=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)
        self.u.EnumWindows.argtypes=[self.enum_callback,w.LPARAM];self.u.EnumWindows.restype=w.BOOL
        self.u.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)];self.u.GetWindowThreadProcessId.restype=w.DWORD
        self.u.IsWindowVisible.argtypes=[w.HWND];self.u.IsWindowVisible.restype=w.BOOL
        self.u.GetWindowTextW.argtypes=[w.HWND,w.LPWSTR,c.c_int];self.u.GetWindowTextW.restype=c.c_int
        self.u.GetClassNameW.argtypes=[w.HWND,w.LPWSTR,c.c_int];self.u.GetClassNameW.restype=c.c_int
        self.u.GetWindowRect.argtypes=[w.HWND,c.POINTER(w.RECT)];self.u.GetWindowRect.restype=w.BOOL
        self.u.GetWindowLongPtrW.argtypes=[w.HWND,c.c_int];self.u.GetWindowLongPtrW.restype=c.c_ssize_t

    def username(self):
        size=w.DWORD(1024);buffer=c.create_unicode_buffer(size.value)
        if not self.a.GetUserNameW(buffer,c.byref(size)):raise c.WinError(c.get_last_error())
        return buffer.value

    def lock(self):
        import contextlib
        @contextlib.contextmanager
        def held():
            c.set_last_error(0)
            mutex=self.k.CreateMutexW(None,True,'Local\\OmenStudioCherryBlossomApplicationStartup')
            error=c.get_last_error()
            if not mutex:raise c.WinError(error)
            if error==183:
                self.k.CloseHandle(mutex)
                raise RuntimeError('Another Veil instance is preparing Resolve.')
            try:yield
            finally:
                self.k.ReleaseMutex(mutex);self.k.CloseHandle(mutex)
        return held()

    def identity(self,handle,pid,account):
        if self.k.GetProcessId(handle)!=pid:raise RuntimeError('Owned process identity differs.')
        times=[w.FILETIME() for _ in range(4)]
        if not self.k.GetProcessTimes(handle,*(c.byref(value) for value in times)):raise c.WinError(c.get_last_error())
        started=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime
        size=w.DWORD(32768);path=c.create_unicode_buffer(size.value)
        if not self.k.QueryFullProcessImageNameW(handle,0,path,c.byref(size)):raise c.WinError(c.get_last_error())
        session=w.DWORD()
        if not self.k.ProcessIdToSessionId(pid,c.byref(session)):raise c.WinError(c.get_last_error())
        return {'pid':pid,'started':started,'exe':path.value,'account':account,'windows_session':session.value}

    def visible_windows(self,pid):
        windows=[]
        @self.enum_callback
        def inspect(hwnd,_):
            owner=w.DWORD()
            self.u.GetWindowThreadProcessId(hwnd,c.byref(owner))
            if owner.value!=pid or not self.u.IsWindowVisible(hwnd):return True
            title=c.create_unicode_buffer(1024);classname=c.create_unicode_buffer(256);rect=w.RECT()
            self.u.GetWindowTextW(hwnd,title,len(title));self.u.GetClassNameW(hwnd,classname,len(classname))
            has_rect=self.u.GetWindowRect(hwnd,c.byref(rect))
            # A metadata failure must not turn a visible window into an absent
            # one: explicit failed-start recovery refuses any visible window.
            windows.append({'title':title.value,'class':classname.value,
                'width':rect.right-rect.left if has_rect else 0,
                'height':rect.bottom-rect.top if has_rect else 0,
                'style':self.u.GetWindowLongPtrW(hwnd,-16)&0xffffffff,
                'extended_style':self.u.GetWindowLongPtrW(hwnd,-20)&0xffffffff})
            return True
        if not self.u.EnumWindows(inspect,0):raise c.WinError(c.get_last_error())
        return windows

    def observe(self,handle,pid):
        code=w.DWORD()
        if not self.k.GetExitCodeProcess(handle,c.byref(code)):raise c.WinError(c.get_last_error())
        wait=self.k.WaitForSingleObject(handle,0)
        if wait==0:return {'alive':False,'exit_code':code.value,'visible_windows':[],'main_window':None}
        if wait!=258:raise RuntimeError('Cannot observe the owned Resolve process.')
        windows=self.visible_windows(pid)
        # A splash alone is not success. Require a normal visible captioned Qt
        # window. A detected window confirms startup, never appearance coverage
        # or playback. This monitor does not send messages to or activate it.
        main=next((window for window in windows
                   if 'qt' in window['class'].casefold()
                   and window['style']&0x00c00000==0x00c00000
                   and not window['extended_style']&0x80
                   and window['width']>=400 and window['height']>=250
                   and 'davinci resolve' in window['title'].casefold()),None)
        return {'alive':True,'visible_windows':windows,'main_window':main}

    @staticmethod
    def _same_identity(actual,expected):
        from pathlib import Path
        def norm(path):return str(Path(path.removeprefix('\\\\?\\')).resolve()).casefold()
        return (actual['pid']==expected.get('pid') and actual['started']==expected.get('started')
                and actual['windows_session']==expected.get('windows_session')
                and norm(actual['exe'])==norm(expected.get('exe','')))

    def inspect_session(self,expected):
        pid=expected.get('pid')
        if not isinstance(pid,int) or not 0<pid<0xffffffff:raise RuntimeError('Invalid recorded process identity.')
        handle=self.k.OpenProcess(0x100000|0x1000,False,pid) # Observe only.
        if not handle:
            error=c.get_last_error()
            if error in (6,87):return {'matches':False,'alive':False,'visible_windows':[]}
            raise c.WinError(error)
        try:
            actual=self.identity(handle,pid,self.username())
            if not self._same_identity(actual,expected):return {'matches':False,'alive':False,'visible_windows':[]}
            result=self.observe(handle,pid);result['matches']=True;return result
        finally:self.k.CloseHandle(handle)

    def cleanup(self,expected):
        """Only reached after explicit no-project confirmation and timeout checks."""
        pid=expected['pid'];handle=self.k.OpenProcess(0x100000|0x1000|1,False,pid)
        if not handle:raise c.WinError(c.get_last_error())
        try:
            actual=self.identity(handle,pid,self.username())
            if not self._same_identity(actual,expected):raise RuntimeError('Failed-launch process identity changed. No process was cleared.')
            observed=self.observe(handle,pid)
            if not observed['alive'] or observed['visible_windows']:raise RuntimeError('Resolve exited or has a visible window. No process was cleared.')
            # Repeat the observation immediately before the explicit recovery
            # action. Never use this path for an observed normal startup.
            if self.visible_windows(pid):raise RuntimeError('Resolve now has a visible window. Close it normally.')
            if not self.k.TerminateProcess(handle,1):raise c.WinError(c.get_last_error())
            if self.k.WaitForSingleObject(handle,5000)!=0:raise RuntimeError('Failed-start recovery has not finished. Do not launch another Resolve instance yet.')
        finally:self.k.CloseHandle(handle)
