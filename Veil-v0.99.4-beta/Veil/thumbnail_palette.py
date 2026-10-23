"""Build-locked media-pool thumbnail indicators for the existing 16 slots."""
import hashlib
import json
import struct
import time

from palette_core import LABELS, STOCK, atomic_json, validate_palette
from thumbnail_scan import scan

PREFIX = ':/Common/FlagsAndMarkers/Thumbnail_'


def recolor(stock, source_rgba, center_rgb, color):
    """Preserve each embedded marker's alpha and dark edge shading."""
    target = bytes.fromhex(color[1:])
    channel = max(range(3), key=lambda i: center_rgb[i])
    scale = center_rgb[channel]
    if not scale or len(stock) != 11 * 12 * 4 or len(source_rgba) != len(stock):
        raise RuntimeError('Invalid thumbnail color mask')
    result = bytearray(stock)
    for i in range(0, len(stock), 4):
        alpha = source_rgba[i + 3]
        if not any(source_rgba[i:i + 3]):
            continue
        strength = source_rgba[i + channel] / scale
        rgb = [min(255, round(c * strength)) for c in target]
        result[i:i + 3] = bytes(((rgb[2] * alpha + 127) // 255,
                                 (rgb[1] * alpha + 127) // 255,
                                 (rgb[0] * alpha + 127) // 255))
    return bytes(result)


class ThumbnailPalette:
    def __init__(self, session):
        self.s = session
        self.signatures = json.loads((session.folder / 'thumbnail_signatures.json').read_text(encoding='utf-8'))
        if set(self.signatures) != set(LABELS):
            raise RuntimeError('Incomplete thumbnail signature set')
        self.groups = {}
        self.records = []
        self.palette = validate_palette(STOCK)
        self.discover()
        self.check()

    @property
    def dirty(self):
        return any(r['expected'] != r['original'] for r in self.records)

    def ownership(self, dot):
        s = self.s
        im = dot['images'][0]
        for address, expected in (
            (int(dot['node'], 16) + 32, int(dot['object'], 16)),
            (int(dot['object'], 16) + 8, int(dot['data'], 16)),
        ):
            if s.read(address, 8) != struct.pack('<Q', expected):
                raise RuntimeError('Thumbnail ownership changed; restart Resolve.')
        if s.read(int(dot['data'], 16), 120) != bytes.fromhex(dot['header']):
            raise RuntimeError('Thumbnail resource changed; restart Resolve.')
        platform = s.read(int(im['platform'], 16), 80)
        original_platform = bytes.fromhex(im['platform_header'])
        if (platform[:8] != original_platform[:8] or
            platform[8:20] != original_platform[8:20] or
            platform[72:80] != original_platform[72:80]):
            raise RuntimeError('Thumbnail platform image changed; restart Resolve.')
        image = s.read(int(im['image_data'], 16), 96)
        original_image = bytes.fromhex(im['image_header'])
        refs = struct.unpack_from('<i', image)[0]
        if not 1 <= refs < 100000:
            raise RuntimeError('Thumbnail reference count changed unexpectedly.')
        # Qt changes other cache/padding fields during painting. Only the
        # verified dimensions, format, buffer and stride are ownership-critical.
        for start, end in ((4, 32), (40, 52), (56, 64)):
            if image[start:end] != original_image[start:end]:
                raise RuntimeError('Thumbnail pixel layout changed; restart Resolve.')

    def check(self):
        for r in self.records:
            self.ownership(r['dot'])
            if self.s.read(r['address'], len(r['expected'])) != r['expected']:
                raise RuntimeError('Another action changed a media-pool dot; restart Resolve.')

    def discover(self):
        """Register only icons already loaded by Resolve; never create UI objects."""
        for attempt in range(3):
            try:
                normal, _, _, _ = scan(self.s)
                transient = any(
                    dot['name'].startswith(PREFIX) and any(
                        image.get('diagnostic') == 'Image changed during read'
                        for image in dot.get('images', [])) for dot in normal)
                if transient:
                    raise ValueError('Thumbnail image changed during read')
                break
            except ValueError as exc:
                if attempt == 2 or not any(word in str(exc).lower() for word in ('map changed', 'tree changed', 'image changed')):
                    raise
                time.sleep(0.05)
        found = {}
        for dot in normal:
            if not dot['name'].startswith(PREFIX):
                continue
            label = dot['name'][len(PREFIX):]
            if label not in LABELS or label in found:
                raise RuntimeError('Unexpected media-pool thumbnail resource')
            found[label] = dot
        for label in self.groups:
            if label not in found:
                raise RuntimeError('A loaded thumbnail disappeared; restart Resolve.')
            old = self.groups[label][0]['dot']
            if any(found[label][key] != old[key] for key in ('node', 'object', 'data')):
                raise RuntimeError('Resolve replaced a thumbnail resource; restart Resolve.')
            if found[label]['images'][0].get('pixels') != old['images'][0].get('pixels'):
                raise RuntimeError('Resolve replaced thumbnail pixels; restart Resolve.')
        added = []
        for label, dot in found.items():
            if label in self.groups:
                continue
            if len(dot.get('images', [])) != 1:
                raise RuntimeError('Thumbnail scaling is unsupported; this build requires 1x images.')
            im = dot['images'][0]
            if not im.get('validated') or (im['width'], im['height'], im['format'], im['stride'], im['dpr']) != (11, 12, 6, 44, 1):
                raise RuntimeError('Unsupported media-pool thumbnail image layout')
            stock = bytes.fromhex(self.signatures[label]['stock_pixels'])
            source_rgba = bytes.fromhex(self.signatures[label]['source_rgba'])
            if hashlib.sha256(stock).hexdigest() != self.signatures[label]['sha256']:
                raise RuntimeError('Invalid embedded thumbnail signature')
            if len(source_rgba) != len(stock) or bytes(v for i in range(0, len(stock), 4)
                for v in ((source_rgba[i+2]*source_rgba[i+3]+127)//255,
                          (source_rgba[i+1]*source_rgba[i+3]+127)//255,
                          (source_rgba[i]*source_rgba[i+3]+127)//255,
                          source_rgba[i+3])) != stock:
                raise RuntimeError('Thumbnail source pixels do not match embedded signature')
            if bytes.fromhex(im['pixel_bytes']) != stock:
                raise RuntimeError('A media-pool dot was already changed. Restart Resolve before connecting.')
            center = self.signatures[label]['center_rgb']
            if list(stock[(6 * 11 + 5) * 4:(6 * 11 + 5) * 4 + 4]) != [center[2], center[1], center[0], 255]:
                raise RuntimeError('Invalid thumbnail center signature')
            group = [dict(dot=dot, label=label, address=int(im['pixels'], 16),
                          original=stock, expected=stock, kind='pixels')]
            for field, header, offset in (('platform', 'platform_header', 28),
                                          ('image_data', 'image_header', 68)):
                old = bytes.fromhex(im[header])[offset:offset + 4]
                group.append(dict(dot=dot, label=label, address=int(im[field], 16) + offset,
                                  original=old, expected=old, kind='key'))
            self.groups[label] = group
            self.records.extend(group)
            added.extend(group)
        if len({r['address'] for r in self.records}) != len(self.records):
            raise RuntimeError('Unexpected shared thumbnail storage')
        self.check()
        return added

    def plan(self, palette, records=None):
        palette = validate_palette(palette)
        selected = self.records if records is None else records
        result = {}
        for r in selected:
            if r['kind'] == 'pixels':
                result[r['address']] = recolor(r['original'], bytes.fromhex(self.signatures[r['label']]['source_rgba']),
                                               self.signatures[r['label']]['center_rgb'],
                                               palette[LABELS.index(r['label'])][1])
            else:
                value = struct.unpack('<I', r['expected'])[0]
                if value >= 0xFFFFFF00:
                    raise RuntimeError('Thumbnail generation counter exhausted; restart Resolve.')
                result[r['address']] = struct.pack('<I', value + 1)
        return result

    def snapshot(self):
        return {r['address']: r['expected'] for r in self.records}

    def transition(self, changes):
        self.check()
        previous = self.snapshot()
        if not any(changes.get(r['address'], r['expected']) != r['expected'] for r in self.records):
            return
        atomic_json(self.s.folder / 'thumbnail_recovery.json', dict(
            identity=self.s.identity(),
            records=[dict(label=r['label'], address=r['address'], kind=r['kind'],
                          original=r['original'].hex(), previous=r['expected'].hex(),
                          target=changes.get(r['address'], r['expected']).hex()) for r in self.records]))
        attempted = []
        try:
            for r in self.records:
                new = changes.get(r['address'], r['expected'])
                if new == r['expected']:
                    continue
                self.ownership(r['dot'])
                attempted.append(r)
                self.s.write(r['address'], new)
                r['expected'] = new
        except Exception as error:
            failures = []
            for r in reversed(attempted):
                try:
                    self.ownership(r['dot'])
                    old = previous[r['address']]
                    new = changes[r['address']]
                    current = self.s.read(r['address'], len(old))
                    if any(c not in (a, b) for c, a, b in zip(current, old, new)):
                        raise RuntimeError('Concurrent thumbnail change')
                    self.s.write(r['address'], old)
                    r['expected'] = old
                except Exception as exc:
                    failures.append(str(exc))
            if failures:
                raise RuntimeError('Thumbnail rollback failed; restart Resolve. ' + str(failures)) from error
            raise

    def apply(self, palette):
        palette = validate_palette(palette)
        if palette == validate_palette(STOCK):
            return self.restore()
        self.discover()
        self.transition(self.plan(palette))
        self.palette = palette

    def refresh(self):
        added = self.discover()
        if added and self.palette != validate_palette(STOCK):
            self.transition(self.plan(self.palette, added))
        return bool(added)

    def restore(self):
        self.transition({r['address']: r['original'] for r in self.records})
        self.palette = validate_palette(STOCK)
