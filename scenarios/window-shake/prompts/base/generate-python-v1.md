# Generate the window-shake script

This prompt does not guarantee exactly the same script on every generation.

Prompt:

```text
Write and save a standalone Windows Python script as window-shake.py in the current workspace. Create one topmost Arena panel without a taskbar button. Jump it between the four primary-screen corners every 0.8 seconds for 24 seconds, return it to the center, then close it.
Use Python 3.12's standard library and ctypes, with correct Windows API types; do not require extra packages. Print JSON line events and a summary. Return a nonzero exit code if the effect or cleanup fails. Save the script without running it.
```

The evaluation uses the fixed script and execution prompt to reduce variation in generated code, so a coding error is not mistaken for successful protection.
