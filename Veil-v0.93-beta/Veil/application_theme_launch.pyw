"""Manual desktop launch entry point. Never invoke from restricted diagnostics."""
from pathlib import Path
import ctypes
import sys
import traceback


def main():
    from application_theme import launch_theme, preflight_theme
    folder = Path(__file__).resolve().parent
    if sys.argv[1:] == ['--preflight']:
        print(preflight_theme(folder))
        return
    if sys.argv[1:]:
        raise SystemExit('Unknown launch arguments.')
    try:
        launch_theme(folder)
    except Exception as exc:
        traceback.print_exc()
        from ctypes import wintypes as w
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.MessageBoxW.argtypes = [w.HWND, w.LPCWSTR, w.LPCWSTR, w.UINT]
        user.MessageBoxW.restype = ctypes.c_int
        user.MessageBoxW(None, str(exc), 'Veil · Cherry Blossom', 0x10)


if __name__ == '__main__':
    main()
