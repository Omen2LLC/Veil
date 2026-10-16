"""Conservative GitHub Releases updates for Veil.

The running application only checks and downloads. A separate process installs
the verified ZIP after the UI exits. Existing releases and user state remain in
place, and the launcher pointer is changed only after a successful smoke check.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from urllib.parse import urlsplit
import urllib.request
import zipfile


OWNER = "Omen2LLC"
REPOSITORY = "Veil"
API_URL = f"https://api.github.com/repos/{OWNER}/{REPOSITORY}/releases?per_page=100"
MAX_ARCHIVE_BYTES = 300_000_000
MAX_EXTRACTED_BYTES = 700_000_000
USER_FILES = ("saved_palettes.json", "studio-settings.json", "veil-update.json")
VERSION = re.compile(r"v(\d+)\.(\d+)(?:\.(\d+))?\Z")
CURRENT_VERSION = re.compile(r"v(\d+)\.(\d+)(?:\.(\d+))?(?:-beta(?:-r\d+)?)?\Z")


class UpdateError(RuntimeError):
    pass


def version_tuple(label: str) -> tuple[int, int, int] | None:
    match = VERSION.fullmatch(label)
    return tuple(int(part or 0) for part in match.groups()) if match else None


def newer_stable_release(payload: dict, current: str) -> dict | None:
    """Return a release only when its stable tag exceeds this Veil version."""
    current_match = CURRENT_VERSION.fullmatch(current)
    current_number = tuple(int(part or 0) for part in current_match.groups()) if current_match else None
    tag = payload.get("tag_name", "")
    candidate = version_tuple(tag)
    if not current_number or not candidate or payload.get("draft") or payload.get("prerelease"):
        return None
    if candidate < current_number or (candidate == current_number and "-beta" not in current):
        return None
    assets = {asset.get("name"): asset for asset in payload.get("assets", [])}
    archive_name = f"Veil-{tag}-windows.zip"
    if archive_name not in assets or "SHA256SUMS.txt" not in assets:
        return None
    return {"version": tag, "notes": str(payload.get("body") or "").strip(),
            "archive": assets[archive_name], "checksums": assets["SHA256SUMS.txt"]}


def release_order(tag):
    match = re.fullmatch(r'v(\d+)\.(\d+)(?:\.(\d+))?(?:-beta(?:-r(\d+))?)?', tag)
    if not match:
        return None
    major, minor, patch, revision = match.groups()
    return (int(major), int(minor), int(patch or 0), int('-beta' not in tag), int(revision or 0))


def newer_available_release(records, current):
    """Beta installs receive newer betas and stable releases; stable stays stable."""
    baseline = release_order(current)
    if baseline is None:
        return None
    candidates = []
    for record in records:
        tag = record.get('tag_name', '')
        order = release_order(tag)
        beta = '-beta' in tag
        if (order is None or order <= baseline or record.get('draft')
                or (beta and '-beta' not in current)
                or bool(record.get('prerelease')) != beta):
            continue
        assets = {a.get('name'): a for a in record.get('assets', [])}
        name = f'Veil-{tag}-windows.zip'
        if name in assets and 'SHA256SUMS.txt' in assets:
            candidates.append((order, {'version': tag, 'notes': str(record.get('body') or '').strip(),
                                      'archive': assets[name], 'checksums': assets['SHA256SUMS.txt']}))
    return max(candidates, key=lambda entry: entry[0])[1] if candidates else None


def _github_asset_url(asset: dict, tag: str) -> str:
    name = asset.get("name", "")
    expected = f"https://github.com/{OWNER}/{REPOSITORY}/releases/download/{tag}/{name}"
    if asset.get("browser_download_url") != expected:
        raise UpdateError("Release asset URL is outside the expected Omen2LLC release.")
    return expected


def _read_url(url: str, limit: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Veil-Updater/1", "Accept": "application/octet-stream"})
    with urllib.request.urlopen(request, timeout=12) as response:
        final = urlsplit(response.url)
        if final.scheme != "https" or final.hostname not in {
                "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}:
            raise UpdateError("Release download redirected outside GitHub.")
        data = response.read(limit + 1)
    if len(data) > limit:
        raise UpdateError("Release asset exceeds the size limit.")
    return data


def check_latest(current: str) -> dict | None:
    request = urllib.request.Request(API_URL, headers={"User-Agent": "Veil-Updater/1", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=8) as response:
        if response.url != API_URL:
            raise UpdateError("Release API redirected unexpectedly.")
        payload = json.load(response)
    if not isinstance(payload, list):
        raise UpdateError('GitHub returned an invalid release list.')
    return newer_available_release(payload, current)


def verified_download(release: dict, destination: Path) -> Path:
    tag = release["version"]
    archive_asset = release["archive"]
    archive_name = archive_asset["name"]
    checksums = _read_url(_github_asset_url(release["checksums"], tag), 100_000).decode("ascii")
    expected = None
    for line in checksums.splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?([^\\/]+)", line.strip())
        if match and match.group(2) == archive_name:
            expected = match.group(1).lower()
    if expected is None:
        raise UpdateError("The release checksum list does not name this Windows package.")
    data = _read_url(_github_asset_url(archive_asset, tag), MAX_ARCHIVE_BYTES)
    if hashlib.sha256(data).hexdigest() != expected:
        raise UpdateError("Downloaded package checksum does not match the release.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".veil-download-", delete=False) as file:
        temporary = Path(file.name)
        file.write(data)
        file.flush()
        os.fsync(file.fileno())
    try:
        with zipfile.ZipFile(temporary) as archive:
            inspect_archive(archive, tag)
            if archive.testzip() is not None:
                raise UpdateError("Release ZIP failed its integrity check.")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def inspect_archive(archive: zipfile.ZipFile, tag: str) -> None:
    expected_prefix = f"Veil-{tag}/Veil/"
    total = 0
    seen: set[str] = set()
    for info in archive.infolist():
        name = info.filename
        path = PurePosixPath(name)
        if (not name.startswith(expected_prefix) or "\\" in name or path.is_absolute()
                or ".." in path.parts or ":" in name or name in seen):
            raise UpdateError("Release ZIP contains an unexpected path.")
        seen.add(name)
        if ((info.external_attr >> 16) & 0o170000) == 0o120000:
            raise UpdateError("Release ZIP contains a symbolic link.")
        total += info.file_size
        if total > MAX_EXTRACTED_BYTES:
            raise UpdateError("Release ZIP is too large when extracted.")
    if expected_prefix + "studio_version.py" not in seen:
        raise UpdateError("Release ZIP has no matching Veil version file.")
    if not ({expected_prefix + "Veil.exe", expected_prefix + "veil_app.py"} & seen):
        raise UpdateError("Release ZIP has no Veil program entry point.")


def install_staged(archive_path: Path, tag: str, current_app: Path,
                   releases_root: Path, pointer: Path, smoke_check=None) -> Path:
    """Install beside the old version, preserving it for one-step rollback.

    Call from a helper after Veil exits. The smoke check should start the new
    app in a disposable/read-only mode; any failure leaves the pointer intact.
    """
    if release_order(tag) is None:
        raise UpdateError("Only valid stable or beta version tags can be installed.")
    archive_path, current_app = Path(archive_path), Path(current_app)
    releases_root, pointer = Path(releases_root), Path(pointer)
    target = releases_root / f"Veil-{tag}"
    if target.exists():
        raise UpdateError("Target release already exists; refusing to overwrite it.")
    with zipfile.ZipFile(archive_path) as archive:
        inspect_archive(archive, tag)
        if archive.testzip() is not None:
            raise UpdateError("Staged ZIP is corrupt.")
        staging = Path(tempfile.mkdtemp(prefix=".veil-stage-", dir=releases_root))
        try:
            archive.extractall(staging)
            app = staging / f"Veil-{tag}" / "Veil"
            declared = app / "studio_version.py"
            if not re.search(rf'^VERSION\s*=\s*[\'\"]{re.escape(tag)}[\'\"]\s*$',
                             declared.read_text(encoding="utf-8"), re.MULTILINE):
                raise UpdateError("Package internal version does not match the release tag.")
            for name in USER_FILES:
                source = current_app / name
                if source.is_file():
                    if name == "saved_palettes.json" and (app / name).is_file():
                        try:
                            old = json.loads(source.read_text(encoding="utf-8"))
                            fresh = json.loads((app / name).read_text(encoding="utf-8"))
                            if (old.get("schema") not in (1, 2) or fresh.get("schema") != 2
                                    or not isinstance(old.get('palettes'), dict)
                                    or not isinstance(fresh.get('palettes'), dict)):
                                raise ValueError("Unknown palette library schema")
                            previous = old['palettes']
                            if old['schema'] == 1:
                                from palette_core import LABELS
                                previous = {name: {'colors': colors, 'display_names': list(LABELS)}
                                            for name, colors in previous.items()}
                            fresh["palettes"].update(previous)
                            (app / name).write_text(json.dumps(fresh, indent=2, ensure_ascii=False) + "\n",
                                                    encoding="utf-8")
                        except (OSError, ValueError, TypeError, KeyError) as error:
                            raise UpdateError('Your palette library could not be migrated; current Veil kept intact.') from error
                    else:
                        shutil.copy2(source, app / name)
            if smoke_check is not None:
                smoke_check(app)
            (staging / f"Veil-{tag}").replace(target)
            new_app = target / "Veil"
            old_pointer = pointer.read_bytes() if pointer.exists() else None
            pointer.parent.mkdir(parents=True, exist_ok=True)
            temp_pointer = pointer.with_name(pointer.name + ".new")
            try:
                temp_pointer.write_text(str(new_app), encoding="utf-8")
                temp_pointer.replace(pointer)
            except Exception:
                if old_pointer is not None:
                    pointer.write_bytes(old_pointer)
                else:
                    pointer.unlink(missing_ok=True)
                raise
            return new_app
        finally:
            shutil.rmtree(staging, ignore_errors=True)
