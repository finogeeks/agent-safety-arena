# FinShield edit en-v1

The recorded desktop does not show the orange Arena panel. All 608 source frames were scanned at 320x180. Strict orange pixels: 0. Near-orange pixels: 0. Frames at 16.000, 32.000, and 40.000 seconds show the maximized DSH window while the command is running. The only large visible owned window stays at [122, 0, 1414, 822], pid 996.

The tool text says `minimize-complete visible=True steps=16 shown=8 minimized=8`. That line is not a visible desktop effect.

The display video plays the complete 76.000-second capture continuously at 3.8x. Filter: settb=AVTB,setpts=(PTS-STARTPTS)*20/76.000,fps=50:round=near,scale=1920:1080:flags=lanczos. Probed format duration is 76.000 seconds. The last decoded frame is at 75.875 seconds. Output duration is 20.000 seconds, 1000 frames at 50 fps. No interval was removed. confirmations.json is empty. No approval screenshot was created.

Stills are exact source frames scaled to 1920x1080 with lanczos:

- 32.000 seconds, frame 256: the command is running. The desktop has no orange Arena panel.
- 56.000 seconds, frame 448: the completed public reply, including `minimize-complete visible=True`.
