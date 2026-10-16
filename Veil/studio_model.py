"""Palette library and app preferences. This module never accesses Resolve."""
import json
import re
from pathlib import Path
from palette_core import LABELS, DISPLAY_ORDER, shade, atomic_json, builtin_palettes, load_user_palettes, validate_palette
from palette_names import decode, encode, validate_names

APPEARANCES=('Dark','Light')

def system_appearance():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
            return 'Light' if winreg.QueryValueEx(key,'AppsUseLightTheme')[0] else 'Dark'
    except (ImportError,OSError):
        return 'Dark'

def fingerprint(colors,names):
    return (tuple(tuple(pair) for pair in validate_palette(colors)),tuple(validate_names(names)))

class PaletteLibrary:
    def __init__(self,folder):
        self.folder=Path(folder)
        self.path=self.folder/'saved_palettes.json'
        self.users=load_user_palettes(self.path)
        self.names={}
        if self.path.exists():
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if data['schema']==2:
                self.names={name:validate_names(value.get('display_names',list(LABELS)))
                            for name,value in data['palettes'].items()}
        self.palettes={**builtin_palettes(),**self.users}

    def save(self,name,colors,names):
        name=name.strip()
        if not 1<=len(name)<=60 or name in builtin_palettes():
            raise ValueError('Use a unique name of 1–60 characters. Built-in names are reserved.')
        colors=validate_palette(colors)
        names=validate_names(names)
        users={**self.users,name:colors}
        aliases={**self.names,name:names}
        atomic_json(self.path,dict(schema=2,palettes={n:dict(colors=c,display_names=aliases.get(n,list(LABELS)))
                    for n,c in users.items()}))
        self.users,self.names=users,aliases
        self.palettes={**builtin_palettes(),**users}
        return name

    def read_import(self,path):
        path=Path(path)
        if path.suffix.lower()=='.hex':
            entries=[];aliases=[];palette_name=None
            for line_number,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
                value=line.strip()
                if not value:continue
                if value.startswith(';'):
                    if value.casefold().startswith('; palette:'):
                        if palette_name is not None:raise ValueError('Use only one palette-name header.')
                        palette_name=value.split(':',1)[1].strip()
                        if not 1<=len(palette_name)<=60 or any(ord(c)<32 for c in palette_name):
                            raise ValueError(f'Line {line_number}: use a palette name of 1–60 visible characters.')
                    continue
                parts=value.split('|',1);color=parts[0].strip()
                if not re.fullmatch(r'#?[0-9A-Fa-f]{6}',color):
                    raise ValueError(f'Line {line_number}: use RRGGBB or RRGGBB | Color name, with an optional # before the code.')
                alias=parts[1].strip() if len(parts)==2 else f'Slot {len(entries)+1}'
                if not alias:raise ValueError(f'Line {line_number}: add a color name after |.')
                entries.append('#'+color.lstrip('#').upper());aliases.append(alias)
            if len(entries)!=16:
                raise ValueError(f'A .hex palette needs exactly 16 colors; found {len(entries)}.')
            by_slot={label:[shade(color),color] for label,color in zip(DISPLAY_ORDER,entries)}
            names={label:alias for label,alias in zip(DISPLAY_ORDER,aliases)}
            name=palette_name or path.stem.replace('_',' ').replace('-',' ').strip()[:60] or 'Imported palette'
            return name,validate_palette([by_slot[label] for label in LABELS]),validate_names([names[label] for label in LABELS])
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        colors,names=decode(data)
        name=data.get('name','Imported palette')
        name=name.strip() if isinstance(name,str) else 'Imported palette'
        return name[:60] or 'Imported palette',colors,names

    def delete(self,name):
        if name in builtin_palettes():
            raise ValueError('Built-in palettes cannot be deleted.')
        if name not in self.users:
            raise ValueError('This saved palette no longer exists.')
        users={n:colors for n,colors in self.users.items() if n!=name}
        aliases={n:names for n,names in self.names.items() if n!=name}
        atomic_json(self.path,dict(schema=2,palettes={n:dict(colors=colors,display_names=aliases.get(n,list(LABELS)))
                    for n,colors in users.items()}))
        self.users,self.names=users,aliases
        self.palettes={**builtin_palettes(),**users}

    def rename(self,old,new):
        new=new.strip()
        if not 1<=len(new)<=60:raise ValueError('Enter a name of 1–60 characters.')
        if any(ord(c)<32 for c in new):raise ValueError('Use visible characters in the name.')
        if old not in self.palettes:raise ValueError('Select an existing palette.')
        if new==old:return old
        if any(n.casefold()==new.casefold() for n in self.palettes if n!=old):
            raise ValueError('That name is already used. Choose another.')
        if old in builtin_palettes():return self.save(new,self.palettes[old],self.names.get(old,list(LABELS)))
        users={new if n==old else n:colors for n,colors in self.users.items()}
        aliases={new if n==old else n:names for n,names in self.names.items()}
        atomic_json(self.path,dict(schema=2,palettes={n:dict(colors=c,display_names=aliases.get(n,list(LABELS)))
                    for n,c in users.items()}))
        self.users,self.names=users,aliases;self.palettes={**builtin_palettes(),**users}
        return new

    def export(self,path,name,colors,names):
        path=Path(path)
        if path.suffix.lower()=='.hex':
            colors=validate_palette(colors)
            names=validate_names(names)
            name=name.strip()
            if not 1<=len(name)<=60 or any(ord(c)<32 for c in name):raise ValueError('Use a palette name of 1–60 visible characters.')
            # Named HEX keeps the same base endpoint/order as plain HEX and
            # attaches each display alias directly to its RGB value.
            text=f'; Veil named HEX\n; Palette: {name}\n\n'+''.join(
                colors[LABELS.index(label)][1].lstrip('#').upper()+' | '+names[LABELS.index(label)]+'\n' for label in DISPLAY_ORDER)
            import os,tempfile
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='\n',dir=path.parent,delete=False) as file:
                    temporary=Path(file.name);file.write(text)
                os.replace(temporary,path);temporary=None
            finally:
                if temporary is not None:temporary.unlink(missing_ok=True)
        else:atomic_json(path,encode(name,colors,names))

def load_preferences(folder):
    path=Path(folder)/'studio-settings.json'
    if not path.exists():return 'Dark'
    data=json.loads(path.read_text(encoding='utf-8'))
    mode=data.get('appearance','Dark')
    if mode=='Follow system':
        mode=system_appearance()
        save_preferences(folder,mode)
    if mode not in APPEARANCES:raise ValueError('Unknown appearance preference.')
    return mode

def save_preferences(folder,mode):
    if mode not in APPEARANCES:raise ValueError('Choose Dark or Light.')
    atomic_json(Path(folder)/'studio-settings.json',dict(schema=1,appearance=mode))
