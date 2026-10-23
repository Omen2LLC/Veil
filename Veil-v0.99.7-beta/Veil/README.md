# Veil v0.99.7-beta

Extract the whole Windows package to a writable folder and open Veil.exe. Keep its files together. Python is bundled in the Windows package. The separate source package needs 64-bit Python 3.11+ with Tkinter.

The 15 starter palettes include Peachy Pop, Afterhours and Retrocal. Personal palettes and appearance settings are preserved during upgrades. Updates offer Upgrade, Later and Skip, and retain the prior version for rollback. Beta copies receive newer betas and stable releases; stable copies receive stable releases.

Palette Apply/Restore supports the independently verified Windows Resolve Free and Studio executables for build 21.1.1.10. Veil selects the matching profile by executable SHA-256; matching version numbers alone do not enable writes. Other builds, including 21.1.0.14, are disabled. Normal close restores the native palette. Themes are a preview during beta.

This beta adds Free support and corrects an overlong Qt menu-pixmap read that could interrupt restoration during repainting. The existing Studio compatibility profile is preserved. Free Apply/Restore passed with Vivid and Soft palettes, custom names, 96 menu-dot records and three loaded thumbnail records on generated test media. Studio's native evidence predates this beta; this machine has Free installed, so a fresh Studio runtime test remains outstanding.

To build from source on Windows with 64-bit Python and Tkinter: install `requirements-build.txt`, run `python -m unittest discover -v`, refresh both official release records with `python release_gate.py --record --version v0.99.7-beta`, then run `python build_windows.py`. The standalone folder is created under `dist/Veil-v0.99.7-beta/Veil`. Build dependencies are not needed to run the packaged app.

# Veil v0.99.7-beta

Adds15 named palettes: Forest, Miyazaki, Summers Past, Vanilla Milkshake,
Island Joy, Lost Century, Sweetie, Ate, Magicolor, Castpixel, Nanner,
Loop Hero, Jmp Japanese Machine Palette, Punolite and Corruption.

Each includes16 distinct color names and two reviewed shades. Dark companion
shades were selectively lifted for more balanced pairs. The original15 starter
palettes, including Peachy Pop, Afterhours and Retrocal, remain included.

Updates merge new palettes into your library and preserve existing palettes and
settings. Existing customizations win if a palette name already exists.
Use Install update in Veil to download, verify and install with the existing
separate-version migration and rollback safeguards. Python is bundled.

Native backend and exact Free/Studio21.1.1.10 profiles are unchanged from0.99.4.
Official Windows Studio metadata checked2026-10-23:21.1.1.10. Other builds remain
blocked. No new native Apply/Restore or timeline readability test is claimed.
The palette tuning was reviewed offline; some darker-secondary similarities
remain a stylistic tradeoff. Themes remain a preview during beta.

# Veil v0.99.7-beta

Renames Jmp Japanese Machine Palette to Neon Arcade and Loop Hero to Dungeon.
All30 palettes retain exactly the same color pairs and color names.

Existing libraries migrate the two titles with a backup. Edited colors are
preserved; a conflicting custom destination palette is kept without overwriting
either entry. Native backend and exact Free/Studio21.1.1.10 profiles are unchanged.
Official Windows Studio metadata checked2026-10-23 remains21.1.1.10.
Bundled Windows package includes Python. Install from Settings > Check for updates.
No new native Apply/Restore test or broader compatibility is claimed.

Personal palettes remain local and survive upgrades. Public packages include only palettes explicitly marked veil-native in native-palette-catalog.json. Personal saved libraries are not release inputs.

# Veil v0.99.7-beta

Fixes library search results staying off-screen after scrolling. Search now
refreshes on text changes, including paste and clearing, ignores outer spaces,
and returns to the first matching card. All30 native palettes are searchable.

Palette cards show a small Veil logo for catalog-matching native palettes and
a simplified waist-up person icon for custom or edited palettes. These marks
work with both Dark and Light appearance; click either mark to select its card.
Custom palettes remain local and are preserved during upgrades. Public packages
contain only the explicit approved native catalog. No palette colors changed.

Free/Studio21.1.1.10 native runtime/profiles remain unchanged. Official Studio
metadata checked2026-10-23 remains21.1.1.10. No new native Apply/Restore claimed.
