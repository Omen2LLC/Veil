"""Display aliases are palette metadata; native slot identifiers never change."""
import unicodedata
from palette_core import LABELS,validate_palette

def validate_names(names):
    if not isinstance(names,list) or len(names)!=16:raise ValueError('Provide 16 display names.')
    result=[]
    for value in names:
        if not isinstance(value,str):raise ValueError('Names must be text.')
        value=unicodedata.normalize('NFC',value.strip())
        if not 1<=len(value)<=40 or any(unicodedata.category(c).startswith('C') for c in value):
            raise ValueError('Each name needs 1–40 visible characters.')
        result.append(value)
    if len({x.casefold() for x in result})!=16:raise ValueError('Give each slot a distinct name.')
    return result

def decode(data):
    if data.get('schema') not in (1,2) or data.get('labels')!=LABELS:raise ValueError('Incompatible palette file.')
    return validate_palette(data['colors']),validate_names(data.get('display_names',list(LABELS)))

def encode(name,colors,names):
    return dict(schema=2,name=name,labels=list(LABELS),colors=validate_palette(colors),display_names=validate_names(names))
