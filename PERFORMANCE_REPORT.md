# Veil performance completion report — v0.99.9-beta candidate

Measured 2026-10-23 against v0.99.8-beta on the same Windows machine. These are
Tk event-processing completion times, not display scanout, physical edge-drag,
or end-to-end Resolve visual timings. Ordinary short operations:100 samples;
create/save:50. P50/P95/max and all individual samples are retained locally.
Normal desktop Tk access and bundled fonts were used for both comparable runs.
Root geometry1220×840, demo mode, disposable libraries, Resolve closed. No
production pin, personal library, project, media or native profile was modified.
Hardware: AMD Ryzen9 9950X3D; Python reports16 logical CPUs; physical RAM
65,909,673,984 bytes. Windows11 build26200, Python3.12.14, Tk8.6.12;
Tk scaling1.334 and Veil logical scale1.00049 (approximately100%). Hardware
memory was recorded separately on the same unchanged machine.

## Before/after

| Metric | Before | After | Target | Result |
|---|---|---|---|---|
| Menu opening and closing P95 | 10.226 ms | 9.581 ms | ≤50 ms | Pass |
| Hover feedback P95 | 1.963 ms | 0.716 ms | ≤30 ms | Pass |
| Selection feedback P95 | 16.200 ms | 6.315 ms | ≤50 ms | Pass |
| Routine selected-card repaint P95 | 28.357 ms | 6.736 ms | ≤16.7 ms | Pass |
| Library refresh P95 | 271.965 ms | 0.426 ms | ≤100 ms | Pass |
| Save through visible library feedback P95 | 1233.364 ms | 28.851 ms | ≤100 ms | Pass |
| Editor palette switch (not Apply) P95 | 256.908 ms | 13.354 ms | ≤50 ms | Pass |
| Complete library filter refresh P95 | 290.109 ms | 56.374 ms | ≤50 ms | Fail |
| Warm palette validation (not native Apply) P95 | 0.039 ms | 0.042 ms | ≤10 ms | Pass |
| Dropdown scroll, 5 entries P95 | Unsupported wheel | 1.099 ms | ≤50 ms | Pass |
| Dropdown scroll, 20 entries P95 | Unsupported wheel | 2.421 ms | ≤50 ms | Pass |
| Dropdown scroll, 50 entries P95 | Unsupported wheel | 2.430 ms | ≤50 ms | Pass |
| Dropdown scroll, 100 entries P95 | Unsupported wheel | 2.267 ms | ≤50 ms | Pass |
| Complete visible Resolve Apply P95 | Not Measured | Not Measured | ≤250 ms stretch | Pending genuine native test |
| Media Pool color failures,100 cycles | Not Measured | Not Measured |0 | Pending genuine native test |
| Text/Text+ default/explicit slot13 mapping | Not Measured | Not Measured |100% | Pending genuine native test |
| Settled idle CPU, mean of three5s windows |0.937% |0.727% |≤1% | Pass for sampled average; see variability below |

Filter layout transitions sometimes exceed50ms; the remaining cost is Tk
grid hide/show and native event processing, rather than regenerating palettes.
No all-operations-under50ms or60fps claim is made. Selected-card repaint is a
representative localized update; it is not the cost of every resize/repaint.
No calibrated high-speed flicker/scanout measurement was performed.

## All eight task areas

1. **Application performance:** removed repeated legacy-palette generation,
   reused unchanged cards, localized selection, reused menu rasters and editor
   widgets. Target table above shows the remaining filter latency miss.
2. **Apply performance:** existing validated/serialized native transaction is
   unchanged. Warm validation meets10ms comfortably. A deliberately slow fake
   backend test proves UI event processing continues and a second Apply while
   busy does not enqueue a duplicate transaction. This is simulated evidence,
   not genuine native Apply timing, variance, or repeated native switching.
3. **Media Pool stability:** reviewed existing guarded refresh path; no new
   native changes.100 genuine cycles and first-stable-frame correctness remain
   Not Measured. Existing historical Apply/Restore evidence does not satisfy
   this new endurance requirement.
4. **Text clip mapping:** native renderer, default-fill operands and profiles
   remain byte-identical to0.99.8. This milestone does not establish default
   Text/Text+ slot13 behavior. No guessed address or broader recoloring added.
   Genuine timeline-view/mapping verification remains Not Measured.
5. **Palette icons:** exact-size antialiased Native and Custom marks, cached
   per appearance/size.8 Dark/Light logical-size cases at100/125/150/200%
   captured and inspected. Actual Windows DPI switching was not performed.
6. **Library synchronization:**50 create/save plus rename/copy/delete,
   failure injection, provenance/filter retention and disk reload checks pass.
   New entries appear without restart; no duplicates or false-success entry.
7. **Filter indicators:** one checked option independent of hover, compact
   unchanged labels/dividers, preference retained across reopening, library
   refresh/save and actual fresh App initialization. Appearance writes merge
   preferences instead of discarding filter/other fields. No silent filter reset.
8. **Editor dropdown:** bounded viewport, wheel and Up/Down/Home/End/Page
   navigation, keyboard visibility, first/middle/last selectable in5/20/50/100
   entries, above/below edge placement and owner-move/resize dismissal.

## Endurance, resources and rendering counts

100 switches,100 filters,50 saves,100 routine selections and100 menu cycles
were timed; an additional500 menu open/close cycles were checked in5 batches.
All batches retained exactly79 Tk images,193 GDI and195 USER resources.
No growth in those menu-resource counts was observed. Process working-set
measurements are snapshots after different library sizes; they do not prove
all long-term memory behavior. Editor last25 switch mean11.02ms versus first25
13.46ms: no progressive editor slowdown in that sample; not native Apply evidence.

20 unchanged refreshes previously created600 cards; candidate creates0.
100 menu hovers previously generated297 raster images; candidate generates0
after initial menu setup. Both redundant-work counts reduced100%, exceeding
the50% reduction goal for these specific measured operations.

The process working set increased from54,849,536 to65,003,520 bytes in the
baseline workload and from57,913,344 to66,121,728 in the pre-review candidate run.
These snapshots include changing library contents and allocator caches; they
are not a measured leak rate or long-duration memory guarantee.

The initial5s post-workload idle window was6.243% in the pre-review final run,
versus below process-timer resolution in earlier runs. It is not discarded.
A separate80-palette idle comparison settled2s, then sampled three5s windows:
baseline0.937/1.248/0.625%, candidate0.623/0/1.558%. Average0.937→0.727%.
This meets the average target in that repeat, but CPU is variable and individual
windows exceed1%. Neither the cause of the6.243% transient nor long-term idle
behavior is established by these short samples; no always-under1% claim.

## Verification boundaries and remaining checks

Focused GUI tests cover the new behavior, library search/provenance, update
notices, theme resize/lifecycle and raster correctness. The development offline
suite initially recorded102/103 passing: a caption pixel check failed under
sandbox capture. That exact check passed against the candidate with normal
desktop capture access. See the local test ledger for subsequent full-run status.
The complete103-test development suite then passed with normal desktop access.
The final focused group comprises10 new acceptance tests plus6 library,3 notice,
2 theme-preview and3 raster tests (24 total), all in disposable data. Review
also caught and fixed retained rename targets during palette switching and
off-screen menu invocation after wheel scrolling; regression tests pass. Theme Lab
offline report unchanged; native Apply not attempted.

Native integration acceptance is **not complete**. Before claiming all brief
targets, obtain genuine100-cycle Media Pool evidence, Text/Text+ default and
explicit slot13 cases across timeline views, click-to-visible Apply timing,
comparable-palette variance and repeated native-switch timing. Also complete
physical DPI and manual flicker/edge-drag checks. No running Resolve process
was available during this work; no Resolve launch/install/native writes occurred.
See NATIVE_PERFORMANCE_PROTOCOL.md. The previous exact Free/Studio21.1.1.10
support remains unchanged; retired21.1.0.14 stays disabled.
