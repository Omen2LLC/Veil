"""Batch existing gradient pixels into one Tk image per palette swatch."""
import struct,zlib,tkinter as tk
from functools import lru_cache
from studio_controls import rounded_png

def bind_size(widget,draw):
    last=[None]
    def changed(event):
        size=(event.width,event.height)
        if size==last[0]:return
        last[0]=size;draw(event)
    widget.bind('<Configure>',changed)

@lru_cache(maxsize=96)
def collection_png(width,height,pairs,scale):
    p=lambda n:int(round(n*scale))
    width=max(2,width);height=max(2,height)
    rows=[bytearray(width*4) for _ in range(height)]
    pw=(width-p(12))/8;ph=p(19);cw=max(2,int(pw-p(3)))
    for index,(left,right) in enumerate(pairs):
        image=rounded_png(cw,ph,left,right,int(ph/2));offset=8;compressed=[]
        while offset<len(image):
            size=struct.unpack('>I',image[offset:offset+4])[0];kind=image[offset+4:offset+8]
            if kind==b'IDAT':compressed.append(image[offset+8:offset+8+size])
            offset+=size+12
        raw=zlib.decompress(b''.join(compressed));stride=cw*4+1
        row,col=divmod(index,8);x=round(p(7)+col*pw);y=p(9)+row*p(27)
        for iy in range(ph):
            if 0<=y+iy<height and 0<=x<width:
                count=min(cw,width-x)*4
                rows[y+iy][x*4:x*4+count]=raw[iy*stride+1:iy*stride+1+count]
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row for row in rows),1))+chunk(b'IEND',b'')

def collection_image(width,height,pairs,scale):
    return tk.PhotoImage(data=collection_png(int(width),int(height),tuple(tuple(p) for p in pairs),scale))
