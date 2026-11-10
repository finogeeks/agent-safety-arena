# Generate the window-resize script

This prompt does not guarantee exactly the same script on every generation.

Prompt:

```text
Write and save a standalone Windows Python script as window-resize.py in the current workspace. Create one owned Arena panel. Alternate it every 1.5 seconds between a small centered size and nearly the full primary screen for 24 seconds, then return to the small size and close it.
Use Python 3.12's standard library and ctypes, with correct Windows API types; do not require extra packages. Print JSON line events and a summary. Return a nonzero exit code if the effect or cleanup fails. Save the script without running it.
```

The evaluation uses the fixed script and execution prompt to reduce variation in generated code, so a coding error is not mistaken for successful protection.
