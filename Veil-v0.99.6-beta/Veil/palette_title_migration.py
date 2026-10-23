"""Rename shipped palette titles without discarding edited colors."""
import json
from pathlib import Path
from palette_core import atomic_json

def migrate_titles(path):
    path=Path(path)
    mapping_path=Path(__file__).with_name('palette-title-migrations.json')
    if not path.is_file() or not mapping_path.is_file():return
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema')!=2:return
    palettes=data['palettes'];changed=False
    for old,record in json.loads(mapping_path.read_text()).items():
        new=record['new'];stock=record['stock']
        if old not in palettes:continue
        if new not in palettes or palettes[new]==stock:
            palettes[new]=palettes.pop(old);changed=True
        elif palettes[new]==palettes[old]:
            palettes.pop(old);changed=True
        # A distinct custom destination is preserved alongside the source.
    if changed:
        backup=path.with_name('palette-titles-before-v0.99.6.json')
        if not backup.exists():
            with backup.open('xb') as stream:stream.write(path.read_bytes())
        atomic_json(path,data)
