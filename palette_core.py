"""Palette validation and serialization. No Resolve access in this module."""
import json
import re
import struct
from pathlib import Path

LABELS = ['Green', 'Teal', 'Blue', 'Purple', 'Pink', 'Tan', 'Brown', 'Apricot',
          'Beige', 'Chocolate', 'Lime', 'Navy', 'Olive', 'Orange', 'Violet', 'Yellow']
DISPLAY_ORDER = ['Orange', 'Apricot', 'Yellow', 'Lime', 'Olive', 'Green', 'Teal', 'Navy',
                 'Blue', 'Purple', 'Violet', 'Pink', 'Tan', 'Beige', 'Brown', 'Chocolate']
STOCK = [('#38694D','#448F64'),('#046666','#009899'),('#446581','#4376A1'),
         ('#816786','#9973A0'),('#B87894','#E98CB5'),('#9F967C','#B9B097'),
         ('#6C4C0B','#996600'),('#E7890C','#FFA833'),('#AB8C6C','#C6A077'),
         ('#734A33','#8C5A3F'),('#8CAE12','#9FC615'),('#134B64','#156284'),
         ('#487318','#5E9920'),('#D16100','#EB6E00'),('#B04675','#D0578D'),
         ('#CC9A1C','#E2A91C')]
RGB_OFFSETS = tuple(i*16+6 for i in range(32))

def hex_color(value):
    if not isinstance(value,str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}',value):
        raise ValueError('Use a color in #RRGGBB format, such as #00FFFF.')
    return value.upper()

def validate_palette(palette):
    if not isinstance(palette,(list,tuple)) or len(palette)!=16:
        raise ValueError('A palette must contain exactly 16 labels.')
    result=[]
    for pair in palette:
        if not isinstance(pair,(list,tuple)) or len(pair)!=2:
            raise ValueError('Each label must have exactly two shades.')
        result.append([hex_color(x) for x in pair])
    return result

def shade(hexvalue,factor=.76):
    v=hex_color(hexvalue)
    rgb=[round(int(v[i:i+2],16)*factor) for i in (1,3,5)]
    return '#'+''.join(f'{c:02X}' for c in rgb)

def builtin_palettes():
    vivid=['#31C48D','#11C5C6','#4798FF','#A378FF','#FF7CC7','#D4BC80',
           '#AC723D','#FFBD66','#E5CBB4','#B17664','#B9DC45','#4F67BA',
           '#859C3E','#FF8438','#EC5C95','#F4CE49']
    soft=['#86B59A','#77B6B3','#89ADD0','#B19DD0','#D9A2C2','#C4B793',
          '#A78A6C','#DDB990','#D5C5AF','#AC8C83','#BAC78A','#7F91B2',
          '#9FA880','#D5A184','#BE8FA7','#D8C68A']
    return {'Resolve Original':validate_palette(STOCK),
            'Vivid':[[shade(c),c] for c in vivid],
            'Soft':[[shade(c),c] for c in soft]}

def validate_blob(blob):
    if not isinstance(blob,bytes) or len(blob)!=512:
        raise ValueError('Unexpected palette byte count.')
    for i in range(32):
        spec,alpha=struct.unpack_from('<iH',blob,i*16)
        if spec!=1 or alpha!=65535:
            raise ValueError('Unexpected internal color representation. Restart Resolve.')

def palette_from_blob(blob):
    validate_blob(blob)
    colors=[]
    for off in RGB_OFFSETS:
        rgb=struct.unpack_from('<HHH',blob,off)
        if any(x%257 for x in rgb):
            raise ValueError('Internal colors are not the verified 8-bit RGB representation.')
        colors.append('#'+''.join(f'{x//257:02X}' for x in rgb))
    return [colors[i:i+2] for i in range(0,32,2)]

def encode_palette(original,palette):
    validate_blob(original)
    palette=validate_palette(palette)
    result=bytearray(original)
    for off,color in zip(RGB_OFFSETS,(x for pair in palette for x in pair)):
        rgb=[int(color[i:i+2],16)*257 for i in (1,3,5)]
        struct.pack_into('<HHH',result,off,*rgb)
    return bytes(result)

def compatible_partial(current,previous,target):
    """Recognize complete per-color writes from an interrupted transaction."""
    if any(len(x)!=512 for x in (current,previous,target)):return False
    masks=set(p for off in RGB_OFFSETS for p in range(off,off+6))
    if any(current[i]!=previous[i] or previous[i]!=target[i] for i in range(512) if i not in masks):
        return False
    return all(current[o:o+6] in (previous[o:o+6],target[o:o+6]) for o in RGB_OFFSETS)

def atomic_json(path,value):
    path=Path(path)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,indent=2),encoding='utf-8')
    temp.replace(path)

def load_user_palettes(path):
    path=Path(path)
    if not path.exists():return {}
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema') not in (1,2) or not isinstance(data.get('palettes'),dict):
        raise ValueError('Unrecognized saved-palette file. It has not been overwritten.')
    result={}
    for name,palette in data['palettes'].items():
        if not isinstance(name,str) or not 1<=len(name.strip())<=60 or name in builtin_palettes():
            raise ValueError('Invalid or reserved saved palette name.')
        result[name]=validate_palette(palette['colors'] if data['schema']==2 else palette)
    return result
