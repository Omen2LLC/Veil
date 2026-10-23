"""Require a fresh official-build check and native evidence for each new release."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

OFFICIAL_URL = 'https://www.blackmagicdesign.com/api/support/latest-stable-version/davinci-resolve-studio/windows.json'
FREE_OFFICIAL_URL = 'https://www.blackmagicdesign.com/api/support/latest-stable-version/davinci-resolve/windows.json'


def exact_build(payload):
    values = payload['windows']
    parts = [values[name] for name in ('major', 'minor', 'releaseNum', 'build')]
    if any(type(part) is not int or part < 0 for part in parts):
        raise ValueError('Official Windows Resolve metadata is invalid')
    return '.'.join(map(str, parts))


def _official_record(version, folder, edition, now):
    record = json.loads((folder / f'compatibility/latest_windows_{edition}.json').read_text(encoding='utf-8'))
    checked = datetime.fromisoformat(record['checked_at_utc'])
    source = FREE_OFFICIAL_URL if edition == 'free' else OFFICIAL_URL
    if (record.get('source') != source or record.get('veil_version') != version
            or not timedelta(0) <= now - checked <= timedelta(hours=24)):
        raise ValueError(f'Refresh the official Resolve {edition} support check for this Veil release')
    return record


def check_record(version, folder, now=None):
    folder = Path(folder)
    now = now or datetime.now(timezone.utc)
    profiles = json.loads((folder / 'compatibility_profiles.json').read_text(encoding='utf-8'))
    report = {'veil_version': version, 'native_apply_restore': 'verified',
              'future_builds': 'blocked until independently tested'}
    for edition in ('studio', 'free'):
        record = _official_record(version, folder, edition, now)
        build = exact_build(record['payload'])
        matches = [profile for profile in profiles.values()
                   if profile.get('version') == build and profile.get('edition', 'studio') == edition
                   and profile.get('native_verified') is True]
        if len(matches) != 1:
            raise ValueError(f'Latest Windows {edition} build has no unique verified native profile: {build}')
        profile = matches[0]
        suffix = '-free' if edition == 'free' else ''
        data = (folder / 'compatibility/verified' / (build + suffix + '.json')).read_bytes()
        result = json.loads(data)
        if (hashlib.sha256(data).hexdigest() != profile.get('verification_sha256')
                or result.get('version') != build
                or not result.get('status', '').startswith('passed actual native')
                or (edition == 'free' and (result.get('edition') != 'free'
                    or result.get('executable_sha256') != profile.get('executable_sha256')))):
            raise ValueError(f'Native {edition} Apply/Restore evidence is missing or mismatched')
        report[f'latest_windows_{edition}_build'] = build
        report[f'{edition}_official_checked_at_utc'] = record['checked_at_utc']
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--record', action='store_true', help='Refresh directly from Blackmagic before checking')
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    if args.record:
        for edition, source in (('studio', OFFICIAL_URL), ('free', FREE_OFFICIAL_URL)):
            request = urllib.request.Request(source, headers={'User-Agent': 'Veil-Release-Check/1'})
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.url != source:
                    raise ValueError('Official support endpoint redirected unexpectedly')
                payload = json.load(response)
            exact_build(payload)
            record = {'source': source, 'veil_version': args.version,
                      'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'payload': payload}
            (folder / f'compatibility/latest_windows_{edition}.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(check_record(args.version, folder), indent=2))


if __name__ == '__main__':
    main()
