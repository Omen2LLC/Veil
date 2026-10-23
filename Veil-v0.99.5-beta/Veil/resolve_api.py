"""Optional, bounded public API diagnostics. Does not launch or modify Resolve."""
import json
import os
from pathlib import Path
import re
import subprocess

PREFIX = 'VEIL_RESOLVE_API:'
PAGES = {'media', 'cut', 'edit', 'fusion', 'color', 'fairlight', 'deliver', 'photo'}


def parse_report(output):
    if len(output) > 65536:
        raise ValueError('Oversized API response')
    lines = [line[len(PREFIX):] for line in output.splitlines() if line.startswith(PREFIX)]
    if len(lines) != 1:
        raise ValueError('Missing API response')
    data = json.loads(lines[0])
    if data == {'status': 'unavailable'}:
        return data
    if not isinstance(data, dict) or data.get('status') != 'connected':
        raise ValueError('Invalid API response')
    if not isinstance(data.get('version'), str) or not re.fullmatch(r'\d{1,6}(\.\d{1,6}){3}', data['version']):
        raise ValueError('Invalid API version')
    if any(type(data.get(key)) is not bool for key in ('project_open', 'timeline_open')):
        raise ValueError('Invalid API state')
    return {'status': 'connected', 'version': data['version'],
            'page': data.get('page') if data.get('page') in PAGES else None,
            'project_open': data['project_open'], 'timeline_open': data['timeline_open']}


def check_connection(discover_process=None, run=None):
    if discover_process is None:
        from resolve_palette import discover, kernel
        discover_process = lambda: discover(kernel())
    try:
        pid, _, executable = discover_process()
    except Exception:
        return {'status': 'not_running'}
    runtime = Path(executable).parent / 'ResolvePython' / 'ResolvePython.exe'
    if not runtime.is_file():
        return {'status': 'sdk_missing'}
    environment = {key: value for key, value in os.environ.items()
                   if key.upper() not in {'PYTHONHOME', 'PYTHONPATH'}}
    try:
        result = (run or subprocess.run)(
            [str(runtime), '-I', '-B', str(Path(__file__).with_name('resolve_api_probe.py'))],
            shell=False, capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=4, env=environment, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            return {'status': 'unavailable'}
        report = parse_report(result.stdout)
        # Detect a close/restart while the SDK call was in flight.
        if discover_process()[0] != pid:
            return {'status': 'session_changed'}
        return report
    except subprocess.TimeoutExpired:
        return {'status': 'timeout'}
    except Exception:
        return {'status': 'unavailable'}


def describe(report):
    if report.get('status') == 'connected':
        page = report.get('page')
        return f"Connected · Resolve {report['version']}" + (f" · {page.title()}" if page else '')
    return {'not_running': 'Open Resolve, then check again.',
            'sdk_missing': 'Public API runtime is not installed with this Resolve version.',
            'timeout': 'Resolve API did not respond. Palette connection is separate.',
            'session_changed': 'Resolve restarted. Check again.'}.get(
                report.get('status'), 'API unavailable. In Resolve, set External scripting to Local to enable it.')
