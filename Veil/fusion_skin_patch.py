"""Cherry Blossom: allowlisted appearance assignments, no asset/layout changes."""
from zipfile import ZipFile, ZIP_DEFLATED
import re

PALETTE={'#E6CED5','#DDB0BC','#D9A0B0','#D9829B','#D46986'}
MAPPING={
    'OctopusGray':'raised','OctopusGray40':'raised','JaguarGray':'panel',
    'NewtGray':'panel','PenguinGray':'panel','OrcaGray':'viewer','OrcaGray40':'viewer',
    'TabButtonGray':'selected','TabButtonGray40':'selected','ThunderstormGray':'hover',
    'ThunderstormGray40':'hover','DropShipGray':'selected','PoseidonGray':'viewer',
    'DolphinGray':'raised','SealGray50':'raised','StarfishGray':'raised',
    'JellyFishGray':'border','JellyFishGray40':'border','JellyFishGray70':'border','PlanktonGray':'border',
    'NautilusGray':'panel'}
RGB=re.compile(rb'(?m)^([A-Za-z]\w*)([ \t]*=[ \t]*\{[ \t]*)(\d+)([ \t]*,[ \t]*)(\d+)([ \t]*,[ \t]*)(\d+)([ \t]*(?:,[ \t]*\d+)?[ \t]*\})')

def _close(blob,start):
    """Balance a value, ignoring Lua strings/comments (no geometry parsing)."""
    depth=0;quote=None;i=start
    while i<len(blob):
        c=blob[i:i+1]
        if quote:
            if c==b'\\':i+=2;continue
            if c==quote:quote=None
        elif c in (b'"',b"'"):quote=c
        elif blob[i:i+2]==b'--':
            end=blob.find(b'\n',i);i=len(blob) if end<0 else end;continue
        elif c==b'{':depth+=1
        elif c==b'}':
            depth-=1
            if depth==0:return i+1
        i+=1
    raise RuntimeError('Unbalanced skin value.')

def _set(blob,name,value,edits,indent=None):
    prefix=rb'[ \t]*' if indent is None else b'\t'*indent
    pattern=re.compile(rb'(?m)^('+prefix+name.encode()+rb'[ \t]*=[ \t]*)')
    hits=list(pattern.finditer(blob))
    for m in reversed(hits):
        start=m.end()
        if blob[start:start+1]==b'{':end=_close(blob,start)
        else:
            symbol=re.match(rb'[A-Za-z]\w*',blob[start:])
            if not symbol:raise RuntimeError('Unsupported appearance expression: '+name)
            end=start+symbol.end()
        if blob[start:end]!=value:
            blob=blob[:start]+value+blob[end:];edits.append(name)
    return blob

def _category(blob,name,depth,fn):
    pattern=re.compile(rb'(?m)^'+b'\t'*depth+name.encode()+rb'[ \t]*=[ \t]*(?:Category[ \t]+)?\{')
    m=pattern.search(blob)
    if not m:return blob
    start=m.end()-1;end=_close(blob,start)
    return blob[:start]+fn(blob[start:end])+blob[end:]

def transform(payload,tokens):
    if any(tokens[k] not in PALETTE for k in ('background','panel','raised','border','viewer','hover','selected','accent')):
        raise ValueError('Cherry Blossom surface colors must come from the supplied hex file.')
    edits=[]
    def rgb(token):return [int(tokens[token][i:i+2],16) for i in (1,3,5)]
    def nested(token):return ('{ { '+', '.join(map(str,rgb(token)))+' } }').encode()
    def replace(m):
        name=m[1].decode()
        if name not in MAPPING:return m[0]
        r,g,b=rgb(MAPPING[name]);out=m[1]+m[2]+str(r).encode()+m[4]+str(g).encode()+m[6]+str(b).encode()+m[8]
        if out!=m[0]:edits.append(name)
        return out
    result=RGB.sub(replace,payload)
    # Reuse existing native black foreground; do not redefine White or semantic
    # rendering/node-category colors that are also used over image content.
    for name,value in {
        'InRangeCol':b'{ TintGray, PenguinGray }','TimeEditCol':b'{ TintGray, PenguinGray }',
        'SelectedTextCol':b'{ TintGray, TabButtonGray }','SelectedItemCol':b'{ TintGray, OctopusGray }',
        'FlowToolCol':b'{ PoseidonGray, TintGray }',
        'FlowSelectedToolCol':b'{ '+nested('selected')[2:-2]+b', TintGray }',
        'FlowActiveToolCol':b'{ '+nested('hover')[2:-2]+b', TintGray }',
        'FlowDisabledToolCol':b'{ DolphinGray, TintGray40 }',
        'ToolbarTextCol':b'TintGrayCol','PVTBButtonSelTextCol':b'TintGrayCol',
        'LabelTextCol':b'TintGrayCol','FlowViewIndicatorCol':b'TintGrayCol',
        'RangeBarCol':nested('border'), 'ActiveViewBorderCol':nested('accent'),
        'ToolbarHotCol':nested('hover'), 'ViewStripActiveBorderCol':nested('accent'),
    }.items():result=_set(result,name,value,edits,indent=0)
    result=_set(result,'ActiveHighlight',nested('accent'),edits)
    # Text foreground assignments only; no labels, fonts or control dimensions.
    keys=set(re.findall(rb'(?m)^\t+([A-Za-z]*TextColor)[ \t]*=',result))
    for key in sorted(keys):
        name=key.decode();fg=b'TintGray40Col' if 'Disabled' in name or 'Inactive' in name else b'TintGrayCol'
        if name=='SelectedTextColor':
            # System selection expects foreground + background; its native
            # SelectedTextCol definition above preserves that two-color shape.
            result=re.sub(rb'(?m)^(\t+'+key+rb'[ \t]*=[ \t]*)\{[ \t]*\{[^}\r\n]+\}[ \t]*\}',lambda m:m[1]+fg,result)
        else:result=_set(result,name,fg,edits)
    def slider_text(block):
        for key in ('Text','DisabledText','ActiveText','DisabledActiveText'):
            block=_set(block,key,b'TintGray40Col' if 'Disabled' in key else b'TintGrayCol',edits,3)
        return block
    result=_category(result,'TimeSlider',1,slider_text)
    # Only foreground Color arrays in these standard control blocks. Bitmap
    # files and numeric layout data remain byte-identical.
    def foreground(block,indent):return _set(block,'Color',b'{ TintGrayCol, TintGrayCol, TintGrayCol, TintGray40Col }',edits,indent)
    for name,depth in (('Button',3),('Combo',3)):
        result=_category(result,name,depth,lambda b,d=depth:foreground(b,d+1))
    for name,depth in (('CheckBox',3),('RadioButton',3),('Tabs',2)):
        result=_category(result,name,depth,lambda b,d=depth:_set(b,'Color',b'{ { TintGrayCol, TintGrayCol, TintGrayCol, TintGray40Col }, { TintGrayCol, TintGrayCol, TintGrayCol, TintGray40Col } }',edits,d+1))
    # Button contains a 3-row native state matrix; retain its dimensions.
    result=_category(result,'Button',3,lambda b:_set(b,'Color',b'{ { TintGrayCol, TintGrayCol, TintGrayCol, TintGray40Col }, { TintGrayCol, TintGrayCol, TintGrayCol, TintGray40Col }, { TintGrayCol, TintGrayCol, TintGrayCol, TintGray40Col } }',edits,4))
    result=_category(result,'Combo',3,lambda b:_set(b,'FillColor',b'{ PenguinGrayCol, DolphinGrayCol, TabButtonGrayCol, PenguinGrayCol }',edits,4))
    result=_category(result,'MultiButton',2,lambda b:_set(b,'Color',b'{ { TintGrayCol, TintGrayCol, TintGrayCol, TintGray40Col }, { TintGrayCol, TintGrayCol, TintGrayCol, TintGray40Col } }',edits,4))
    # White graph curves would vanish on the light pink controls. Reuse a
    # native dark foreground without changing channel colors or curve data.
    def curve(m):edits.append('CurveColor');return m[1]+b'TintGrayCol'
    result=re.sub(rb'(?m)^(\t+CurveColor[ \t]*=[ \t]*)WhiteCol\b',curve,result)
    # The empty viewer surround is color-only; this does not recolor footage.
    result=_category(result,'Views',1,lambda b:_set(b,'BackgroundColor',nested('viewer'),edits,2))
    # UI effect tiles use literal gradients which override FlatCol. Scope
    # these changes to EffectsLibraryView; never alter effect/image colors.
    def effect_tiles(block):
        block=_set(block,'GradTopColor',nested('panel'),edits,2)
        block=_set(block,'GradBottomColor',nested('raised'),edits,2)
        return _set(block,'HoverBorderColor',b'TintGrayCol',edits,2)
    result=_category(result,'EffectsLibraryView',1,effect_tiles)
    # Step 2: change only the custom-painted Flow canvas background.
    result=_category(result,'Flow',1,lambda b:_set(b,'BackgroundColor',nested('raised'),edits,2))
    return result,edits

def build_candidate(source,destination,tokens):
    changes={}
    with ZipFile(source) as original,ZipFile(destination,'w',ZIP_DEFLATED) as candidate:
        candidate.comment=original.comment
        for info in original.infolist():
            payload=original.read(info.filename)
            if info.filename in ('Fusion.skin','Neutral.skin'):
                payload,edits=transform(payload,tokens);changes[info.filename]=edits
            candidate.writestr(info,payload)
    with ZipFile(source) as original,ZipFile(destination) as candidate:
        if candidate.testzip() is not None or original.namelist()!=candidate.namelist():raise RuntimeError('Invalid theme archive.')
        for name in original.namelist():
            before=original.read(name);after=candidate.read(name)
            expected=transform(before,tokens)[0] if name in ('Fusion.skin','Neutral.skin') else before
            if after!=expected:raise RuntimeError('Unexpected resource change: '+name)
    return changes
