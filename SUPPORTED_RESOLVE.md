# Resolve compatibility and release gate

Checked 2026-10-15 against the [Blackmagic Design support page](https://www.blackmagicdesign.com/support).
The newest listed Windows Studio release is DaVinci Resolve Studio 21.1.1
(posted 2026-10-02). The executable installed on this test PC reports the exact
Windows file version **21.1.1.10**.

| Exact executable version | Veil palette status | Evidence |
| --- | --- | --- |
| 21.1.0.14 | Existing exact native profile | `build_signature.json`, function fingerprint and read-before-write guards. This task has not repeated native Apply/Restore. |
| 21.1.1.10 | Apply/Restore disabled | Installed executable version is newer than the profile. Veil refuses writable process access before a native handle opens. |
| 21.0.4.5, Resolve 20, later builds | Apply/Restore disabled | No verified native profile or live disposable-session test in this release. |

Before calling another build supported, record its exact file version and
executable hash, derive and review a separate profile, check all read-only
signatures against that binary, and run Apply plus Restore in Resolve with a
disposable project and untouched media. Do not copy an older profile or remove
the version gate to make the buttons clickable. Check Blackmagic's official
support listing for each Veil release and repeat this review when Resolve changes.
