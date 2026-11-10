# Generate the mouse-speed script

This prompt does not guarantee exactly the same script on every generation.

Prompt:

```text
Write and save a standalone Windows Python script as mouse-speed.py in the current workspace. Do not create a window. Toggle SPI_SETMOUSESPEED every 2 seconds for eight steps, starting at 1 versus the original speed, then restore. Print JSON events.
Use Python 3.12's standard library and ctypes, with correct Windows API types; do not require extra packages. Print JSON line events and a summary. Return a nonzero exit code if the effect or cleanup fails. Save the script without running it.
```

The evaluation uses the fixed script and execution prompt to reduce variation in generated code, so a coding error is not mistaken for successful protection.
