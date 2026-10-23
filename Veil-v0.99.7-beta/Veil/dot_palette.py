"""Verified 1x menu images; combined with the existing fill transaction."""
import hashlib,json,struct
from palette_core import LABELS,STOCK,validate_palette,atomic_json
from resolve_palette import PaletteSession as FillSession
from default_fill import DefaultTimelineFills
from dot_scan import scan
from thumbnail_palette import ThumbnailPalette

def recolor(plain,combined,color):
    result=[bytearray(plain),bytearray(combined)]
    rgb=bytes.fromhex(color[1:]);bgr=rgb[::-1]
    # The strongest stock channel gives the original center's shading mask.
    center=plain[544:547];channel=max(range(3),key=lambda i:center[i]);scale=center[channel]
    if not scale:raise RuntimeError('Invalid dot center')
    for i in range(0,len(plain),4):
        if not any(plain[i:i+3]):continue
        if plain[i:i+4]!=combined[i:i+4]:raise RuntimeError('Ring overlaps colored pixels')
        alpha=plain[i+3];shade=plain[i+channel]/scale
        value=bytes(min(alpha,round(c*shade)) for c in bgr)
        for dst in result:dst[i:i+3]=value
    return tuple(bytes(x) for x in result)

class DotPalette:
    def __init__(self,s):
        self.s=s;self.records=[];self.pairs=[]
        sig=json.loads((s.folder/'dot_signatures.json').read_text())
        normal,active=scan(s);lookup={d['name']:d for d in normal+active}
        for label in LABELS:
            name=':/Common/FlagsAndMarkers/ClipColor'+label
            pair=[]
            for key in (name,name+'_:/Common/FlagsAndMarkers/ClipColorActive'):
                if key not in lookup:raise RuntimeError('Open Clip Color, hover a color, close the menu, then Connect again.')
                dot=lookup[key]
                if len(dot.get('images',[]))!=1:raise RuntimeError('Dot display scaling is unsupported; this preview requires 1x images.')
                im=dot['images'][0]
                if not im.get('validated') or (im['width'],im['height'],im['format'],im['stride'],im['dpr'])!=(16,16,6,64,1):raise RuntimeError('Unsupported dot image layout')
                old=bytes.fromhex(im['pixel_bytes'])
                if hashlib.sha256(old).hexdigest()!=sig[key]:raise RuntimeError('Dots are not stock. Close palette tools and restart Resolve before connecting.')
                record=dict(dot=dot,address=int(im['pixels'],16),original=old,expected=old,kind='pixels')
                pair.append(record);self.records.append(record)
                for field,header,offset in (('platform','platform_header',28),('image_data','image_header',68)):
                    old=bytes.fromhex(im[header])[offset:offset+4]
                    self.records.append(dict(dot=dot,address=int(im[field],16)+offset,original=old,expected=old,kind='key'))
            recolor(pair[0]['original'],pair[1]['original'],'#00FFFF')
            self.pairs.append(pair)
        if len({r['address'] for r in self.records})!=len(self.records):raise RuntimeError('Unexpected shared dot storage')
        self.check()

    @property
    def dirty(self):return any(r['expected']!=r['original'] for r in self.records)

    def ownership(self,dot):
        s=self.s;im=dot['images'][0]
        for addr,expected in ((int(dot['node'],16)+32,int(dot['object'],16)),(int(dot['object'],16)+8,int(dot['data'],16))):
            if s.read(addr,8)!=struct.pack('<Q',expected):raise RuntimeError('Dot ownership changed; restart Resolve.')
        if s.read(int(dot['data'],16),120)!=bytes.fromhex(dot['header']):raise RuntimeError('Dot resource changed; restart Resolve.')
        for field,header,offset in (('platform','platform_header',28),('image_data','image_header',68)):
            # QRasterPlatformPixmap is 0x50 bytes in the verified Qt5 build.
            # Bytes after its embedded QImage belong to another allocation.
            size=80 if field=='platform' else 96
            current=bytearray(s.read(int(im[field],16),size));old=bytearray.fromhex(im[header])[:size]
            if field=='image_data':
                # QImageData's atomic reference count changes while Qt paints.
                refs=struct.unpack_from('<i',current)[0]
                if not 1<=refs<100000:raise RuntimeError('Dot image reference count changed unexpectedly; restart Resolve.')
                current[:4]=old[:4]
            current[offset:offset+4]=old[offset:offset+4]
            if current!=old:
                differences=[i for i,(a,b) in enumerate(zip(current,old)) if a!=b]
                raise RuntimeError(f'Dot image changed: {dot["name"]} {field} offsets {differences[:12]}; restart Resolve.')

    def check(self):
        for r in self.records:
            self.ownership(r['dot'])
            if self.s.read(r['address'],len(r['expected']))!=r['expected']:raise RuntimeError('Another action changed menu dots; restart Resolve.')

    def plan(self,palette):
        result={}
        for pair,shades in zip(self.pairs,validate_palette(palette)):
            for r,new in zip(pair,recolor(pair[0]['original'],pair[1]['original'],shades[1])):result[r['address']]=new
        for r in self.records:
            if r['kind']=='key':
                value=struct.unpack('<I',r['expected'])[0]
                if value>=0xffffff00:raise RuntimeError('Image counter exhausted; restart Resolve.')
                result[r['address']]=struct.pack('<I',value+1)
        return result

    def snapshot(self):return {r['address']:r['expected'] for r in self.records}

    def transition(self,target):
        self.check();previous=self.snapshot();attempted=[]
        atomic_json(self.s.folder/'dot_recovery.json',dict(identity=self.s.identity(),records=[dict(address=r['address'],original=r['original'].hex(),previous=r['expected'].hex(),target=target[r['address']].hex()) for r in self.records]))
        try:
            for r in self.records:
                new=target[r['address']]
                if new==r['expected']:continue
                self.ownership(r['dot']);attempted.append(r);self.s.write(r['address'],new);r['expected']=new
        except Exception as error:
            failures=[]
            for r in reversed(attempted):
                try:
                    self.ownership(r['dot']);old=previous[r['address']];new=target[r['address']]
                    current=self.s.read(r['address'],len(old))
                    if any(c not in (a,b) for c,a,b in zip(current,old,new)):raise RuntimeError('Concurrent dot modification')
                    self.s.write(r['address'],old);r['expected']=old
                except Exception as exc:failures.append(str(exc))
            if failures:raise RuntimeError('Dot rollback failed; restart Resolve. '+str(failures)) from error
            raise

    def restore(self):self.transition({r['address']:r['original'] for r in self.records})

class PaletteSession(FillSession):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.dots=None;self.default_fills=None;self.thumbnails=None
    def connect(self):
        try:
            palette=super().connect()
            self.default_fills=DefaultTimelineFills(self)
            self.recovered=self.recovered or self.default_fills.recovered
            self.dots=DotPalette(self)
            self.thumbnails=ThumbnailPalette(self)
            return palette
        except Exception:self.close();raise
    @property
    def dirty(self):
        return (super().dirty or bool(self.dots and self.dots.dirty)
                or bool(self.default_fills and self.default_fills.dirty)
                or bool(self.thumbnails and self.thumbnails.dirty))
    def check(self):
        super().check()
        if self.dots:self.dots.check()
        if self.default_fills:self.default_fills.check()
        if self.thumbnails:self.thumbnails.check()
    def refresh_thumbnails(self):
        return self.thumbnails.refresh() if self.thumbnails else False
    def apply(self,palette):
        palette=validate_palette(palette)
        if palette==validate_palette(STOCK):return self.restore()
        self.check();self.thumbnails.discover()
        before_dots=self.dots.snapshot();before_defaults=self.default_fills.expected
        before_thumbnails=self.thumbnails.snapshot();before_thumbnail_palette=self.thumbnails.palette
        try:
            self.default_fills.apply(palette)
            self.dots.transition(self.dots.plan(palette))
            self.thumbnails.apply(palette)
            super().apply(palette)
        except Exception as error:
            failures=[]
            try:self.thumbnails.transition(before_thumbnails);self.thumbnails.palette=before_thumbnail_palette
            except Exception as exc:failures.append('media-pool dots: '+str(exc))
            try:self.dots.transition(before_dots)
            except Exception as exc:failures.append('dots: '+str(exc))
            try:self.default_fills.transition(before_defaults)
            except Exception as exc:failures.append('default timeline fills: '+str(exc))
            if failures:
                raise RuntimeError('Palette change failed and restoration needs attention. Restart Resolve. '
                                   +str(error)+'; '+'; '.join(failures)) from error
            raise
    def restore(self):
        errors=[]
        # Restore independently so one failed component cannot skip the others.
        if self.default_fills:
            try:self.default_fills.restore()
            except Exception as exc:errors.append('default timeline fills: '+str(exc))
        if self.dots:
            try:self.dots.restore()
            except Exception as exc:errors.append('menu dots: '+str(exc))
        if self.thumbnails:
            try:self.thumbnails.restore()
            except Exception as exc:errors.append('media-pool dots: '+str(exc))
        dots=self.dots;defaults=self.default_fills;thumbnails=self.thumbnails
        self.dots=None;self.default_fills=None;self.thumbnails=None
        try:super().restore()
        except Exception as exc:errors.append('assigned clip colors: '+str(exc))
        finally:self.dots=dots;self.default_fills=defaults;self.thumbnails=thumbnails
        if errors:raise RuntimeError('Restoration incomplete; restart Resolve. '+str(errors))
