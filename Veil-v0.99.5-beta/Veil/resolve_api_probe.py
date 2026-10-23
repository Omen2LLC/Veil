"""Read-only probe executed by Resolve's own Python, never Veil's runtime."""
import json

PREFIX = 'VEIL_RESOLVE_API:'


def snapshot(resolve):
    if resolve is None:
        return {'status': 'unavailable'}
    version = resolve.GetVersion()
    if not isinstance(version, (list, tuple)) or len(version) < 4:
        raise ValueError('Invalid API version')
    parts = version[:4]
    if any(type(part) is not int or not 0 <= part <= 100000 for part in parts):
        raise ValueError('Invalid API version')
    manager = resolve.GetProjectManager()
    project = manager.GetCurrentProject() if manager else None
    return {'status': 'connected', 'version': '.'.join(map(str, parts)),
            'page': resolve.GetCurrentPage(), 'project_open': project is not None,
            'timeline_open': bool(project and project.GetCurrentTimeline())}


def main():
    try:
        import DaVinciResolveScript
        result = snapshot(DaVinciResolveScript.scriptapp('Resolve'))
    except Exception:
        # SDK errors can include private paths; never forward exception text.
        result = {'status': 'unavailable'}
    print(PREFIX + json.dumps(result))


if __name__ == '__main__':
    main()
