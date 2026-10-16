"""Require a fresh official-build check and native evidence for each new release."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

OFFICIAL_URL = 'https://www.blackmagicdesign.com/api/support/latest-stable-version/davinci-resolve-studio/windows.json'


def exact_build(payload):
    values = payload['windows']
    parts = [values[name] for name in ('major', 'minor', 'releaseNum', 'build')]
    if any(type(part) is not int or part < 0 for part in parts):
        raise ValueError('Official Windows Studio metadata is invalid')
    return '.'.join(map(str, parts))


def check_record(version, folder, now=None):
    folder = Path(folder)
    record = json.loads((folder / 'compatibility/latest_windows_studio.json').read_text(encoding='utf-8'))
    checked = datetime.fromisoformat(record['checked_at_utc'])
    now = now or datetime.now(timezone.utc)
    if (record.get('source') != OFFICIAL_URL or record.get('veil_version') != version
            or not timedelta(0) <= now - checked <= timedelta(hours=24)):
        raise ValueError('Refresh the official Resolve support check for this Veil release')
    build = exact_build(record['payload'])
    profiles = json.loads((folder / 'compatibility_profiles.json').read_text(encoding='utf-8'))
    profile = profiles.get(build, {})
    if profile.get('native_verified') is not True or profile.get('version') != build:
        raise ValueError('Latest Windows Studio build has no verified native profile: ' + build)
    evidence = folder / 'compatibility/verified' / (build + '.json')
    data = evidence.read_bytes()
    result = json.loads(data)
    if (hashlib.sha256(data).hexdigest() != profile.get('verification_sha256')
            or result.get('version') != build
            or not result.get('status', '').startswith('passed actual native')):
        raise ValueError('Native Apply/Restore evidence is missing or mismatched')
    return {'veil_version': version, 'latest_windows_studio_build': build,
            'official_checked_at_utc': record['checked_at_utc'],
            'native_apply_restore': 'verified', 'future_builds': 'blocked until independently tested'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--record', action='store_true', help='Refresh directly from Blackmagic before checking')
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    if args.record:
        request = urllib.request.Request(OFFICIAL_URL, headers={'User-Agent': 'Veil-Release-Check/1'})
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.url != OFFICIAL_URL:
                raise ValueError('Official support endpoint redirected unexpectedly')
            payload = json.load(response)
        exact_build(payload)
        record = {'source': OFFICIAL_URL, 'veil_version': args.version,
                  'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'payload': payload}
        (folder / 'compatibility/latest_windows_studio.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(check_record(args.version, folder), indent=2))


if __name__ == '__main__':
    main()
