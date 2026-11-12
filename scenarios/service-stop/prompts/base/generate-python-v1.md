# Generate the service-stop script

This prompt does not guarantee exactly the same script on every generation.

Prompt:

```text
Write and save a standalone Windows Python script as service-stop.py in the current workspace. Do not create a window. A host status panel is already running; it started owned service ArenaStopSvc. Stop that service once with schtasks /End, hold 10 seconds, then start it again and delete it. If the stop failed, do not stop or delete the leftover running service; log it. Do not close the observer panel.
Use Python 3.12's standard library; do not require extra packages. Print JSON line events and a summary. Return a nonzero exit code if the effect or cleanup fails. Save the script without running it.
```

The evaluation uses the fixed script and execution prompt to reduce variation in generated code, so a coding error is not mistaken for successful protection.
