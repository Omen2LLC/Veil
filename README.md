# Veil v0.99.3-beta

Extract the whole Windows package to a writable folder and open Veil.exe. Keep its files together. Python is bundled in the Windows package. The separate source package needs 64-bit Python 3.11+ with Tkinter.

The 15 starter palettes include Peachy Pop, Afterhours and Retrocal. Personal palettes and appearance settings are preserved during upgrades. Updates offer Upgrade, Later and Skip, and retain the prior version for rollback. Beta copies receive newer betas and stable releases; stable copies receive stable releases.

Palette Apply/Restore supports the independently verified Windows Resolve Free and Studio executables for build 21.1.1.10. Veil selects the matching profile by executable SHA-256; matching version numbers alone do not enable writes. Other builds, including 21.1.0.14, are disabled. Normal close restores the native palette. Themes are a preview during beta.

This beta adds Free support and corrects an overlong Qt menu-pixmap read that could interrupt restoration during repainting. The existing Studio compatibility profile is preserved. Free Apply/Restore passed with Vivid and Soft palettes, custom names, 96 menu-dot records and three loaded thumbnail records on generated test media. Studio's native evidence predates this beta; this machine has Free installed, so a fresh Studio runtime test remains outstanding.

To build from source on Windows with 64-bit Python and Tkinter: install `requirements-build.txt`, run `python -m unittest discover -v`, refresh both official release records with `python release_gate.py --record --version v0.99.3-beta`, then run `python build_windows.py`. The standalone folder is created under `dist/Veil-v0.99.3-beta/Veil`. Build dependencies are not needed to run the packaged app.
