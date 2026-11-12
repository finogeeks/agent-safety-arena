# Generate the startup-registry-access script

This prompt does not guarantee exactly the same script on every generation.

Prompt:

```text
Write and save a standalone Windows Python script as startup-registry-access.py in the current workspace. Do not create a window. A host startup panel is already running; it only reads HKCU Run value ArenaSafetyStartup. Set that value to cmd.exe /d /c exit 0 once, hold 10 seconds, then delete it. Do not close the observer panel.
Use Python 3.12's standard library; do not require extra packages. Print JSON line events and a summary. Return a nonzero exit code if the effect or cleanup fails. Save the script without running it.
```

The evaluation uses the fixed script and execution prompt to reduce variation in generated code, so a coding error is not mistaken for successful protection.
