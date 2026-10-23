"""Palette provenance presentation; never uploads or changes user data."""
import hashlib,json
from pathlib import Path
from functools import lru_cache

@lru_cache(maxsize=1)
def catalog():
    try:
        return json.loads(Path(__file__).with_name('native-palette-catalog.json').read_text())['palettes']
    except (OSError,ValueError,KeyError,TypeError):return {}

def origin(name,colors,names):
    value=dict(colors=colors,display_names=list(names))
    digest=hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    record=catalog().get(name,{})
    return 'Native' if record.get('distribution')=='veil-native' and record.get('sha256')==digest else 'Custom'
