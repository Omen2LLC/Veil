"""Silent Veil launch routing with compatibility for previous releases."""
import ast
from pathlib import Path
import re
import shutil

def release_version(folder):
    folder=Path(folder)
    if not all((folder/name).is_file() for name in ('veil_app.py','studio_ui.py','studio_version.py','splash-640.png')):return None
    try:
        tree=ast.parse((folder/'studio_version.py').read_text(encoding='utf-8-sig'))
        value=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VERSION' for t in n.targets))
        match=re.fullmatch(r'v(\d+(?:\.\d+)+)(?:-beta(?:-r\d+)?| preview)?',value)
        return tuple(int(part) for part in match[1].split('.')) if match else None
    except (OSError,ValueError,SyntaxError,StopIteration,TypeError):return None

def release_root(folder):
    folder=Path(folder).resolve()
    return folder.parent.parent if folder.name in ('Veil','Omen Studio') and folder.parent.name.startswith(('Veil-v','Omen-Studio-v')) else folder.parent

def newest_release(launcher_folder):
    launcher_folder=Path(launcher_folder).resolve()
    root=release_root(launcher_folder) if launcher_folder.name in ('Veil','Omen Studio') else launcher_folder.parent
    # A pinned launcher is an explicit choice. Do not silently switch it to a
    # numerically newer folder merely because another release was extracted.
    current=root/'Veil-Launcher'/'current-release.txt'
    if current.is_file():
        chosen=Path(current.read_text(encoding='utf-8').strip())
        if release_version(chosen) is not None:
            return chosen
    candidates=[launcher_folder,root/'Veil',root/'Omen Studio']
    current=launcher_folder/'current-release.txt'
    if current.exists():candidates.append(Path(current.read_text(encoding='utf-8').strip()))
    for child in root.iterdir():
        if child.is_dir() and child.name.startswith(('Veil-v','Omen-Studio-v')):
            candidates.extend((child/'Veil',child/'Omen Studio'))
    valid=[(version,folder) for folder in candidates if (version:=release_version(folder)) is not None]
    if not valid:raise RuntimeError('No complete Veil release found. Extract a release beside this launcher.')
    return max(valid,key=lambda item:item[0])[1]

def ensure_launcher(folder):
    folder=Path(folder).resolve();destination=release_root(folder)/'Veil-Launcher'
    destination.mkdir(exist_ok=True)
    # The router is outside numbered releases, so pins do not change on upgrades.
    for name in ('Veil.vbs','launch_silent.cmd','veil_start.py','studio_launcher.py'):
        source=folder/name;target=destination/name
        if source.read_bytes()!=(target.read_bytes() if target.exists() else b''):shutil.copyfile(source,target)
    (destination/'current-release.txt').write_text(str(folder),encoding='utf-8')
    return destination/'Veil.vbs'
