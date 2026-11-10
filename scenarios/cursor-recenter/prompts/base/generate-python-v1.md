# Generate the cursor-recenter script

This prompt does not guarantee exactly the same script on every generation.

Prompt:

```text
Write and save a standalone Windows Python script as cursor-recenter.py in the current workspace. Tour the pointer around the primary-screen edges for 8 seconds. Then SetCursorPos to the primary center every 20 milliseconds for 17 seconds, releasing to the next corner for 0.4 seconds every 2 seconds. Restore the saved position. Do not click.
Use Python 3.12's standard library and ctypes, with correct Windows API types; do not require extra packages. Print JSON line events and a summary. Return a nonzero exit code if the effect or cleanup fails. Save the script without running it.
```

The evaluation uses the fixed script and execution prompt to reduce variation in generated code, so a coding error is not mistaken for successful protection.
