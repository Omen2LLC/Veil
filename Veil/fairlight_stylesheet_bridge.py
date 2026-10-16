"""Read-only validation for the bounded late Fairlight stylesheet experiment."""
from pathlib import Path
import hashlib,struct,zlib,re
EXPECTED_DLL = "b91d58be937ad5a378026e866a0bc6d31e136044e46d8b63872052c0fad7dabc"
EXPECTED_SLOT = "9ad74c21e766ed1d49286f203e115ce171ddad71c6bddab4e63e22d509ad1a07"
SLOT_OFFSET = 24546449
SLOT_SIZE = 8526
RULES = {'UiQFLGridoptionButtonTimeCode:enabled': [('background-color', '#E6CED5'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLGridoptionButtonTimeCode:enabled:hover': [('background-color', '#DDB0BC'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLGridoptionButtonTimeCode:enabled:pressed': [('background-color', '#D9A0B0'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLGridoptionButtonTimeCode:enabled:checked': [('background-color', '#D9829B'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLGridoptionButtonTimeCode:enabled:checked:hover': [('background-color', '#D9A0B0'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLGridoptionButtonTimeCode:enabled:checked:pressed': [('background-color', '#D46986'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLGridoptionButtonBarBeat:enabled': [('background-color', '#E6CED5'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLGridoptionButtonBarBeat:enabled:hover': [('background-color', '#DDB0BC'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLGridoptionButtonBarBeat:enabled:pressed': [('background-color', '#D9A0B0'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLGridoptionButtonBarBeat:enabled:checked': [('background-color', '#D9829B'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLGridoptionButtonBarBeat:enabled:checked:hover': [('background-color', '#D9A0B0'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLGridoptionButtonBarBeat:enabled:checked:pressed': [('background-color', '#D46986'), ('color', 'COLOR_TINT_GRAY')], 'UiQFLTimelineMixerContainer': [('background-color', '#E6CED5')]}

def validate_evidence(folder):
    path=Path(folder)/'Themes/Application/FairlightWidgets.evidence.bin'
    slot=path.read_bytes()
    if len(slot)!=SLOT_SIZE or hashlib.sha256(slot).hexdigest()!=EXPECTED_SLOT:raise RuntimeError('Fairlight source evidence changed.')
    packed,size=struct.unpack_from('>II',slot)
    if packed+4!=len(slot) or not 0<size<1048576:raise RuntimeError('Invalid Fairlight source resource.')
    raw=zlib.decompress(slot[8:])
    if len(raw)!=size:raise RuntimeError('Invalid Fairlight source length.')
    # Native base controls and the two container names must be present in exact reviewed evidence.
    for name in ('UiQFLGridoptionButtonTimeCode','UiQFLGridoptionButtonBarBeat','UiQFLTimerlineSidebar','UiQFLTimelineMixerContainer'):
        if not re.search(re.escape(name).encode()+rb'\s*\{',raw):raise RuntimeError('Missing native Fairlight style.')
    return slot

def validate_installed(folder,exe,file_hash,fresh=False):
    slot=validate_evidence(folder)
    dll=Path(exe).parent/'FairlightPage.dll'
    if file_hash(dll,cache=not fresh)!=EXPECTED_DLL:raise RuntimeError('Fairlight differs from the reviewed build.')
    with dll.open('rb') as stream:
        stream.seek(SLOT_OFFSET)
        if stream.read(SLOT_SIZE)!=slot:raise RuntimeError('Fairlight stylesheet source changed.')
