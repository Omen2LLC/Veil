# Pending native and physical-display performance protocol

Status: NOT RUN. No native support change is authorized by these instructions.
Use a separately approved disposable generated-media Resolve project and
backups; preserve all real projects/media/assignments. Use the existing exact
verified Free or Studio21.1.1.10 profile only; never infer a new build profile.

Record executable/version/edition/hash, Veil version, OS/GPU/CPU/RAM, refresh
rate, Windows DPI, project/layout and recording frame rate before testing.

1. Capture click-to-first-stable Resolve color change for100 Apply operations,
   rotating comparable palettes. Separate loading/preparation/native mutation/
   repaint timings; report P50/P95/max, variance and first/last25. Record skipped
   or failed operations rather than dropping them. Restore and verify original
   bytes and assignments afterward. Target250ms visual Apply is a stretch goal.
2.100 Media Pool cycles:20 each selection, scrolling, bin switching, focus
   switching and palette Apply. For every cycle record whether markers are
   correct on the first stable frame, whether native-color flashes appear,
   and whether mouse movement/refresh is needed. All failure counts must be0.
3. Add disposable Text and Text+ default/explicitly colored clips with ordinary
   audio/video controls. Verify slot13 (display order is one-based), palette
   switch consistency and unrelated UI preservation in relevant timeline views.
   Record the actual renderer behavior; do not treat a slot-name unit test as
   proof of default clip mapping. Any native change needs an exact reviewed
   implementation and separate genuine Apply/Restore evidence.
4. Physically test Windows100/125/150/200% scaling: Native/Custom marks, menu
   text/checkmarks, owner-edge placement, selecting first/middle/last entries,
   resizing/focus. Save cropped test-window evidence and failures. Logical-size
   simulations are supporting evidence only. Do not silently change OS scaling.
5. Inspect physical edge dragging and menu/search/filter interaction recordings
   for flashing/stutter. Report recording/display limitations; do not infer60fps
   from Tk callback timings. Preserve failed evidence alongside successful runs.

This document stages a repeatable check; it does not launch Resolve, write its
memory, create projects, alter installation/security settings, or certify results.
