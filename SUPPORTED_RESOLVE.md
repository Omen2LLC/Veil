# Resolve compatibility and release gate

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
