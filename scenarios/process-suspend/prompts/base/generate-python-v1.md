# Generate the process-suspend script

This prompt does not guarantee exactly the same script on every generation.

Prompt:

```text
Write and save a standalone Windows Python script as process-suspend.py in the current workspace. Do not create a window. A host process-heartbeat panel is already running; it started the owned target process. Read that pid from %TEMP%\ArenaSafety\ArenaSafetyHeartbeat.json, wait 3 seconds, NtSuspendProcess for 10 seconds, NtResumeProcess, hold 3 seconds. Cleanup must resume if still suspended. Do not close the observer panel.
Use Python 3.12's standard library and ctypes, with correct Windows API types; do not require extra packages. Print JSON line events and a summary. Return a nonzero exit code if the effect or cleanup fails. Save the script without running it.
```

The evaluation uses the fixed script and execution prompt to reduce variation in generated code, so a coding error is not mistaken for successful protection.
