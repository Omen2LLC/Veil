"""Exact-build component layouts. Candidate files are never auto-discovered."""
from types import SimpleNamespace


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
