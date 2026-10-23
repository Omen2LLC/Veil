# Resolve compatibility and release gate

## Free and Studio support in v0.99.3-beta

The Windows Free executable installed on the Free test machine reports **21.1.1.10**,
SHA-256 `bafcef184b6f056a93098cd5a3fe20125de2f5042f20b2f6dd98ceb7d3ef9157`.
Blackmagic's Free release metadata checked on October 22, 2026 also reports
21.1.1 build 10; the exact response is in `compatibility/latest_windows_free.json`.

Free and Studio share a version number but have different native layouts.
Veil selects a native-verified profile by both version and executable SHA-256,
before requesting writable process access. Unknown hashes and ambiguous matches
remain blocked. Profile dictionary keys identify profiles, not version aliases.
The original Studio profile and evidence are unchanged.

Free evidence: `compatibility/verified/21.1.1.10-free.json`. Vivid and Soft each
passed actual Apply, component readback and byte-for-byte Restore in the
`Veil_Free_QA_20261022` project using generated PNGs and a silence WAV. This covered
all 16 palette entries, four default-fill operands, custom menu-name sources,
96 menu-dot records and three loaded thumbnail records. No user footage was used.
Visual checking is limited to the test machine; other DPI settings remain untested.

Testing exposed a pre-existing 96-byte read of an 80-byte QRasterPlatformPixmap.
The installed Qt5Gui `createCompatiblePlatformPixmap` export at RVA `0xb5af0`
allocates `0x50` bytes (`mov ecx, 0x50` at `0xb5afd`). Its QImage data pointer
is at offset 72. Scanners and ownership checks now stop at 80 bytes, preserving
checks within the object rather than comparing neighboring allocations.
The corresponding [Qt source](https://raw.githubusercontent.com/qt/qtbase/5.15/src/gui/image/qpixmap_raster_p.h)
defines the raster pixmap as QPlatformPixmap plus an embedded QImage.

Studio native tests below are historical evidence from October 15. Studio cannot
be retested on this machine because only Free is installed. Automated tests cover
both edition selections, write-access rejection, and the pixmap-boundary regression.

## Original Studio verification

Checked 2026-10-16 against the [Blackmagic Design support page](https://www.blackmagicdesign.com/support).
The newest listed Windows Studio release is DaVinci Resolve Studio 21.1.1
(posted 2026-10-02). The executable installed on this test PC reports the exact
Windows file version **21.1.1.10**.
The official [Windows Studio release metadata](https://www.blackmagicdesign.com/api/support/latest-stable-version/davinci-resolve-studio/windows.json)
also reports major 21, minor 1, release 1, build 10. The per-release check is
recorded in `compatibility/latest_windows_studio.json`.

| Exact executable version | Veil palette status | Evidence |
| --- | --- | --- |
| 21.1.0.14 | Retired; Apply/Restore disabled | Removed from the active allowlist at the user's request. Old local profile files cannot reactivate it. |
| 21.1.1.10 | Native Apply/Restore verified | Exact executable SHA-256, six relocated function comparisons, all live component signatures/layouts, two native palette transactions and full byte restoration on generated test data. Three loaded media-pool marker records and custom menu names included. Clip/media color IDs unchanged. |
| 21.0.4.5, Resolve 20, later builds | Apply/Restore disabled | No verified native profile or live disposable-session test in this release. |

Before calling another build supported, record its exact file version and
executable hash, derive and review a separate profile, check all read-only
signatures against that binary, and run Apply plus Restore in Resolve with a
disposable project and untouched media. Do not copy an older profile or remove
the version gate to make the buttons clickable. Check Blackmagic's official
support listing for each Veil release and repeat this review when Resolve changes.

Evidence: `compatibility/verified/21.1.1.10.json`. Actual native operations passed;
visual rendering, high-DPI variants and other Windows machines remain manual checks.
Only 21.1.1.10 is enabled in current Veil releases. Historical releases retain their
original behavior and are preserved as archives; use the current release.
