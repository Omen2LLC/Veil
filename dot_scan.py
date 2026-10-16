import ctypes,struct
from resolve_palette import MODULEENTRY32W

def scan(session):
    k=session.k;pid=session.pid;base=session.base
    snap=k.CreateToolhelp32Snapshot(0x18,pid)
    if snap==ctypes.c_void_p(-1).value:raise RuntimeError('Cannot inspect UI module')
    entry=MODULEENTRY32W();entry.dwSize=ctypes.sizeof(entry);ui=None
    try:
        ok=k.Module32FirstW(snap,ctypes.byref(entry))
        while ok:
            if entry.szModule.lower()=='bmddavui.dll':ui=entry.modBaseAddr
            ok=k.Module32NextW(snap,ctypes.byref(entry))
    finally:k.CloseHandle(snap)
    if not ui:raise RuntimeError('UI module unavailable')
    total=0
    def read(p,n):
        nonlocal total
        total+=n
        if not 0x10000<p<0x7fffffffffff or not 0<n<=4096 or total>4*1024*1024:raise RuntimeError('Dot scan bounds exceeded')
        return session.read(p,n)
    def ptr(p):return struct.unpack('<Q',read(p,8))[0]
    def qstring(p):
        data=ptr(p);raw=read(data,24);ref,size,alloc,pad,offset=struct.unpack('<iiIIq',raw)
        if not 0<=size<=1024 or not 24<=offset<=128:raise ValueError('QString bounds')
        return read(data+offset,size*2).decode('utf-16le') if size else ''
    # Exact exported Instance() body resolves this global; verify before use.
    if read(ui+0x3f930,8)!=bytes.fromhex('488b0509842500c3'):raise ValueError('Instance signature changed')
    manager=ptr(ui+0x297d40);tree=ptr(manager);header=read(tree,32)
    ref,size=struct.unpack_from('<ii',header)
    if not 0<size<20000:raise ValueError('Unexpected map size')
    stack=[struct.unpack_from('<Q',header,16)[0]];seen=set();dots=[]
    while stack:
        node=stack.pop()
        if not node:continue
        if node in seen or len(seen)>=size:raise ValueError('Map changed or invalid tree')
        seen.add(node);raw=read(node,48)
        parent,left,right,key,obj,control=struct.unpack('<6Q',raw)
        stack.extend((left,right));name=qstring(node+24)
        if '/FlagsAndMarkers/ClipColor' in name:
            resource=read(obj,16);data=struct.unpack_from('<Q',resource,8)[0]
            resource_header=read(data,120)
            dot=dict(name=name,node=hex(node),object=hex(obj),data=hex(data),header=resource_header.hex(),images=[])
            # Candidate Qt 5 x64 layout. Validate dimensions and lengths before pixels.
            for slot in (0x10,0x30,0x50):
                platform=struct.unpack_from('<Q',resource_header,slot+24)[0]
                if not platform:continue
                image=dict(slot=hex(slot),platform=hex(platform))
                dot['images'].append(image)
                try:
                    platform_header=read(platform,96)
                    image['platform_header']=platform_header.hex()
                    width,height,depth=struct.unpack_from('<iii',platform_header,8)
                    image.update(width=width,height=height,depth=depth)
                    if not 1<=width<=64 or not 1<=height<=64 or depth!=32:
                        raise ValueError('Unconfirmed platform image layout')
                    image_data=struct.unpack_from('<Q',platform_header,72)[0]
                    image_header=read(image_data,96)
                    image.update(image_data=hex(image_data),image_header=image_header.hex())
                    refs,iw,ih,idepth,nbytes,dpr,colors,pixels,fmt=struct.unpack_from('<iiiiqdQQi',image_header)
                    stride=struct.unpack_from('<q',image_header,56)[0]
                    if (iw,ih,idepth)!=(width,height,depth) or not 0<refs<100000:
                        raise ValueError('Image header does not match platform dimensions')
                    if not width*4<=stride<=width*4+64 or nbytes!=stride*height or nbytes>16384 or fmt not in (4,5,6,17,18):
                        raise ValueError('Unconfirmed pixel format or buffer size')
                    payload=b''.join(read(pixels+i,min(4096,nbytes-i)) for i in range(0,nbytes,4096))
                    if read(platform,96)!=platform_header or read(image_data,96)!=image_header:
                        raise ValueError('Image changed during read')
                    image.update(format=fmt,stride=stride,dpr=dpr,pixels=hex(pixels),pixel_bytes=payload.hex(),validated=True)
                except (OSError,ValueError,struct.error) as exc:
                    image['diagnostic']=str(exc)
            dots.append(dot)
    if ptr(manager)!=tree or read(tree,8)!=header[:8]:raise ValueError('Map changed during inspection')
    result=dict(pid=pid,module=hex(ui),manager=hex(manager),map_size=size,visited=len(seen),read_bytes=total,dots=dots)
    normal_dots=dots
    if read(base+0x248ea12,7)!=bytes.fromhex('488b050fd1f718'):raise ValueError('Composite cache signature mismatch')
    tree=ptr(base+0x1b40bb28);header=read(tree,32)
    ref,size=struct.unpack_from('<ii',header)
    if not 0<=size<=2048:raise ValueError('Composite cache size is unexpected')
    stack=[struct.unpack_from('<Q',header,16)[0]];seen=set();entries=[]
    while stack:
        node=stack.pop()
        if not node:continue
        if node in seen or len(seen)>=size:raise ValueError('Composite tree changed')
        seen.add(node);raw=read(node,48)
        left,right=struct.unpack_from('<QQ',raw,8);stack.extend((left,right))
        name=qstring(node+24)
        entry_result=dict(name=name,node=hex(node),value=raw[32:48].hex())
        entries.append(entry_result)
        obj=struct.unpack_from('<Q',raw,32)[0]
        if '/FlagsAndMarkers/ClipColor' in name and obj:
            resource=read(obj,16);data=struct.unpack_from('<Q',resource,8)[0]
            resource_header=read(data,120)
            dot=dict(name=name,node=hex(node),object=hex(obj),data=hex(data),header=resource_header.hex(),images=[])
            # Candidate Qt 5 x64 layout. Validate dimensions and lengths before pixels.
            for slot in (0x10,0x30,0x50):
                platform=struct.unpack_from('<Q',resource_header,slot+24)[0]
                if not platform:continue
                image=dict(slot=hex(slot),platform=hex(platform))
                dot['images'].append(image)
                try:
                    platform_header=read(platform,96)
                    image['platform_header']=platform_header.hex()
                    width,height,depth=struct.unpack_from('<iii',platform_header,8)
                    image.update(width=width,height=height,depth=depth)
                    if not 1<=width<=64 or not 1<=height<=64 or depth!=32:
                        raise ValueError('Unconfirmed platform image layout')
                    image_data=struct.unpack_from('<Q',platform_header,72)[0]
                    image_header=read(image_data,96)
                    image.update(image_data=hex(image_data),image_header=image_header.hex())
                    refs,iw,ih,idepth,nbytes,dpr,colors,pixels,fmt=struct.unpack_from('<iiiiqdQQi',image_header)
                    stride=struct.unpack_from('<q',image_header,56)[0]
                    if (iw,ih,idepth)!=(width,height,depth) or not 0<refs<100000:
                        raise ValueError('Image header does not match platform dimensions')
                    if not width*4<=stride<=width*4+64 or nbytes!=stride*height or nbytes>16384 or fmt not in (4,5,6,17,18):
                        raise ValueError('Unconfirmed pixel format or buffer size')
                    payload=b''.join(read(pixels+i,min(4096,nbytes-i)) for i in range(0,nbytes,4096))
                    if read(platform,96)!=platform_header or read(image_data,96)!=image_header:
                        raise ValueError('Image changed during read')
                    image.update(format=fmt,stride=stride,dpr=dpr,pixels=hex(pixels),pixel_bytes=payload.hex(),validated=True)
                except (OSError,ValueError,struct.error) as exc:
                    image['diagnostic']=str(exc)
            entry_result.update(dot)
    if read(tree,8)!=header[:8]:raise ValueError('Composite cache changed during read')
    result=dict(pid=pid,map_size=size,visited=len(seen),entries=entries)
    return normal_dots,entries
