# Veil changelog (formerly O2 Switcher)

Veil is an experimental external Windows application for DaVinci Resolve Studio 21.1.0.14. Versions through v0.18 were named O2 Switcher. These numbered builds are previews, not a supported Resolve plugin. Each palette replaces the colors behind Resolve's existing 16 slots; it does not add slots or change clips' assigned slot identities.

## v0.81 - Cherry Blossom application session test

- Added a version/hash-locked application layer beside the existing Cherry Blossom Fusion skin. A user-initiated Start Resolve creates its own suspended process, validates and changes four non-executable stylesheet resource slots, verifies them and restores memory protections before startup. Installed Resolve.exe and regular shortcuts remain unchanged.
- Twenty color properties cover the exposed page-bar frame, menu bar/text/selected bar items, text tooltips, enabled scrollbar handles, Sound Library keyword field and Inspector subtitle caption timecode field. Supplied Cherry Blossom colors and native dark foregrounds are used; all non-color declarations and 25 other main stylesheets remain unchanged. Most panels, popup menus, custom-painted areas, Fairlight DLL resources and plug-ins remain unsupported.
- Apply Theme validates both layers before installing Fusion and starting a themed session. Restore Original disables future session state and restores Fusion using the existing protected transaction. Normal closure removes session colors; no automatic close, minimization or interruption of existing Resolve processes.
- Startup waits for a visible titled Resolve Qt window with a finite timeout. A timed-out resumed process is preserved; explicit recovery requires confirmation and rechecks process identity and absence of visible windows. Restricted Codex diagnostic accounts are refused before child creation.
- Resource/style audit, fake-runtime failure and recovery tests, disposable native resource fixtures and isolated Tk dark/light/responsive checks passed. Expanded native appearance, startup and comprehensive behavior still require a live user-account check; this is not a complete application theme.

## v0.80 - Cherry Blossom Restore progress-file lock fix

- A transient Windows permission denial on a progress JSON used to cancel Restore before skin replacement. Progress reads/writes are now advisory; the authoritative result is read first. Mandatory request/result reads tolerate short sharing races with finite limits.
- A final result locked after worker exit gets a bounded read grace. Cancellation, expiry, build/hash checks and original backup guards remain enforced. Cancellation write failures do not mask the original failure or bypass owned-helper timeout cleanup.
- Reproduced the reported errno 13 with native Windows exclusive file handles. Fixture Apply/Restore, mandatory cancellation and finite failure paths, real Tk dispatch and elevation regressions passed. Cherry Blossom theme values, recipe, palettes and preferences unchanged; live Restore retry remains pending.

## v0.79 - Cherry Blossom theme

- Replaced the Oxygen Test catalogue entry with Cherry Blossom, using the approved first Petal mockup and the exact five supplied hex colors for supported Fusion surfaces and accents. Native dark text is reused for contrast; semantic warnings/errors, category/socket colors and image content remain unchanged.
- Themes shows the approved reference with Apply Theme and Restore Original above it. Clip palettes and Omen dark/light preferences are independent and preserved.
- Retained build/hash checks, original backup, finite elevated helper and atomic restoration. Recognizes old theme hashes solely for restoration before Cherry Blossom; no automatic Resolve close/restart or window minimization.
- Verified UI clicks/worker recovery, temporary-file Apply/Restore, migration, archive assets/layouts and exact colors. Native Cherry Blossom appearance and whole-Resolve coverage remain unverified. No live resource changes made by this release task.

## v0.78 - graceful Resolve shutdown before theme restoration

- User confirmed the stronger Oxygen Test is visible; Apply journal and installed resource hash matched the candidate. Early Restore attempts were refused during shutdown; a later retry succeeded, with journal and installed hash matching the original.
- Process checks now open a SYNCHRONIZE-only handle and inspect actual exit state, ignoring signalled/exited processes and PIDs that disappeared after enumeration. Unverifiable processes still fail closed.
- Before requesting administrator access, Apply/Restore wait up to 20 seconds for graceful Resolve exit with visible progress, then continue automatically. Persistent processes yield a clear retry message. No process termination, automatic application restart or resource write while Resolve is active.
- Verified native exited-process handles retained by the parent, process disappearance/access-denial cases, shutdown completion and timeout, refusal before helper launch, actual Tk operations through child processes on temporary skin copies, restoration/idempotence and unchanged library data. Full functional/application coverage remains unverified.
- Preserved the original theme backup locally and packaged `Omen-Studio-v0.78-Resolve-Shutdown.zip` without proprietary archives or pending operations.

## v0.77 - Resolve-closed preflight before administrator approval

- User-operation logs confirmed the v0.76 elevated helper ran but rejected each attempt because Resolve was still running; the installed skin remained original. The Windows approval prompt names Python because it is the actual runtime requesting access.
- Apply/Restore now check the Resolve process before any administrator/helper launch. The helper still repeats the check after approval and immediately before replacement. Resolve is never closed automatically.
- Moved readable transaction status directly above the action buttons, with explicit not-installed/not-restored messages and recovery instructions. Explains that the Windows approval names Python and Resolve must be reopened manually to load the skin.
- Verified the native running-process refusal for Apply and Restore with no helper launches or installed-file changes, real child-process Apply/Restore on temporary resources, preflight failures through Tk in Dark/Light, recovery/navigation, archive integrity and unchanged palette data. Live closed-Resolve installation remains awaiting user action.
- Packaged as `Omen-Studio-v0.77-Theme-Preflight.zip`. Stronger Fusion-only theme, palette data and all other UI behavior unchanged.

## v0.76 - protected Fusion skin installation fix

- Removed NamedTemporaryFile from theme staging. On Windows its access-denied retry loop can prevent PermissionError from reaching the elevation fallback. Exclusive UUID staging now fails immediately if the destination denies creation; permission-denial tests preserve the original.
- Requests administrator access before protected Apply/Restore writes. Every installation runs in an isolated helper, including already elevated launches. The 90-second deadline now covers the whole operation rather than just elevation. A real stalled child was terminated and its delayed write prevented in QA.
- Rechecks cancellation, expiry and Resolve closure after staging/flush and immediately before atomic replacement. Added granular transaction progress and helper stack logs. Brief Windows reader-sharing races receive a bounded retry.
- Verified the actual Tk actions through real child processes using temporary skin copies, cancellation during flush, timeout/recovery, archive integrity and all 15 palettes. A native read-only isolated-worker probe passed; the live installed skin remains original. Administrator launch from the normal user shortcut still needs live verification; the prior test-environment elevation probe was refused by Windows.
- Retains the stronger Fusion-only recipe. No palette, Omen appearance, Resolve layout or clip-backend changes. Packaged as `Omen-Studio-v0.76-Theme-Install-Fix.zip` without proprietary resource archives or pending requests.

## v0.75 - recoverable Fusion theme administrator handoff

- Replaced the worker-thread Windows elevation call and indefinite process wait with a separate COM STA broker and a 90-second approval/helper timeout. Cancelled and expired requests are checked again immediately before installation, so late helpers cannot start a cancelled commit.
- Added progress for the Resolve check, original backup, candidate verification, administrator approval and installation/restoration. Failed operations release the controls and retain the error instead of being overwritten by queued progress. Completion callback failures no longer stop worker result delivery.
- Verified Apply/Restore on temporary resource copies, navigation during work, timeout/cancellation/expired requests, original preservation before a cancelled commit, callback recovery and all 15 palettes. The native read-only administrator probe returned Windows error 0xC0000142 in the test environment; successful UAC installation still needs a normal-shortcut live check. The installed Resolve skin is unchanged.
- Retains the stronger v0.74 Fusion-only appearance, version/hash guards and original backups. No theme expansion or palette-data changes. Packaged as `Omen-Studio-v0.75-Theme-Apply-Fix.zip` without proprietary skin archives or pending requests.

## v0.74 - more apparent Oxygen Fusion theme test

- Added real Apply Theme and Restore Original for the experimental, build-locked Fusion skin. Requires Resolve closed; user starts it manually. Guarded original backup, recognized hashes, atomic replacement and transaction journal; unknown resources are rejected. Windows elevation is requested only if a clicked operation lacks file access.
- Increased visibility of selected-node fills, selected tabs, toolbar hover and active-view borders. Only two skin definition files change; all other resource entries, icons, layouts, dimensions and red error/warning colors are preserved. Clip palettes remain unchanged.
- First patch activation and normal controls were confirmed by the user; the stronger revision needs live verification. Whole-application appearance/function coverage is not claimed.
- Packaged as `Omen-Studio-v0.74-Oxygen-Fusion-Test.zip` without proprietary skin archives; candidates are generated locally from the verified original.

## v0.73 - Oxygen Test theme preview

- Replaced Themes placeholder with an Oxygen Test concept card, responsive workspace illustration, six selectable preview states and inline compatibility details. Semantic dark-theme tokens derive from the optimized Oxygen palette; Veil appearance and clip palette data remain separate.
- Inspected Resolve 21.1.0.14 and its official installed API documentation. Fusion.fuskin contains color definitions, but activation, full-application coverage and safe functional preservation are unverified. No application theme setter was found in the installed API.
- Apply Theme and Restore Original remain disabled with a clear reason. Direct backend calls also reject theme operations. No Resolve files/memory/preferences were changed; no restart or window activation was triggered.
- Included the token profile, resource/version inspection and honest verification scope. Full Resolve theme application remains unimplemented until a verified mechanism and transactional recovery exist.
- Packaged as `Omen-Studio-v0.73-Oxygen-Test.zip`.

## v0.72 - amranthus palette

- Removed Colorburst from the visible library and bundled HEX files. Replaced it with amranthus, named exactly as requested, optimized from the uploaded lovely-amaranthus-16.hex. The other 14 palettes remain byte-for-byte identical at the record level.
- Applied the accepted Console/native Resolve lightness and chroma profile, broadened one redundant dark purple to Deep Lagoon, and verified all 120 color pairs at nine gradient positions with minimum Oklab separation above 0.075. Preserved source slot order and embedded expressive color names in its HEX file.
- Backed up the prior library and audit, retained original source bytes and optimization report, and verified exact HEX round-trip plus library/menu loading in Dark and Light. UI and Resolve implementation unchanged; no live Resolve operations tested.
- Packaged as `Omen-Studio-v0.72-Amranthus.zip`.

## v0.71 - distinct palette identities

- Reviewed all 15 optimized palettes, broadened redundant hue families, and separated close colors through restrained lightness/chroma adjustments. Pastel Horizon replaces Lavender Haze with Ochre Glow, Lilac Glow with Sage Mist, and Blush Cloud with Cloud Blue; Iris Bloom and Violet Dusk remain its two violet accents. Other palettes retain their character while gaining clearer identity.
- Checked all 120 pairs per palette at nine positions across each shade-to-base gradient. Every revised palette exceeds a minimum Euclidean Oklab distance of 0.075 at matching gradient positions. This design threshold does not guarantee universal perception, color-vision accessibility, or live Resolve comfort.
- Retained all 16 slots in order, updated matching embedded color names, supplied the 15 named HEX files and detailed before/after audit, and backed up v0.70's library. App UI and Resolve behavior are unchanged.
- Verified importer/exporter round-trips and all 15 palettes loading with exact colors/names in Dark and Light. Live Resolve operations were not exercised.
- Packaged as `Omen-Studio-v0.71-Distinct-Palettes.zip`.

## v0.70 - replace library with optimized palettes

- Replaced the entire visible saved library with the 14 newly optimized named HEX palettes plus the previously accepted Console, now displayed as Console. Exactly 15 palettes: Arcade, Retrobubble, Console, VHS, Pastel Horizon, Woodspark, Dawnbringer, Bubblegum, Colorburst, Retrocal, Peachy Pop, Afterhours, Flowers, Oxygen and Bloom.
- Preserved every optimized base RGB value, embedded color name and display order. Console retains the exact approved 16 RGB values. The HEX importer derives the darker endpoint using its established behavior.
- Backed up the prior installed library byte-for-byte in `Backup/previous-library-v0.69.json`. Included the 15 named HEX files and retained the current appearance preference. Old visible entries are absent; internal Resolve defaults remain for restoration.
- Verified exact record count and source data, all 15 Library cards and Editor menu entries in Dark/Light, and every palette loading with matching color/name data. No Tk callback errors. UI, Resolve integration and launcher code unchanged; no live Resolve operations performed.
- Packaged as `Omen-Studio-v0.70-Optimized-Library.zip`.

## v0.69 - names embedded in HEX files

- HEX exports now embed each display name on its RGB line, using `RRGGBB | Color name`, plus a palette-name comment header. HEX imports preserve those names and the palette title automatically. Existing plain 16-color HEX files remain supported.
- Kept base RGB values and display order unchanged. Named HEX stores one RGB endpoint per color; JSON continues retaining both gradient endpoints. Added validation for blank/duplicate names, malformed colors, wrong counts and palette-header injection; export remains atomic.
- Every library palette round-trips title, display names, base RGB values and order. Verified legacy HEX inputs, Unicode/BOM handling, invalid-file rejection, unchanged library data and original action handlers through Tk click bindings in isolated QA storage. No live Resolve operations performed.
- Included Console Optimized Experimental as a named HEX example. Packaged as `Omen-Studio-v0.69-Named-Hex.zip`.

## v0.68 - Console Optimized Experimental

- Added Console Optimized Experimental from the supplied .hex file, with all 16 custom color names from its accompanying key. Verified every source color and key name maps to the correct displayed slot, and the saved palette reloads correctly.
- All other library records preserved; Colorburst remains removed. UI, Resolve integration and launcher implementation unchanged. Packaged as `Omen-Studio-v0.68-Console-Optimized.zip`.

## v0.67 - remove Colorburst

- Removed Colorburst from the saved library. Verified that the library reloads without Colorburst and every remaining palette retains identical data. UI, Resolve integration and launcher implementation unchanged.
- Packaged as `Omen-Studio-v0.67-Remove-Colorburst.zip`.

## v0.66 - Bloom and Console palettes

- Added Bloom and Console from the user's bloom.hex and console.hex files using the existing 16-color importer. Preserved source color order and exact primary/base RGB values; derived the other gradient endpoint using the existing import behavior.
- Verified both files contain 16 valid hex colors, every imported base endpoint matches its source, and the saved library reloads both entries. Existing library entries and slot names preserved. UI, Resolve integration and launcher implementation unchanged.
- Packaged as `Omen-Studio-v0.66-Bloom-Console.zip`.

## v0.65 - palette names and menu finishing

- Added an Actions separator between Rename and Save. Clipped the native overlay child window to its rounded shape, removing opaque bottom corner pixels while retaining in-window menus and safe input-grab handling.
- Renamed exactly the specified saved palettes: PICO-8 to Arcade; Blank VHS Box to VHS; DawnBringer 16 to Dawnbringer; Bubblegum 16 to Bubblegum; NA16 to Earthlight; Peachy Pop 16 to Peachy Pop; PICO-DB to Afterhours; ARQ16 to Colorburst; Oxygen 16 to Oxygen. Retrobubble, Pastel Horizon, Woodspark, Retrocal and Flowers retain their names. Other collection entries remain untouched.
- Carried forward the installed v0.64 library; every palette color, slot name and value is unchanged. Updated actual saved palette keys so Library, Editor selector, saving and export use the same names.
- Verified exact mappings and preservation of all values, separator positions and native bottom-corner clipping in Dark/Light. Rechecked menu lifetime, typed field updates, palette switching and all six action handlers through Tk click bindings with isolated QA storage. Resolve integration unchanged; no live Resolve operations performed.
- Packaged as `Omen-Studio-v0.65-Palette-Names.zip`.

## v0.64 - in-window Editor dropdowns

- Replaced separate Windows popup Toplevels with rounded overlay menus drawn and raised inside Omen's existing main window. Removes separate native popup mapping/focus behavior. Menu canvas owns the local grab and handles outside clicks; keyboard navigation and focus restoration remain.
- Preserved palette selector and exact Actions order, command handlers, editing fields and aligned 4x4/inspector layout.
- Verified both menus open via widget press/release bindings and remain visible through two seconds of event-loop/chrome updates. Verified palette switching, timed entry updates, Save/Save As/Rename, JSON/.hex Export, Import, Delete cancellation/confirmation, repeated outside dismissal and navigation using isolated QA storage and mocked dialog answers only.
- Verified Dark/Light regular/compact/wide layouts and 1.25/1.5 geometry scaling. Inspected owned-window captures with both dropdowns visibly open. Resolve integration and launcher implementation unchanged; no live Resolve operations performed.
- Packaged as `Omen-Studio-v0.64-In-Window-Menus.zip`.

## v0.63 - repair dropdown input capture

- Fixed popup dismissal at the Tk Toplevel where a local grab delivers outside clicks. Previously only the Canvas handled clicks, leaving the grab active and blocking other app controls. Dismissal now releases the grab and restores focus.
- Ignore root Configure notifications that do not change the owner geometry, avoiding premature menu closure. Dismiss on actual move/resize or focus leaving the popup, and safely clean up bindings during teardown.
- Reproduced the v0.62 outside-click failure before the fix. Verified Tk widget click bindings for palette selection, normal timed field updates, Save, Save As, Rename, JSON/.hex Export, Import, Delete cancellation/confirmation, repeated menu reopening/dismissal and page navigation. File operations use isolated QA storage and mocked dialog answers, not mocked action handlers.
- Retested Dark/Light regular/compact/wide layouts, menu anchoring and keyboard navigation, equal panel geometry and 1.25/1.5 layout scaling. Resolve integration, data and launcher implementation unchanged; no live Resolve operations performed.
- Packaged as `Omen-Studio-v0.63-Menu-Repair.zip`.

## v0.62 - unified Editor and Actions menu

- Consolidated Editor buttons into Actions beside the palette selector, in exact order Rename, Save, Save As, Import, Export, Delete. Subtle separators group save/file/destructive actions. Original handlers, deletion confirmation and unsaved-change handling remain.
- Replaced both native rectangular dropdowns with rounded, neutral popup menus anchored directly below their triggers. Added keyboard navigation, Escape/outside dismissal, disabled states and focus restoration.
- Preserved 4x4 slot order and gradient previews. Inspector and palette panels share top/bottom edges and matching corner radii, with distributed inspector rows and comfortable field sizes. Narrow windows retain stacking and scrolling.
- Verified action routing using mocks, endpoint editing, popup order/anchoring/transparency/keyboard/dismissal, busy states, Dark/Light regular/compact/wide layouts and 1.25/1.5 layout scaling. Integration, no-window-switch refresh, storage and launcher unchanged. No live Resolve operations performed.
- Packaged as `Omen-Studio-v0.62-Editor-Actions.zip`.

## v0.61 - reference Editor layout

- Rebuilt the Editor around a rounded 4x4 palette panel and adjacent Color inspector. Retained gradient swatches, slot names, editable name/hex fields and both endpoint pickers; added clickable endpoint color chips.
- Moved Delete immediately left of Save, with Save as preceding it. Centered Import/Export below the inspector at the height of the last palette row's swatches. Narrow windows stack the inspector below the grid and scroll the complete Editor.
- Verified controls and command bindings, 16-slot order, endpoint updates, selector menu, action alignment, Dark/Light at 900/1220/1600 widths and 1.25/1.5 layout scaling. Resolve integration, no-window-switch refresh, storage and launcher source unchanged. No live Resolve operations performed.
- Packaged as `Omen-Studio-v0.61-Editor-Layout.zip`.

## v0.60 - aligned Dashboard and simpler Settings

- Removed Coming soon from the Dashboard Themes card. Palettes and Themes headings, descriptions and entry buttons now share matching vertical positions and consistent text alignment. Themes remains a preview page without working Resolve theme controls.
- Removed Settings About heading and its version/company description. Appearance and expandable compatibility/recovery controls remain. Dynamic version remains in the splash.
- Verified card heading/description/button positions in Dark/Light at 900/1220/1600 widths, both Dashboard entry actions, absence of Settings About/version-company copy, and expandable diagnostics. Integration, refresh, storage and launcher unchanged.
- Packaged as `Omen-Studio-v0.60-Dashboard-Alignment.zip`.

## v0.59 - consistent button colors after clicking

- Removed persistent focus tint from controls configured without outlines. Apply Palette and Restore Defaults now share the same resting background even when one retains focus after clicking. Shared hover and disabled treatments remain consistent.
- Verified rendered button background pixels match despite different focused states, matched hover/disabled states in Dark/Light and no underline/outline added. Integration, no-window-switch refresh, data and launcher unchanged.
- Packaged as `Omen-Studio-v0.59-Consistent-Buttons.zip`.

## v0.58 - remove underline focus styling

- Removed underline rendering from shared button code, including Apply Palette, Restore Defaults and the Dashboard connection control. No button text becomes underlined on focus. Controls without outlines use a subtle surface change for focus; other existing outlines remain as configured.
- Recorded the design preference: do not introduce underlined UI text unless explicitly requested. Removed obsolete mouse-focus tracking.
- Verified button fonts across Dashboard, Library, Editor, Themes and Settings in Dark/Light, no underline configuration in application Python, and unchanged integration, no-window-switch refresh, data and launcher.
- Packaged as `Omen-Studio-v0.58-No-Underlines.zip`.

## v0.57 - no window switching during Apply or Restore

- Removed automatic foreground activation/restoration from Resolve repaint entirely. Apply and Restore write their palette changes immediately and queue a non-activating, asynchronous background redraw. Omen stays in place; no z-order, hide, minimize or resize calls occur.
- If Resolve is behind Omen, defer the guarded Media Pool cache click until the user naturally returns to Resolve. Connection polling schedules that pending refresh only while Resolve is foreground. Recheck focus and blank-area ownership before any click. A user's switch away during discovery cancels/defer the click.
- Mocked Windows regressions verify no activation APIs, background-only redraw and deferred/safe refresh behavior. Owned Tk UI tests exercise Apply and Restore through workers and polling, confirm responsive event handling, unchanged Omen window geometry/state and cache refresh only after simulated natural Resolve focus. No live Resolve operations performed; live repaint behavior still requires confirmation.
- Palette writes, rollback, UI styling, data, recovery and launcher unchanged. Packaged as `Omen-Studio-v0.57-No-Window-Switch.zip`.

## v0.56 - keep Omen visible after Apply

- Preserve the foreground window around the guarded Resolve repaint. After briefly exposing Resolve, return focus to the previous visible, non-minimized window on success or refresh failure. No minimize, hide, resize or maximize calls are made. Respect user focus changes and intentional minimization during the refresh.
- Removed focus outlines from Apply Palette and Restore Defaults. Mouse activation retains their neutral appearance; keyboard focus uses a text underline, matching the Dashboard connection control.
- Mocked Windows tests verify foreground restoration, failure guards and respect for changed focus/minimized windows. UI tests verify outline settings, keyboard/mouse distinction, retained controls and responsive mocked Apply/repaint; Dark/Light at 900/1220/1600 widths. Palette write/recovery/storage/launcher unchanged. Live Resolve focus behavior still requires confirmation.
- Packaged as `Omen-Studio-v0.56-Keep-Omen-Visible.zip`.

## v0.55 - matching Palette actions

- Moved Apply Palette immediately left of Restore Defaults in the Library's top-right toolbar. Both use the same neutral button treatment, font weight and height. Removed the former bottom Apply footer; Search remains left.
- Enlarged Library cards slightly and arranged them in three columns with vertical scrolling. Editor remains 4x4.
- Verified three-column card positions, scrolling to the collection bottom, placement, matching style/font/height, command bindings, filtering, Editor Delete and a responsive mocked Apply/repaint cycle. Dark/Light layouts checked at 900/1220/1600 widths. v0.54 refresh fix, integration, storage, recovery and launcher unchanged; no live Resolve operations performed.
- Packaged as `Omen-Studio-v0.55-Palette-Actions.zip`.

## v0.54 - Apply refresh order and Library toolbar

- Fixed a repaint ordering defect: refresh-point visibility/discovery previously ran before Resolve was foreground, so an overlapping Omen window could block repaint despite successful palette writes. Bring Resolve forward first, then verify/discover empty background and revalidate immediately before the guarded repaint click. Foreground denial, covered points and absent verified blank space still prevent clicks.
- Moved Search to the left and restored Restore Defaults at the upper right on the same vertical axis. Apply Palette remains centered at the bottom. Editor Delete remains available.
- Verified cached/discovered refresh ordering and failure guards using mocks. Verified an actual UI Apply call with mocked session/menu/repaint keeps Tk responsive and returns to enabled state. Checked Dark/Light layouts and toolbar/button geometry at 900/1220/1600 widths. Palette write/rollback, storage, recovery and launcher source unchanged.
- User log showed palette writes completing but Media Pool repaint repeatedly skipped. No live Resolve operations performed during verification; live visual refresh remains to be confirmed.
- Packaged as `Omen-Studio-v0.54-Apply-Refresh-Fix.zip`.

## v0.53 - Delete in Editor

- Added Delete beside Rename in the Editor toolbar, targeting the palette currently being edited. Reuses the existing deletion confirmation and storage behavior. Disabled for unsaved palettes, storage errors and busy/closing state. Library remains free of Delete.
- Verified canceled deletion leaves data unchanged, confirmed deletion removes only the chosen saved palette from QA-copy storage, unsaved editing values/names are retained as a draft, and clean deletion returns to an unsaved palette. Applied Resolve state is retained. Dark/Light layouts checked; no live Resolve operations performed.
- Integration, storage implementation, recovery and launcher unchanged. Packaged as `Omen-Studio-v0.53-Editor-Delete.zip`.

## v0.52 - centered Apply Palette

- Centered Apply Palette horizontally in the Library footer and removed Restore Defaults from that page. Existing application behavior and normal-close restoration/recovery remain unchanged.
- Verified Apply Palette center within one pixel at 900/1220/1600 widths in Dark/Light, retained selected-palette command, absent Restore Defaults, search filtering and unchanged Editor controls. Integration, storage, recovery and launcher unchanged; no live Resolve operations performed.
- Packaged as `Omen-Studio-v0.52-Centered-Apply.zip`.

## v0.51 - remove Library Delete

- Removed the Delete button from the Library. Centered Search, palette selection, Restore Defaults and Apply Palette remain unchanged. Saved palettes are preserved.
- Verified Delete remains absent after palette selection/deselection, search centering/filtering, Dark/Light at 900/1220/1600 widths and unchanged Editor controls. Integration, storage, recovery and launcher unchanged; no live Resolve operations performed.
- Packaged as `Omen-Studio-v0.51-Clean-Library.zip`.

## v0.50 - centered Library search

- Centered the Library search field horizontally beneath Library/Editor while retaining its toolbar row and vertical position. Delete remains at the left; Search label sits beside the centered field.
- Verified exact field centering at 900, 1220 and 1600 pixel window widths in Dark/Light, unchanged row height, working search filtering and retained Library/Editor controls. Integration, storage, recovery and launcher unchanged; no live Resolve operations performed.
- Packaged as `Omen-Studio-v0.50-Centered-Search.zip`.

## v0.49 - fewer Library actions

- Removed Import, Export, Edit and Rename buttons from the Palette Library. Retained Delete, Search, Restore Defaults and Apply Palette. Editor Import/Export, Rename, Save and Save as remain available.
- Verified absent Library controls, retained Delete command and selection-dependent state, Dark/Light at normal/smaller window sizes and unchanged Editor controls. Integration, storage, reconnect, recovery and launcher source unchanged; no live Resolve operations performed.
- Packaged as `Omen-Studio-v0.49-Library-Actions.zip`.

## v0.48 - persistent page selection and simpler inspector

- Keep a clicked primary page outlined independently of keyboard focus, including while changing Library/Editor tabs or appearance. Startup does not set a persistent page outline; choosing another page transfers it.
- Simplified Color inspector into a centered name field, two combined Primary/Secondary picker and editable hex rows, and the gradient preview. The labeled buttons open the existing color pickers. Removed repeated Name and Pick color labels without removing any editing functions.
- Removed the Dashboard connection button focus outline. Connection text and the red/green circle remain; keyboard focus receives a subtle text underline.
- Verified all four page transitions, startup state, tab activation, focus loss, appearance rebuilds, picker endpoint bindings, all three editing variables, Dark/Light normal and compact layouts, and absence of Tk callback errors. Integration, storage, reconnect, recovery and launcher source unchanged. No live Resolve operations performed.
- Packaged as `Omen-Studio-v0.48-Persistent-Page-Selection.zip`.

## v0.47 - centered color inspector

- Renamed Left endpoint and Right endpoint to Primary and Secondary, preserving both stored values and their order. Removed Clip preview text while keeping the gradient pill.
- Centered the inspector heading, field labels and editable text. Balanced compact-layout margins and control spacing, and hide the validation area when there is no error.
- Verified labels, centered alignment, retained 4x4 grid and command bindings, and Dark/Light layouts at normal and smaller window sizes. Resolve integration, storage, recovery and launcher unchanged; no live Resolve operations performed.
- Packaged as `Omen-Studio-v0.47-Inspector-Labels.zip`.

## v0.46 - 4x4 palette Editor

- Arranged the Editor's 16 existing slots in four columns and four rows, preserving Resolve slot order and all color/name values. The inspector stays alongside at normal width and retains its existing compact layout at smaller sizes.
- Verified all 16 grid positions, normal/smaller Dark/Light layouts and retained Editor/Library controls. Integration, reconnect, recovery, data and launcher unchanged. No live Resolve operations performed.
- Packaged as `Omen-Studio-v0.46-Four-Column-Editor.zip`.

## v0.45 - simplified Editor actions and clean preview

- Kept Save and Save as at the Editor's upper right, using lowercase as. Moved Editor Import and Export together to the bottom left and removed Editor Apply Palette and Restore Defaults buttons. Library Apply/Restore and its file actions remain available.
- Removed Preview only text beneath the clip preview and matched the pill canvas background to the inspector panel, eliminating the dark rectangular corner surround.
- Verified button locations/labels, retained command bindings, Library actions, preview background/text, Dark/Light at normal/smaller sizes and unchanged integration/reconnect/recovery/storage/launcher. No live Resolve session accessed.
- Packaged as `Omen-Studio-v0.45-Editor-Toolbar.zip`.

## v0.44 - reconnect after Resolve restarts and stable connection button

- Fixed a session-lifetime bug: a failed compatibility check previously stopped all polling, leaving a stale session and disabled Connect after Resolve exited. Failed sessions now receive process-liveness checks only, without continuing memory validation. Once the process exits, its handle/menu reference, failure flags and applied snapshot are cleared, pending repaint is canceled and Connect becomes available for a fresh verified session.
- Added a stale callback guard so an old check cannot clear a replacement session. Normal process exit no longer produces a diagnostic error state.
- Reserved a fixed width for the longest connection label. Connect to DaVinci Resolve, Connected to DaVinci Resolve and Connecting keep the same button and indicator-group footprint.
- Verified mocked healthy/failed session exit/reconnect cycles, liveness-only checking after failure, state/handle cleanup, stale callbacks and identical button/group dimensions in Dark/Light. Existing memory writes, restoration/recovery logic, palette data and launchers unchanged. A live Resolve close/reopen/reconnect check remains required.
- Packaged as `Omen-Studio-v0.44-Reconnect.zip`.

## v0.43 - quiet Dashboard connection state

- Removed diagnostic/error text beneath the Dashboard connection button, including Dot resource changed messages. Red/green indicator and connection button remain; details are retained in Settings compatibility/recovery diagnostics and the log.
- Verified Dark/Light mocked connected/disconnected/error states, absence of Dashboard error text, retained Settings diagnostics, navigation and unchanged integration/recovery/storage/launcher. No live Resolve operations performed.
- Packaged as `Omen-Studio-v0.43-Quiet-Dashboard.zip`.

## v0.42 - Dashboard connection control and clean button corners

- Removed Your studio heading and header connection text. Added a bottom-center Dashboard control labeled Connect to DaVinci Resolve, with a red disconnected circle and green connected circle. On successful connection the button reads Connected to DaVinci Resolve and disables duplicate connection attempts; failed connection checks turn the circle red with nearby actionable feedback.
- Corrected rounded controls inside painted panels to use the panel interior color around transparent antialiased corners. This removes the rectangular corner patches on Dashboard buttons and applies consistently to fields inside panels.
- Verified Dashboard positioning, disconnected/connected/error states through mocks, Dashboard-only visibility, navigation, Dark/Light and smaller layouts, correct corner alpha and panel button backgrounds. Integration, restoration, recovery, palette files and launchers remain unchanged. Live Resolve connection behavior and other Windows display scaling settings were not exercised.
- Packaged as `Omen-Studio-v0.42-Dashboard-Connect.zip`.

## v0.41 - monochrome applied-palette outline

- Replaced the green applied-palette outline with a light silver outline in Dark mode and a dark charcoal outline in Light mode. The neutral gray full-card selection fill remains separate and toggles off independently.
- Verified Dark/Light appearance and selection toggles retaining the applied outline; unchanged restoration, integration, palette data and launcher. No live Resolve session accessed.
- Packaged as `Omen-Studio-v0.41-Monochrome-Active.zip`.

## v0.40 - bundled DM Sans typography

- Applied DM Sans to application labels, fields, buttons, navigation, palette selectors, inspector and dynamic splash version text. Regular handles body and controls, Medium navigation, Semibold palette names and primary actions, and Bold larger headings.
- Bundled the supplied Regular, Medium, Semibold and Bold files; loaded privately for this process without installing Windows fonts. Included the DM Sans SIL Open Font License. Existing splash artwork and native Windows title-bar/dialog typography remain unchanged.
- Verified registered families and actual rendered widget font families, Dark/Light views of Dashboard, Library, Editor, Themes and Settings, plus a smaller Editor window. Resolve integration, worker, recovery, palette data and launchers unchanged. No live Resolve operations or other Windows scaling settings exercised.
- Packaged as `Omen-Studio-v0.40-DM-Sans.zip`.

## v0.39 - centered contextual tabs and Dashboard connection

- Centered Library | Editor within the contextual toolbar.
- Restricted Resolve connection status and Connect controls to Dashboard. Other pages keep clean centered primary navigation. Connection state continues updating while the controls are hidden.
- Verified Dark/Light at normal and smaller sizes, centered primary/contextual navigation, page switching, Dashboard-only visibility and mocked connected/disconnected controls. Resolve integration, restoration, recovery, storage and launchers unchanged; no live Resolve session accessed.
- Packaged as `Omen-Studio-v0.39-Centered-Tabs.zip`.

## v0.38 - toggle selection and user-palette collection

- Clicking or keyboard-activating a selected card again deselects it and removes the whole-card gray highlight. Selection-dependent actions disable when no card is selected. Deselecting does not alter the applied palette or its green outline.
- Removed Resolve Original, Vivid and Soft from the Library and Editor palette selector. Restore Defaults retains the internal stock color data and the existing restoration path; it remains the way to return Resolve to its original appearance.
- Initialized the Editor from a saved palette rather than a removed built-in. Empty collections show an import prompt and retain import/restore access.
- Verified repeated selection toggles, disabled actions, independent applied outline, Dark/Light, absence of built-ins in both selection surfaces, navigation persistence and empty collection handling. Resolve integration, restoration, recovery, launcher and saved palette files are unchanged. No live Resolve operations were performed.
- Packaged as `Omen-Studio-v0.38-Library-Toggle.zip`.

## v0.37 - whole-card palette selection

- Expanded palette selection to the full rounded card, including its background, padding, name and color preview. All card surfaces use the selection cursor and select the same saved palette.
- Moved neutral selection highlighting from the small preview block to the entire card. The green applied-palette outline remains independent and can coexist with the selection fill. Keyboard focus retains a separate visible ring.
- Verified clicks across background corners, padding, name and preview in Dark/Light; one selected card at a time; independent applied outline; keyboard Enter and selection persistence across contextual navigation. Resolve integration, recovery, palette data and launcher unchanged. No live Resolve session accessed.
- Packaged as `Omen-Studio-v0.37-Card-Selection.zip`.

## v0.36 - segmented workspace header

- Partitioned the header with quiet one-pixel horizontal rules, short vertical dividers between primary pages, and a separate Resolve connection group on the right.
- Placed Library and Editor in a distinct contextual toolbar with a complementary neutral surface and its own boundary. The contextual toolbar is hidden on Dashboard, Themes and Settings.
- Kept centered primary navigation, readable selection/focus states, seamless native title bar and compact wide-window content. Narrow layouts wrap navigation instead of overlapping connection controls.
- Verified Dark/Light screenshots at 900, 1220 and 1900 pixels, centered navigation and no overlap, page and contextual-tab actions, version-free title, and unchanged Resolve integration, recovery, storage and launchers. No live Resolve operations were run.
- Packaged as `Omen-Studio-v0.36-Segmented-Header.zip`.

## v0.35 - seamless title bar and compact wide-window layout

- Removed the duplicate logo and product name from the navigation header. The native Windows title bar retains the application icon and now shows only Veil, without a version number. About and the startup splash retain the dynamic version.
- Applied native Windows dark-mode caption, background, text and border colors to match Veil appearance. Standard minimize, maximize, close, resizing and taskbar behavior remain native. Older Windows builds fall back to supported native dark-mode caption attributes.
- Centered the workspace with a maximum width of 1200 logical pixels. Maximizing provides space around the content instead of widening palette cards indefinitely; typography, card height and swatch proportions remain stable.
- Verified Dark/Light title bar and wide-window screenshots, window title, absence of duplicate branding, compact card widths at 1220 and 1900 pixels, maximize/restore and page navigation. Native caption setters returned success; Windows does not expose custom color readback through DwmGetWindowAttribute in this environment, so visual inspection verified the result. Resolve operations, recovery, launchers and saved palette data are unchanged. No live Resolve changes were made.
- Packaged as `Omen-Studio-v0.35-Compact-Window.zip`.

## v0.34 - centered navigation and palette file actions

- Centered Dashboard, Palettes, Themes and Settings in the header. Branding stays left and Resolve status stays right; compact headers move navigation to a centered second row when necessary.
- Moved Library Import and Export together to the bottom left. Search stays at the upper right and follows the right edge of the palette cards as the scrollbar appears or the window resizes.
- Added plain .hex export in both Library and Editor: 16 right-endpoint RGB values, one per line in Resolve display order. This format cannot retain custom names or both endpoint values; JSON remains the lossless palette format. File output is replaced atomically.
- Verified Dark/Light at normal and smaller sizes, header centering, navigation membership, action placement, search alignment, .hex slot order and base-color import roundtrip, JSON roundtrip, and both export dialogs. Resolve integration, recovery, launcher and palette data are unchanged. Live Resolve and other Windows display scaling settings were not exercised.
- Packaged as `Omen-Studio-v0.34-Workspace-Actions.zip`.

## v0.33 � clean Library and modern scrolling

- Removed the Library heading, selected-name text and all card metadata labels. Collection actions share one compact toolbar with search and import.
- Added a persistent green rounded outline around the successfully applied saved palette. Selecting another palette uses a separate neutral preview highlight. Failed application leaves the previous applied outline; successful restoration highlights Resolve Original. Unsaved editor changes remain indicated beside its toolbar.
- Replaced the native rectangular scrollbars with slim rounded grayscale gradient thumbs throughout the workspace, with dragging, paging, keyboard navigation and automatic hiding. Selecting a Library card no longer rebuilds the collection or resets its scroll position.
- Verified Dark/Light and smaller window renders, card state transitions through mocked Apply/failure/Restore callbacks, scrollbar dragging/endpoints/Home and hiding. Resolve integration, launcher, recovery and saved palette data are byte-for-byte unchanged from v0.32. Live Resolve verification remains pending.
- Packaged as `Omen-Studio-v0.33-Clean-Library.zip`.

## v0.32 — stable latest-release launcher and silent startup

- Added Veil.vbs as the normal GUI entry. It runs runtime discovery hidden, then uses the existing pythonw / CREATE_NO_WINDOW startup path. Only the splash and app should appear; Check Connection.cmd remains an intentional console diagnostic. Startup errors are written to launcher-error.txt and shown in a short dialog.
- Taskbar relaunch now targets an Omen-Studio-Launcher folder outside numbered releases. The router selects the highest complete release by its numeric studio_version.py value among sibling Omen-Studio-v* folders, ignoring incomplete builds. Future numbered releases extracted alongside existing folders use the same pin. App identity is retained for existing taskbar grouping.
- Repaired the local Windows grouped Omen/O2 shortcut targets and relaunch properties with backups kept in the v0.32 working directory. Created a stable Veil.lnk for repinning if Windows retains cached shortcut data. Other applications' pins were not changed.
- Verified VBScript command parsing, numeric ordering including future v0.100, incomplete-build rejection, console-suppression subprocess flags, stable taskbar relaunch data, and unchanged Resolve integration / recovery / palette files. Actual Explorer pin-cache refresh and splash-only launch require the user's desktop check. Archived as `Omen-Studio-v0.32-Silent-Launcher.zip`.

## v0.31 — Dark and Light appearance only

- Removed Follow system from Settings. New installations default to Dark; Dark and Light remain remembered choices. Existing Follow system preferences migrate once to the current Windows appearance and persist as a fixed mode. Removed periodic system-appearance switching; corrupt preferences fall back to Dark without overwriting the damaged file.
- Updated shared version, instructions and changelog. Palette data, Resolve operations and recovery behavior are unchanged. Archived as `Omen-Studio-v0.31-Appearance.zip`.

## v0.30 — cleaner palette workspace

- Removed the bottom Selected / Editing / Applied summary and the persistent bottom operation/technical-message line. Library Editing / Unsaved / Applied card badges and the header connection indicator remain. The latest operation details are accessible in Settings' expandable diagnostics and existing logs.
- Shortened Restore Resolve Defaults to Restore Defaults and matched its control height to Apply Palette, retaining text-sized width and secondary styling. Updated the shared release version, instructions, changelog and verification. Resolve operations and recovery behavior are unchanged. Archived as `Omen-Studio-v0.30-Clean-Workspace.zip`.

## v0.29 — monochrome modular workspace redesign

- Replaced the sidebar and global palette footer with an understated horizontal Veil brand/header, Dashboard / Palettes / Themes navigation, a single Resolve connection indicator and separate Settings. Library / Editor tabs appear only within Palettes. Branding stays beside the preserved silver logo.
- Added coordinated neutral-charcoal and light-gray tokens, shared rounded buttons/inputs/panels, keyboard focus states and smooth antialiased gradient pills. Dashboard has two module tiles with palette and grayscale interface previews; Themes remains coming soon. Settings remembers appearance and exposes About plus expandable compatibility/recovery/diagnostic information.
- Library cards select a palette without disturbing the editor draft; one shared toolbar provides Edit, Rename, Export and Delete. Inline Rename is prepopulated, confirms with Enter, cancels with Escape, validates empty/conflicting names, atomically updates saved names/metadata and preserves colors, custom slot names and dirty editing state. Built-in Rename creates a copy.
- Editor has a compact palette selector, Save / Save As / Import / Export toolbar, 16 gradient-pill slots without slot numbers, and a contextual endpoint inspector. Both underlying shades and slot identities are preserved. On narrower windows the inspector moves below the grid with horizontal endpoint controls. Apply Palette and Restore Resolve Defaults are available only within Palettes; Save and Apply remain separate, and editing/applied states are distinguished.
- Kept the v0.27 serialized Resolve worker, memory integration and recovery modules byte-identical. Fixed an inherited import-name shadowing bug that could name a draft after its last slot alias. Retained splash, logo assets and dynamic version.
- Visually inspected Dashboard, Library, Editor, Themes and Settings in both appearances. Checked text contrast, 900 / 1220 layouts, simulated 100–200% scaling, rename/copy validation, dirty-state preservation, saving/import/export, gradient interpolation, keyboard navigation and simulated Apply/Restore/normal close. Live Resolve writes, process recovery and actual multi-monitor DPI transitions remain manual checks. Archived as `Omen-Studio-v0.29-Workspace.zip`.

## v0.28 — centered palette-card status and actions

- Centered the Library status text and the complete Edit palette / Apply palette / Delete button group horizontally within each card. Replaced the Saved card label with Imported; Built-in, Editing, Unsaved, and Applied indicators retain their existing behavior.
- Updated the shared release version, changelog, and instructions. Verified centered alignment and readable button labels in dark and light modes at small and normal window widths and simulated 100–200% display scaling. Resolve integration, background worker, and palette data are unchanged. Archived as `Omen-Studio-v0.28-Centered-Cards.zip`.

## v0.27 — responsive palette application and compact Library actions

- Moved Apply, Restore, periodic connection/resource checks, and Media Pool repaint work off Tk's interface thread into one serialized background worker. Tk variables and widgets are updated only on the main thread. Busy actions reject repeated clicks; pending writes wait for background checks and are refused if the connection changes.
- Reused the existing Apply transaction and menu-name rollback. Kept native memory patching and recovery modules unchanged. Normal close waits for outstanding work, pauses background checks during confirmation dialogs, then runs the existing restoration path. Exit cleanup waits for worker completion before touching Resolve handles; successful close cancels periodic callbacks.
- Limited automatic Media Pool background-point discovery to 400 ms. A timed-out search skips the repaint and reports the reason without weakening point validation. Operation durations and full errors are logged for investigating remaining delays.
- Put Edit palette, Apply palette, and Delete together in a smaller action row. Centered palette names, and adjusted responsive card widths to keep labels readable. Removed the redundant footer Apply Palette button; save editor changes before applying from a Library card. Checked both appearance modes, simulated 100–200% scaling, delayed operations, repeated clicks, failure rollback, connection drift, cancelled close, and close during Apply. Live Resolve validation remains required. Updated version and documentation; archived as `Omen-Studio-v0.27-Responsive-Apply.zip`.

## v0.26 — hex palette import and readable Delete label

- Added .hex import: exactly 16 RGB colors, one per line, in Resolve's display slot order. Accepts optional # prefixes, mixed case, blank lines, surrounding whitespace, and UTF-8 BOM. Invalid lines and wrong counts are rejected before replacing the editor draft.
- Imported hex palettes use the filename as their draft name and editable Slot 1–16 names. Shade 2 keeps each supplied RGB value; Shade 1 uses the existing 0.76 darker-shade formula. Import does not save or apply automatically. JSON import/export and stored palette schemas remain compatible.
- Removed the undersized fixed width from Library Delete buttons so the complete label and padding fit. Verified both appearance modes, small and normal windows, and simulated 100–200% display scaling. Resolve integration and bundled palette data are unchanged. Updated shared version, instructions, and verification report. Archived as `Omen-Studio-v0.26-Hex-Import.zip`.

## v0.25 — delete saved palettes

- Removed Preset 1 from the bundled palette library. Added a quiet Delete button on user-saved Library cards with a confirmation dialog; Resolve Original, Vivid, and Soft remain protected built-ins.
- Deletion atomically updates the saved library and custom-name metadata. If the deleted palette has unsaved editor changes, those changes remain as an unsaved draft. A clean selected palette returns the editor to Resolve Original.
- Deleting a saved palette does not apply or restore any colors in Resolve. The active snapshot remains available on Home until another palette is applied or defaults are restored. Updated the shared release label and instructions. Archived as `Omen-Studio-v0.25-Palette-Delete.zip`.

## v0.24 — apply palettes from Library cards

- Added Apply palette next to Edit palette on every Library card. The card action applies that saved palette's colors and names directly, while preserving the selected editor palette and any unsaved draft.
- Card Apply buttons follow the connection, busy and compatibility states. Applied badges update immediately after applying or restoring. Adjusted responsive card widths to keep the two actions readable.
- Reused the existing verified apply transaction and rollback behavior. The footer Apply Palette continues to apply the editor draft. Updated the shared release label, instructions, and verification report. Archived as `Omen-Studio-v0.24-Library-Apply.zip`.

## v0.23 — modular interface redesign

- Rebuilt the Tkinter interface with a persistent Home / Palettes / Themes / Settings sidebar, a compact connection indicator, neutral rounded surfaces, readable Segoe UI typography, and a small creative dashboard. Themes has a Coming soon page; a shared page registry supports future modules.
- Added remembered Dark, Light, and Follow system appearance settings for Veil. These settings are separate from future Resolve themes. Text and status colors were checked for at least 4.5:1 contrast, including text over the supplied palettes.
- Added a searchable palette-card Library and an Editor with the 16 existing slots, a focused name / Shade 1 / Shade 2 editing panel, editable hex values, color pickers, and an illustrative clip preview. Saving, editing and applying now have separate states. Unsaved drafts prompt before replacement or closing; restoring Resolve defaults keeps the editor draft.
- Retained schema 1 / 2 palette compatibility, custom names, both shades, import/export, and the v0.22 Resolve actions. Seven connection/apply/restore/poll/close action methods were moved without changing their logic; backend memory and recovery modules are unchanged. The silver logo and three-second rounded splash are retained, with a shared dynamic v0.23 release label.
- Verified both appearance modes and all pages in an isolated Tk preview; storage/file workflows, validation, keyboard navigation, a 900 × 640 layout, and simulated 100–200% scaling passed. Simulated Apply/Restore, failed-apply name rollback, fingerprint-drift disabling, open-menu close protection, and normal-close restoration passed. Live Resolve behavior and actual multi-monitor DPI transitions remain manual checks. Archived as `Omen-Studio-v0.23-Interface.zip`.

## v0.22 — slightly larger taskbar logo

- Increased the silver logo's coverage within the Windows icon by reducing transparent padding. The common 32 px icon now uses a 31 px wide logo instead of 28 px, a roughly 11% increase, with the original proportions and transparency retained.
- Updated the taskbar icon resource and app identity so Windows can show the enlarged icon after repinning. The splash and window now display v0.22. Archived as `Omen-Studio-v0.22-Icon-Size.zip`.

## v0.21 — smaller splash and cleaner taskbar icon

- Removed the added dark outline from every small Windows icon size. Rebuilt the transparent icons from the supplied silver logo and updated the taskbar resource and identity to avoid the older cached image.
- Reduced the centered splash to a maximum of 960 × 409 pixels, preserving the artwork's approximately 2.35:1 ratio. Smaller screens use 800 or 640 pixel variants. The native splash window now has rounded corners that clip stray background pixels.
- Kept the three-second startup display and dynamic release label; this release shows v0.21. Palette behavior is unchanged. Archived as `Omen-Studio-v0.21-Visual-Polish.zip`.

## v0.20 — startup splash and silver logo

- Added a centered splash using the supplied Veil artwork. It stays up for three seconds before the main window opens; connection checks skip it.
- Removed the fixed v0.19 text from the splash artwork and draw the release number from the app's VERSION value, so each new release can display its own number.
- Replaced the app header, window, and taskbar icon with the supplied transparent silver O2 logo. Updated the Windows icon resource and app identity to avoid reusing the older cached pin. Palette behavior is unchanged from v0.19. Archived as `Omen-Studio-v0.20-Splash.zip`.

## v0.19 — Veil name and chrome logo

- Renamed the visible app, window title, taskbar pin, launcher, package folder, instructions, and diagnostic messages from O2 Switcher to **Veil**. Internal palette storage and the session lock remain compatible with earlier builds.
- Replaced the previous black icon with the supplied chrome O2 logo. Removed its opaque black background, including the openings inside the mark, and bundled the transparent high-resolution source, multi-size Windows icon, and in-app header image.
- Gave the renamed app a distinct Windows taskbar identity and icon resource so it does not inherit an older pinned O2 Switcher image. Palette switching behavior is unchanged from v0.18. Static branding, icon-transparency, and Windows pin-property checks pass; visual behavior on the user's desktop remains to be checked. Archived as `Omen-Studio-v0.19.zip`.

## v0.18 — Refresh the transparent Windows icon

- Kept v0.17's fully transparent, antialiased Omen 2 artwork. GDI+ loaded the 16, 24, 32, and 48 px ICO images with transparent corners, confirming the file itself contains no white tile.
- Gave the ICO/PNG new filenames and assigned a new Windows AppUserModelID so a taskbar pin cannot reuse v0.16's cached white-tile resource. The O2 Switcher display name and relaunch command remain the same.
- This addresses the report that a white background still appeared after v0.17. The actual taskbar appearance remains to be checked after unpinning the older O2 icon and pinning the newly running v0.18 window. Archived as `O2-Switcher-v0.18-Transparent-Icon-Refresh.zip`.

## v0.17 — Transparent, smoother small icon

- Removed the white tile from the Omen 2 window and taskbar icon. Every ICO size now has a transparent background.
- Rebuilt the 16–48 px icon images directly from the original logo with antialiased, lightly sharpened edges instead of the hard pixel cutoff used in v0.16. Kept the 64–256 px images individually sized as well.
- Kept v0.16's O2 Switcher taskbar pin name, icon-resource, and relaunch settings unchanged. Palette behavior is unchanged. Icon files and Python source passed offline checks; visual taskbar confirmation is pending. Archived as `O2-Switcher-v0.17-Transparent-Icon.zip`.

## v0.16 — Crisp taskbar icon and O2 Switcher pin identity

- Rebuilt the company icon from the supplied Omen 2 logo with individually rendered 16–256 px images. The small taskbar sizes use hard-edged pixels instead of scaling down the 256 px PNG, and Windows now uses the multi-size ICO directly.
- Added Windows window-level AppUserModel properties for the relaunch command, icon, display name **O2 Switcher**, and app ID. This addresses the pinned shortcut reverting to Python's icon and name while keeping the existing Python launcher and palette behavior.
- Verified the four taskbar properties by writing and reading them on a temporary native Windows window, verified the ICO sizes, and compiled the changed source. The actual pin-and-relaunch behavior still needs a visual test on the user's desktop. Archived as `O2-Switcher-v0.16-Crisp-Icon-Taskbar-Pin.zip`.

## v0.15 — Omen 2 company icon

- Replaced the default Python feather in O2 Switcher's window and Windows taskbar with an icon made from the supplied Omen 2 black logo. A white tile keeps the black mark visible on light and dark taskbars.
- Added a Windows app identity and bundled PNG/ICO icon assets. Palette switching and Media Pool refresh behavior are unchanged from v0.14.
- Confirmed the icon assets and source compile offline. The taskbar appearance still needs a visual check after closing and reopening O2 Switcher. Archived as `O2-Switcher-v0.15-Company-Icon.zip`.

## v0.14 — Automatic Media Pool refresh without setup

- Removed v0.13's Set Media Pool refresh point button. O2 now searches the upper-left Media Pool area for a broad, uniform dark background point, validates that it belongs to Resolve, and saves it for subsequent palette changes. A moved or resized window triggers a fresh search. If no verified point is visible, it skips the synthetic click and reports the reason.
- Preserved the bounded repaint mechanism proven by the live probe: foreground Resolve, then post a blank-area click without moving the physical pointer or changing clip-color assignments. The user reported no unwanted visible action in that probe.
- The v0.13 live attempt switched palettes but had not completed calibration when the user first checked the dots. Calibration later succeeded. Its log also recorded an unrelated native dot-image change warning in that Resolve session, so a fresh Resolve session is required for a clean v0.14 test.
- Offline auto-discovery, guard, and click-order tests pass. The user later reported that v0.14 worked mostly well, with occasional Media Pool dots still requiring a repaint. Archived as `O2-Switcher-v0.14-Auto-Media-Pool-Refresh.zip`.

## v0.13 — Automatic Media Pool repaint preview

- Added an optional Set Media Pool refresh point button. The user calibrates a uniform dark blank area once; O2 saves its client coordinate, window size, and surrounding pixels for later sessions.
- After applying or restoring a palette, and after O2 detects a newly loaded thumbnail marker, it verifies the saved point still belongs to the same Resolve window and background, then requests a repaint with a synthetic blank-area click. The physical pointer does not move. If the layout changed or O2 covers the point, it skips the click and reports why.
- A timed live probe showed slot-2 Wine Circuit stayed visible through ten seconds of observation, synthetic hover, and foreground activation. A synthetic blank-area click then repainted the dot as Slatewave. The user reported no unwanted visible action.
- Added guard and event-order tests. The integrated v0.13 app still requires a live check in a disposable project, including calibration, switching, restore, and an altered-layout guard.
- Archived as `O2-Switcher-v0.13-Media-Pool-Refresh.zip`.

## v0.12 — Faster Media Pool dot detection preview

- Shortened the connection and thumbnail-resource check interval from two seconds to half a second. This should reduce the wait before O2 recolors a newly loaded Media Pool dot; Resolve may still delay repainting an existing visible thumbnail.
- The successful all-slot mapping and restoration behavior from v0.11 is unchanged. No cursor movement or temporary clip-color reassignment is used.
- A read-only synthetic-hover probe was inconclusive: in the valid calibration run, the slot-2 dot had already changed from Console16 Wine Circuit to Retrobubble Slatewave before the event. A temporary Apricot→Orange→Apricot assignment did refresh Slatewave but visibly flashed Orange, so it was not included.
- Pending live test of responsiveness and restoration. Archived as `O2-Switcher-v0.12-Faster-Media-Pool.zip`.

## v0.11 — Media-pool markers across all slots

- Fixed the v0.10 refresh stop that left newly selected Media Pool colors at Resolve's original dots. Resolve changed nonstructural image metadata after the initial Orange marker update; O2 had treated that as a new allocation and disabled its periodic refresh.
- The ownership check now verifies the resource, image object, pixel-buffer pointer, dimensions, format, stride, and expected pixels/keys while allowing Qt's unrelated metadata to change during painting. A true buffer or layout change still stops writes.
- Newly loaded markers, including Apricot in slot 2, are picked up on O2's next connection check and recolored from their verified stock pixels to the active palette's matching slot. Simulated tests passed for all 16 colors, metadata changes, pointer guards, lazy loading, rollback, and restoration.
- The integrated fix still needs a live test. Restart Resolve before using this build if v0.10 reported a thumbnail error.
- Archived as `O2-Switcher-v0.11-Media-Pool-Fix.zip`.

## v0.10 — Media-pool thumbnail dot preview

- Added palette switching for the separate 11×12 clip-color markers shown on Media Pool thumbnails. Slot 1's Orange marker now follows the active slot-1 color, such as Retrobubble's Mistglass, while the clip retains its native slot assignment.
- New marker resources loaded while O2 is open are detected during the regular connection check and recolored to the active palette. This may take up to about two seconds after a newly colored clip appears.
- Derived exact Qt pixel signatures for all 16 embedded marker images and confirmed the live Orange and Navy buffers match. Any other marker must match its signature before O2 changes it. Updates preserve edge shading and transparency and journal the original pixels and image keys before writing. Restore Defaults and normal close restore these marker resources alongside the timeline, menu dots, and names.
- A bounded Orange-to-Mistglass preview visibly worked for the user and its report verified exact pixel and image-key restoration. Simulated tests passed for switching, late resource loading, restoration, rollback, and coordinator failures. The integrated v0.10 app still needs its first live user test.
- The integrated v0.10 test found a false allocation-change warning after Resolve updated image metadata. O2 then stopped polling for new media-pool markers, leaving slots other than the initially loaded Orange marker at their stock colors. v0.11 addresses this.
- Archived as `O2-Switcher-v0.10-Media-Pool-Preview.zip`.

## v0.9 — Partner package

- Packaged the v0.8 slot-6 audio and slot-9 video switching code without changing its behavior; updated only the version label and partner-facing instructions.
- Included all 16 supplied custom palettes, connection check, first-run checklist, setup and recovery guidance, and the complete changelog in a clean ZIP.
- The user reported the combined v0.8 test worked perfectly on the original Resolve machine. The partner's machine still needs its own first-run check against the exact supported build.
- Archived as `O2-Switcher-v0.9-Partner-Package.zip`.

## v0.8 — Unassigned audio and video defaults preview

- Combined default-fill switching: unassigned audio Green follows menu slot 6 (internal ID 0), and unassigned video Blue follows menu slot 9 (internal ID 2). Both clips retain empty color labels while the palette changes.
- A bounded audio-source preview visibly changed the unassigned Green fill for the user. Its report verifies five audio clips remained unassigned and both original Green instructions were restored; the separate manual recovery log also verified stock bytes.
- Added exact audio/video callsite and class checks, a four-instruction recovery transaction, and simulated switching, rollback, restoration, and coordinator tests. The user later reported the combined v0.8 test worked perfectly.
- Added explicit requirements for Resolve Studio 21.1.0.14, 64-bit Python 3.11+ with Tcl/Tk, and a writable extracted folder. Clarified first-run checks, slot mapping, and recovery steps.
- Preserved the user's 16 supplied saved palettes and added a partner test checklist.
- The user confirmed v0.7 switching worked and Restore Defaults returned the unassigned fill, assigned colors, menu dots, and names to their originals. This package still needs a first-run check on the partner's machine.
- Packaged a combined test preview as `O2-Switcher-v0.8-Green-and-Blue-Preview.zip`.

## v0.7 — Unassigned video fill follows slot 9

- Added the ordinary video-clip default-Blue source to palette switching. An unassigned video clip remains unassigned while its fill follows the active palette's menu slot 9 (internal Blue ID 2); both Blue shades are updated together.
- Kept assigned clips on their original slot numbers, and retained the native menu dots and custom names from v0.6.
- Added build/callsite/class checks, a recovery record before code changes, per-instruction verification, rollback, instruction-cache refresh, and code-page protection restoration.
- Incorporated independent restoration attempts so a failure in names, dots, default fill, or assigned-clip colors does not silently skip the other components.
- A bounded source preview changed the visible unassigned fill to magenta; the user observed it, and its report verifies five clips stayed unassigned and both original instructions were restored. The user later confirmed the combined v0.7 switch worked and Restore Defaults returned all checked visuals to stock.
- Added a version-specific test checklist. Simulated default-fill and transaction-coordination tests passed.
- Archived as `O2-Switcher-v0.7-Default-Video-Fill.zip`.

## v0.6 — First-frame native names

- Replaced the pointer-sweep menu refresh with a native name-lookup redirect, so palette-specific names appear on the first opening of Clip Color without hovering each row.
- Kept per-palette custom names, including longer names, alongside the 16-color palette data.
- Kept the native slot mapping stable while palettes recolor already-labeled clips.
- Added build checks and recovery/restoration for native names and palette colors.
- User confirmed the first-frame naming preview worked very well.
- Archived as `O2-Switcher-v0.6-First-Frame-Names.zip`.

## v0.5 — Cursor-sweep name refresh preview

- Applied the selected 16-color palette to clip fills and native menu dots, with custom names for each palette.
- Refreshed Resolve's menu text by briefly sweeping the real pointer across its rows when the menu opened (about 0.6 seconds in the test). The sweep did not click, but the pointer movement was visible.
- Custom names and the 15 supplied palettes plus Preset 1 were included.
- Superseded by v0.6, which removed the cursor sweep.
- Archived as `O2-Switcher-v0.5-preview.zip`.

## v0.4.1 — Faster native-menu naming preview

- Built on palette and dot switching, adding palette-specific native menu names.
- Tested faster name updates and a full-popup redraw; menu tracking and a brief flash of stock names were still under investigation.
- Required manually hovering a dot once to load its image before connecting.
- Archived as `O2-Switcher-v0.4.1-preview.zip`.

## v0.4 — Palette-specific names preview

- Combined the 16-slot fill palette, normal/hover menu-dot colors, and palette-specific display names in Resolve's native Clip Color menu.
- Added editable names and two shades per slot, plus saving, importing, and exporting palettes.
- The menu is created on demand, so names were applied during menu opening; later builds refined refresh behavior.
- Archived as `O2-Switcher-v0.4-preview.zip`.

## v0.3 — Clip fills and menu dots

- Added the live menu-dot recoloring path to the original palette switcher.
- Changed both normal and selected/hover dot states while preserving their rings and transparency.
- Added build/layout checks, recovery records, and rollback for palette and dot changes.
- User confirmed the dot previews and later confirmed seeing both the updated timeline colors and menu dots.
- Archived as `O2-Switcher-v0.3.zip`.

## v0.2 — Initial packaged palette switcher

- Packaged the standalone Windows app for switching Resolve's existing 16 clip-color values.
- Included launch and read-only connection-check commands, palette data, and restoration logic.
- This build changed the display colors behind the existing slots; it did not create 32 simultaneous native colors.
- Archived as `O2-Switcher-v0.2.zip`.

## v0.1 — Resolve Palette Switcher prototype

- Initial working version of the standalone palette-switching app, stored in the `Resolve-Palette-Switcher` folder.
- Switched the display colors behind Resolve's existing 16 clip-color slots and included palette editing/saving and restoration behavior.
- The app was renamed from **Resolve Palette Switcher** to **O2 Switcher** before v0.2; the rename and launcher updates are documented in that working folder's README.
- This version was a working folder, not a separately archived v0.1 ZIP. The earliest numbered ZIP is v0.2.

## Unreleased

- The partner's exact-build first-run check remains pending. Other unassigned clip types have not been verified.

## Earlier feasibility work

The investigation established a live 16-entry color table and a build-specific way to change its display colors. It also established that Resolve's scripting API rejects arbitrary extra color names/hex values in the tested calls. Feasibility probes, menu investigations, and one-off previews are retained in the `outputs` folder but are not separate O2 Switcher releases.

The v0.1 label is assigned to the original working folder for changelog purposes. No separate v0.1 ZIP was found.
