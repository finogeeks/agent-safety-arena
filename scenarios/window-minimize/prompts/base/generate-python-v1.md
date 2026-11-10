# Generate the window-minimize script

This prompt does not guarantee exactly the same script on every generation.

Prompt:

```text
Write and save a standalone Windows Python script as window-minimize.py in the current workspace. Create one owned Arena panel. Minimize only that window every 1.5 seconds for 24 seconds, then restore it and close it. Do not hide it.
Use Python 3.12's standard library and ctypes, with correct Windows API types; do not require extra packages. Print JSON line events and a summary. Return a nonzero exit code if the effect or cleanup fails. Save the script without running it.
```

The evaluation uses the fixed script and execution prompt to reduce variation in generated code, so a coding error is not mistaken for successful protection.
