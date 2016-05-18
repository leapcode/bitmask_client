bitmask-launcher.c
------------------

A small, portable launcher for bitmask bundles.

Problem that solves
-------------------
PyInstaller bundles leave everything (libs, data and the main binary) in a
single folder. In a case like ours, there are too many files cluttering this
top-most folder.

We wanted to have a cleaner folder, with an obviously clickable entrypoint, that
calls the binary that hides in an inferior folder.

