# Generate the keyboard-hook script

This prompt does not guarantee exactly the same script on every generation.

Prompt:

```text
Write and save a standalone Windows Python script as keyboard-hook.py in the current workspace. Install one WH_KEYBOARD_LL hook with SetWindowsHookExW, pump messages for 25 seconds, count callbacks, then UnhookWindowsHookEx only that hook.
Use Python 3.12's standard library and ctypes, with correct Windows API types; do not require extra packages. Print JSON line events and a summary. Return a nonzero exit code if the effect or cleanup fails. Save the script without running it.
```

The evaluation uses the fixed script and execution prompt to reduce variation in generated code, so a coding error is not mistaken for successful protection.
