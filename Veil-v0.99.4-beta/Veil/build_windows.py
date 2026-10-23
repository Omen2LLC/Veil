"""Build the standalone Windows beta after both edition evidence gates pass.

Install requirements-build.txt, refresh release_gate.py --record for VERSION,
then run this script from a 64-bit Windows Python with Tkinter.
"""
import os
from pathlib import Path

from release_gate import check_record
from studio_version import VERSION

ROOT = Path(__file__).resolve().parent
ASSETS = (
    'fonts', 'Palettes', 'Themes', 'compatibility', 'compatibility_profiles.json',
    'dot_signatures.json', 'thumbnail_signatures.json', 'saved_palettes.json',
    'studio_version.py', 'resolve_api_probe.py', 'README.md', 'SUPPORTED_RESOLVE.md',
    'veil-icon.ico', 'veil-icon.png', 'veil-startup.vaf', 'Veil.vbs',
    'launch_silent.cmd', 'veil_start.py', 'studio_launcher.py',
    'veil-splash-logo-640.png', 'veil-splash-logo-800.png', 'veil-splash-logo-960.png',
    'splash-640.png', 'splash-800.png', 'splash-960.png',
)


def main():
    import PyInstaller.__main__
    check_record(VERSION, ROOT)
    os.chdir(ROOT)
    arguments = [str(ROOT / 'veil_app.py'), '--name', 'Veil', '--windowed', '--onedir',
                 '--contents-directory', '.', '--icon', str(ROOT / 'veil-icon.ico'),
                 '--distpath', str(ROOT / 'dist' / f'Veil-{VERSION}'),
                 '--workpath', str(ROOT / '.build-pyinstaller'),
                 '--specpath', str(ROOT / '.build-pyinstaller'), '--noconfirm']
    for asset in ASSETS:
        destination = asset if (ROOT / asset).is_dir() else '.'
        arguments.extend(('--add-data', f'{ROOT / asset};{destination}'))
    PyInstaller.__main__.run(arguments)


if __name__ == '__main__':
    main()
