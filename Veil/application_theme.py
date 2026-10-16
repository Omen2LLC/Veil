"""User-initiated, build-specific application appearance sessions.

Only immutable Qt resource data in a fresh suspended child is changed. Installed
files, existing Resolve sessions, normal shortcuts and Fusion skins are separate.
"""
from pathlib import Path
import contextlib
import ctypes
import hashlib
import json
import os
import re
import struct
import threading
import time
import uuid
import zlib

INSTALL = Path('C:/Program Files/Blackmagic Design/DaVinci Resolve')
EXPECTED_VERSION = '21.1.0.14'
EXPECTED_SOURCE = '0a8f20c70851e629c1753ed537801d1df0b5162ad98a5ab399e4abc7b77df236'
# Set to the independently verified staged recipe before releasing this build.
EXPECTED_RECIPE = '5822d97d90c1083ef92d03f9b0fac282546044554ef84c70ec570cf5efd9a564'
STARTUP_TIMEOUT = 90
COLORS = {(230, 206, 213), (221, 176, 188), (217, 160, 176),
          (217, 130, 155), (212, 105, 134)}
COLOR_PROPERTIES = {'color', 'background-color', 'border-color',
                    'border-top-color', 'border-bottom-color',
                    'border-left-color', 'border-right-color',
                    'selection-color', 'selection-background-color',
                    'alternate-background-color'}
_operation_lock = threading.Lock()
_source_cache = {}


class ApplicationThemeUnavailable(RuntimeError):
    pass


class ApplicationThemeStartupError(RuntimeError):
    """The resumed process is preserved; explicit recovery may be available."""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _file_sha(path, cache=False):
    path = Path(path)
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    if cache and key in _source_cache:
        return _source_cache[key]
    with path.open('rb') as stream:
        result = hashlib.file_digest(stream, 'sha256').hexdigest()
    if cache:
        _source_cache.clear()
        _source_cache[key] = result
    return result


def _resource_path(folder, filename):
    base = Path(folder).resolve() / 'Themes' / 'Application'
    path = (base / filename).resolve()
    if path.parent != base.resolve() or not isinstance(filename, str):
        raise ApplicationThemeUnavailable('Invalid application theme resource path.')
    return path


def _state_path(folder):
    return Path(folder) / 'Themes' / 'Application' / 'session.json'


def _load_state(folder):
    path = _state_path(folder)
    if not path.exists():
        return {'schema': 1, 'enabled': False, 'status': 'Not started', 'session': None}
    if path.stat().st_size > 65536:
        raise ApplicationThemeUnavailable('Application theme session record is invalid.')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('schema') != 1:
        raise ApplicationThemeUnavailable('Application theme session record is invalid.')
    return value


def _save_state(folder, state):
    path = _state_path(folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / ('.application-session-' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write((json.dumps(state, indent=2) + '\n').encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        deadline = time.monotonic() + .5
        while True:
            try:
                os.replace(temporary, path)
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.01)
    finally:
        temporary.unlink(missing_ok=True)


def _advisory_state(folder, state):
    # Never interrupt an already resumed application because of a logging error.
    try:
        _save_state(folder, state)
    except OSError:
        pass


def _decode_slot(slot):
    if not 8 <= len(slot) <= 65536:
        raise ApplicationThemeUnavailable('Invalid compressed resource slot.')
    packed, raw_size = struct.unpack_from('>II', slot)
    if not 8 <= packed + 4 <= len(slot) or not 0 < raw_size <= 1024 * 1024:
        raise ApplicationThemeUnavailable('Invalid compressed resource size.')
    decompressor = zlib.decompressobj()
    raw = decompressor.decompress(slot[8:packed + 4], raw_size + 1)
    if (len(raw) != raw_size or not decompressor.eof or
            decompressor.unused_data or decompressor.unconsumed_tail):
        raise ApplicationThemeUnavailable('Application theme resource decoding failed.')
    return raw


def _qss_blocks(raw):
    text = re.sub(rb'/\*.*?\*/', b'', raw, flags=re.S).decode('utf-8')
    blocks = []
    for match in re.finditer(r'([^{}]+)\{([^{}]*)\}', text):
        selector = ' '.join(match[1].split())
        declarations = []
        for part in match[2].split(';'):
            if not part.strip():
                continue
            if ':' not in part:
                raise ApplicationThemeUnavailable('Unrecognized stylesheet declaration.')
            key, value = part.split(':', 1)
            declarations.append((key.strip(), ' '.join(value.split())))
        blocks.append((selector, declarations))
    return blocks


def _validate_edits(original, proposed, edits, added_rules=()):
    before, after = _qss_blocks(original), _qss_blocks(proposed)
    applied = set()
    for index, (selector, declarations) in enumerate(before):
        expected = list(declarations)
        for edit_index, edit in enumerate(edits):
            if edit['selector'] != selector:
                continue
            if edit_index in applied or edit['property'] not in COLOR_PROPERTIES:
                raise ApplicationThemeUnavailable('Unreviewed stylesheet operation.')
            value = ' '.join(edit['proposed'].split())
            native_foreground = value == 'COLOR_TINT_GRAY'
            rgb = re.fullmatch(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', value)
            hex_color = re.fullmatch(r'#([0-9a-fA-F]{6})', value)
            triplet = tuple(map(int, rgb.groups())) if rgb else (
                tuple(int(hex_color[1][at:at+2],16) for at in (0,2,4)) if hex_color else None)
            if not native_foreground and triplet not in COLORS:
                raise ApplicationThemeUnavailable('A theme color differs from Cherry Blossom.')
            key, old = edit['property'], edit['original']
            found = [i for i, pair in enumerate(expected) if pair[0] == key]
            if old is None:
                if found:
                    raise ApplicationThemeUnavailable('Unexpected existing color declaration.')
                expected.append((key, value))
            else:
                if len(found) != 1 or expected[found[0]][1] != ' '.join(old.split()):
                    raise ApplicationThemeUnavailable('Original stylesheet declaration differs.')
                expected[found[0]] = (key, value)
            applied.add(edit_index)
        before[index] = (selector, expected)
    original_selectors = {selector for selector, _ in before}
    added_selectors = set()
    for rule in added_rules:
        selector = ' '.join(rule['selector'].split())
        if selector in original_selectors or selector in added_selectors:
            raise ApplicationThemeUnavailable('Duplicate appended color selector.')
        parts = selector.split(', ')
        if not parts or any(not re.fullmatch(r'Ui\w+ (?:Ui\w+Label:enabled|QAbstractButton)', part) for part in parts):
            raise ApplicationThemeUnavailable('Unreviewed descendant color selector.')
        declarations = [tuple(pair) for pair in rule['declarations']]
        text_rule = declarations == [('color', 'COLOR_TINT_GRAY')]
        icon_backing = declarations == [('background-color', 'COLOR_ORCA_GRAY')]
        if ((not text_rule and not icon_backing) or
                (text_rule and any(not part.endswith('Label:enabled') for part in parts)) or
                (icon_backing and any(not part.endswith(' QAbstractButton') for part in parts))):
            raise ApplicationThemeUnavailable('Appended rules may only pair neutral labels or retain native button backing.')
        before.append((selector, declarations))
        added_selectors.add(selector)
    if before != after or applied != set(range(len(edits))):
        raise ApplicationThemeUnavailable('Stylesheet changes extend beyond reviewed color edits.')


def load_recipe(folder, expected_digest=None):
    path = _resource_path(folder, 'recipe.json')
    data = path.read_bytes()
    expected_digest = EXPECTED_RECIPE if expected_digest is None else expected_digest
    if _sha(data) != expected_digest:
        raise ApplicationThemeUnavailable('Application theme recipe differs from the reviewed build.')
    recipe = json.loads(data)
    if (recipe.get('resolve_version') != EXPECTED_VERSION or
            recipe.get('source_sha256') != EXPECTED_SOURCE or
            not 1 <= len(recipe.get('resources', [])) <= 29):
        raise ApplicationThemeUnavailable('Application theme belongs to another Resolve build.')
    slots, names = [], set()
    for item in recipe['resources']:
        if item['resource'] in names or not item['resource'].startswith(':/StyleSheet/'):
            raise ApplicationThemeUnavailable('Duplicate or invalid stylesheet resource.')
        names.add(item['resource'])
        if (not isinstance(item['size'], int) or not 8 <= item['size'] <= 65536 or
                not isinstance(item['offset'], int) or item['offset'] < 0 or
                not isinstance(item['rva'], int) or item['rva'] < 0):
            raise ApplicationThemeUnavailable('Invalid resource range.')
        values, raw_values = [], []
        for prefix in ('original', 'proposed'):
            blob = _resource_path(folder, item[prefix + '_file']).read_bytes()
            if len(blob) != item['size'] or _sha(blob) != item[prefix + '_sha256']:
                raise ApplicationThemeUnavailable('Reviewed application theme resource changed.')
            raw = _decode_slot(blob)
            if _sha(raw) != item['raw_' + prefix + '_sha256']:
                raise ApplicationThemeUnavailable('Decoded stylesheet differs from review.')
            values.append(blob)
            raw_values.append(raw)
        original, proposed = values
        packed = struct.unpack_from('>I', proposed)[0]
        if proposed[packed + 4:] != original[packed + 4:]:
            raise ApplicationThemeUnavailable('Application theme exceeds its resource slot.')
        _validate_edits(*raw_values, item['edits'], item.get('added_color_rules', []))
        slots.append((item, original, proposed))
    for key in ('offset', 'rva'):
        ranges = sorted((item[key], item[key] + item['size']) for item, _, _ in slots)
        if any(end > following for (_, end), (following, _) in zip(ranges, ranges[1:])):
            raise ApplicationThemeUnavailable('Application theme resource ranges overlap.')
    return recipe, slots


def _verify_image_ranges(exe, slots):
    with Path(exe).open('rb') as stream:
        dos = stream.read(64)
        if dos[:2] != b'MZ':
            raise ApplicationThemeUnavailable('Resolve is not a PE executable.')
        nt = struct.unpack_from('<I', dos, 60)[0]
        stream.seek(nt)
        header = stream.read(24)
        if header[:6] != b'PE\0\0d\x86':
            raise ApplicationThemeUnavailable('Resolve must use the reviewed x64 build.')
        count = struct.unpack_from('<H', header, 6)[0]
        opt_size = struct.unpack_from('<H', header, 20)[0]
        if not 1 <= count <= 96 or not 112 <= opt_size <= 4096:
            raise ApplicationThemeUnavailable('Invalid Resolve image headers.')
        optional = stream.read(opt_size)
        if optional[:2] != b'\x0b\x02':
            raise ApplicationThemeUnavailable('Resolve is not a PE32+ image.')
        image_size = struct.unpack_from('<I', optional, 56)[0]
        sections = [stream.read(40) for _ in range(count)]
        for item, original, _ in slots:
            matches = []
            for section in sections:
                if len(section) != 40:
                    raise ApplicationThemeUnavailable('Incomplete Resolve section table.')
                virtual_size, rva, raw_size, offset = struct.unpack_from('<IIII', section, 8)
                characteristics = struct.unpack_from('<I', section, 36)[0]
                if offset <= item['offset'] and item['offset'] + item['size'] <= offset + raw_size:
                    matches.append((rva, offset, virtual_size, characteristics))
            if len(matches) != 1:
                raise ApplicationThemeUnavailable('Stylesheet range is outside native image data.')
            rva, offset, virtual_size, flags = matches[0]
            if (flags & 0x20000000 or not flags & 0x40000000 or
                    item['rva'] != rva + item['offset'] - offset or
                    item['rva'] + item['size'] > min(image_size, rva + virtual_size)):
                raise ApplicationThemeUnavailable('Stylesheet is not verified non-executable image data.')
            stream.seek(item['offset'])
            if stream.read(item['size']) != original:
                raise ApplicationThemeUnavailable('Installed stylesheet resource differs from review.')


class NativeRuntime:
    def __init__(self):
        from application_theme_memory import NativeContext
        self.native = NativeContext()
        self.exe = INSTALL / 'Resolve.exe'
        self.monotonic = time.monotonic
        self.sleep = time.sleep

    def username(self):
        return self.native.username()

    def version(self):
        from resolve_palette import file_version
        return file_version(str(self.exe))

    def active_pids(self):
        from theme_transaction import active_resolve_pids
        return active_resolve_pids()

    def lock(self):
        return self.native.lock()

    def child(self):
        from application_theme_memory import SuspendedChild
        return SuspendedChild(self.exe)

    def identity(self, child, username):
        return self.native.identity(child.info.hProcess, child.info.pid, username)

    def observe(self, child):
        return self.native.observe(child.info.hProcess, child.info.pid)

    def inspect_session(self, identity):
        return self.native.inspect_session(identity)

    def cleanup(self, identity):
        return self.native.cleanup(identity)


def require_user_account(runtime):
    username = runtime.username()
    if (not username or username.casefold().startswith('codexsandbox') or
            username.casefold() in ('system', 'local service', 'network service')):
        raise ApplicationThemeUnavailable(
            'Start Veil from your normal Windows desktop account. '
            'Resolve cannot be launched from CodexÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢s restricted diagnostic account. '
            'No Resolve process was created.')
    return username


def _preflight(folder, runtime, validate_source=True, expected_digest=None):
    username = require_user_account(runtime)  # Before any process creation.
    recipe, slots = load_recipe(folder, expected_digest)
    if runtime.version() != EXPECTED_VERSION or (validate_source and _file_sha(runtime.exe) != EXPECTED_SOURCE):
        raise ApplicationThemeUnavailable('Resolve differs from reviewed build ' + EXPECTED_VERSION + '.')
    _verify_image_ranges(runtime.exe, slots)
    return username, recipe, slots


def capability(folder):
    result = dict(can_start=False, can_restore=False, can_cleanup=False,
                  enabled=False, session_enabled=False, session=None,
                  status='Unavailable', reviewed_version=EXPECTED_VERSION,
                  reason='', report={})
    try:
        state = _load_state(folder)
        result.update(enabled=bool(state.get('enabled')),
                      session_enabled=bool(state.get('enabled')),
                      can_restore=bool(state.get('enabled')), session=state.get('session'))
        runtime = NativeRuntime()
        # Periodic UI refresh reads the small reviewed resource slots and version.
        # Full executable hashing remains mandatory at user-initiated preflight
        # and immediately before resume, never on the Tk refresh path.
        username, recipe, _ = _preflight(folder, runtime, validate_source=False)
        result['report'] = recipe
        pids = runtime.active_pids()
        session = state.get('session')
        if (session and state.get('status') == 'startup_timeout' and
                session.get('account', '').casefold() == username.casefold()):
            observed = runtime.inspect_session(session)
            result['can_cleanup'] = observed['matches'] and observed['alive'] and not observed['visible_windows']
        if pids:
            result.update(status='Resolve is running', reason='Save your work and close Resolve normally before starting a themed session.')
        else:
            result.update(can_start=True, status='Ready Ãƒâ€šÃ‚Â· session-only application test',
                          reason='Supported shared interface surfaces only; complete application coverage is unverified.')
        return result
    except (OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
        result['reason'] = str(exc)
        return result


def preflight_theme(folder, *, _runtime=None, _expected_digest=None):
    """Full read-only launch validation; does not create or modify any process."""
    runtime = NativeRuntime() if _runtime is None else _runtime
    username, recipe, slots = _preflight(folder, runtime, expected_digest=_expected_digest)
    if runtime.active_pids():
        raise ApplicationThemeUnavailable('Resolve is running or finishing shutdown. Save your work and close it normally before applying Cherry Blossom.')
    return dict(account=username, reviewed_version=EXPECTED_VERSION,
                source_sha256=EXPECTED_SOURCE, resources_verified=len(slots),
                scope=recipe.get('scope', []), process_created=False,
                installed_files_modified=False)


validate_theme = preflight_theme


@contextlib.contextmanager
def _operation(runtime):
    if not _operation_lock.acquire(blocking=False):
        raise ApplicationThemeUnavailable('Another application theme operation is in progress.')
    try:
        with runtime.lock():
            yield
    finally:
        _operation_lock.release()


def launch_theme(folder, progress=lambda message: None, *, _runtime=None,
                 _expected_digest=None, _startup_timeout=STARTUP_TIMEOUT):
    """Called only from a user-initiated Veil action; never by diagnostics."""
    runtime = NativeRuntime() if _runtime is None else _runtime
    require_user_account(runtime)
    child, resumed = None, False
    with _operation(runtime):
        state = _load_state(folder)
        previous_enabled = bool(state.get('enabled'))
        try:
            progress('Checking the reviewed Resolve build and application resourcesÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦')
            username, recipe, slots = _preflight(folder, runtime, expected_digest=_expected_digest)
            if runtime.active_pids():
                raise ApplicationThemeUnavailable('Resolve is running or finishing shutdown. Save your work and close it normally before starting Cherry Blossom.')
            # A final active-process check precedes creation. Existing processes are
            # never attached to, patched, minimized, restarted or terminated here.
            progress('Preparing a new Cherry Blossom sessionÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦')
            if runtime.active_pids():
                raise ApplicationThemeUnavailable('Resolve opened during preparation. No theme session was created.')
            child = runtime.child()
            identity = runtime.identity(child, username)
            state.update(schema=1, enabled=True, status='preparing', session=identity,
                         recipe_sha256=EXPECTED_RECIPE if _expected_digest is None else _expected_digest,
                         scope=recipe.get('scope', []), appearance_verified=False,
                         native_files_modified=False, last_error=None)
            _save_state(folder, state)  # Mandatory recovery metadata before resume.
            for item, original, proposed in slots:
                child.patch_data(item['rva'], original, proposed)
            base = child.image_base()
            for item, _, proposed in slots:
                if child.read(base + item['rva'], len(proposed)) != proposed:
                    raise ApplicationThemeUnavailable('Final application resource readback failed.')
            if _file_sha(runtime.exe) != EXPECTED_SOURCE:
                raise ApplicationThemeUnavailable('Resolve changed during preparation. The suspended session was cancelled.')
            if any(pid != identity['pid'] for pid in runtime.active_pids()):
                raise ApplicationThemeUnavailable('Another Resolve instance opened during preparation. The suspended theme session was cancelled.')
            state['status'] = 'starting'
            _save_state(folder, state)
            child.resume()
            resumed = child.resumed
            deadline = runtime.monotonic() + max(0, min(float(_startup_timeout), STARTUP_TIMEOUT))
            progress('Starting Resolve and waiting for its normal interfaceÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦')
            while True:
                observation = runtime.observe(child)
                if not observation['alive']:
                    state.update(status='startup_exited', exit_code=observation.get('exit_code'))
                    raise ApplicationThemeStartupError('Resolve exited before its normal interface appeared. Installed files and regular shortcuts are unchanged; open Resolve using your regular shortcut.')
                if observation.get('main_window'):
                    state.update(status='window_detected', window=observation['main_window'])
                    _advisory_state(folder, state)
                    return 'ResolveÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢s interface opened with the Cherry Blossom session resources. Appearance coverage still needs a live check.'
                if runtime.monotonic() >= deadline:
                    state['status'] = 'startup_timeout'
                    raise ApplicationThemeStartupError(
                        'Resolve has not shown its normal interface after 90 seconds. '
                        'Its process was left running to protect any project. '
                        'If no Resolve window or project is open, use the recovery control before trying your regular shortcut.')
                runtime.sleep(.25)
        except Exception as exc:
            if child is not None:
                resumed = bool(child.resumed)
            if child is not None and not resumed:
                state.update(enabled=previous_enabled, status='preparation_failed', session=None)
            elif resumed and state.get('status') not in ('startup_timeout', 'startup_exited'):
                state['status'] = 'startup_uncertain'
            state['last_error'] = str(exc)
            _advisory_state(folder, state)
            raise
        finally:
            if child is not None:
                child.dispose()  # Discards only our never-resumed child; closes handles after resume.


def disable_theme(folder, *, _runtime=None):
    """Disable future themed-session state; an active session must close normally."""
    runtime = NativeRuntime() if _runtime is None else _runtime
    with _operation(runtime):
        state = _load_state(folder)
        state['enabled'] = False
        _save_state(folder, state)
    return 'Application session theme disabled. Close any themed Resolve session normally and reopen it using your regular shortcut for the original application appearance.'


def cleanup_failed_start(folder, confirm_no_project=False, *, _runtime=None):
    """Explicit recovery for a timed-out owned process, never an ordinary session."""
    if confirm_no_project is not True:
        raise ApplicationThemeUnavailable('Confirm that no Resolve window or project is open before clearing a failed launch.')
    runtime = NativeRuntime() if _runtime is None else _runtime
    username = require_user_account(runtime)
    with _operation(runtime):
        state = _load_state(folder)
        identity = state.get('session')
        if (state.get('status') != 'startup_timeout' or not identity or
                identity.get('account', '').casefold() != username.casefold()):
            raise ApplicationThemeUnavailable('No matching timed-out theme process is available for recovery.')
        observation = runtime.inspect_session(identity)
        if not observation['matches'] or not observation['alive']:
            raise ApplicationThemeUnavailable('The failed process exited or its identity changed. No process was cleared.')
        if observation['visible_windows']:
            raise ApplicationThemeUnavailable('Resolve has a visible window. Close it normally; recovery will not interrupt it.')
        runtime.cleanup(identity)  # Rechecks start time, path, session, liveness and all visible windows.
        state.update(status='cleanup_complete', enabled=False, session=None, last_error=None)
        _save_state(folder, state)
        return 'The matching failed theme launch was cleared. Open Resolve using your regular shortcut.'
