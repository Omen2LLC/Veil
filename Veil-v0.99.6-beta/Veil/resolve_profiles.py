"""Exact-build component layouts. Candidate files are never auto-discovered."""
from types import SimpleNamespace


def select_profile(profiles, version, executable_sha256, active_builds):
    """Authorize an exact executable, never a version number or edition label alone."""
    matches = [profile for profile in profiles.values()
               if isinstance(profile, dict)
               and version in active_builds
               and profile.get('version') == version
               and profile.get('native_verified') is True
               and isinstance(profile.get('executable_sha256'), str)
               and len(profile['executable_sha256']) == 64
               and profile['executable_sha256'] == executable_sha256]
    if not matches:
        raise RuntimeError(
            f'No verified profile for this Resolve {version} executable. '
            'Free and Studio require independently verified profiles. No changes made.')
    if len(matches) != 1:
        raise RuntimeError('Ambiguous Resolve executable profiles. No changes made.')
    return matches[0]


def component_layout(signature, name, baseline, byte_fields=(), byte_maps=()):
    supplied = signature.get(name)
    if supplied is None:
        raise RuntimeError(f'No verified {name} layout for this Resolve build.')
    if not isinstance(supplied, dict) or set(supplied) != set(baseline):
        raise RuntimeError(f'Incomplete {name} compatibility profile.')
    values = dict(supplied)
    for field in byte_fields:
        values[field] = bytes.fromhex(values[field])
    for field in byte_maps:
        values[field] = {key: bytes.fromhex(value) for key, value in values[field].items()}
    return SimpleNamespace(**values)
