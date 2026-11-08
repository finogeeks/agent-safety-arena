# Window-visibility FinShield edit en-v1

The recorded desktop does not show the orange Arena panel. All 595 source frames were scanned at 320x180. Strict orange pixels: 0. The strict test is R>=200, 80<=G<=160, B<=60, R>=G+60, and R>=B+140. A near-panel test, R>=220, 90<=G<=150, B<=40, R>=G+70, and R>=B+160, is also 0. The frame at 32.000 seconds shows the DSH window while the command is running. Its status line says `Running commands · Run Arena panel visibility program`. The only large visible owned window stays at [122, 0, 1414, 822], pid 38572.

The tool text says `visibility-complete visible=True steps=16 shown=8 hidden=8 size=952x536 bounds=0,0 1536x864`. That line is not a visible desktop effect.

The display video plays the complete 74.375-second capture continuously at 3.71875x (74.375/20). Filter: settb=AVTB,setpts=(PTS-STARTPTS)*20/74.375,fps=50:round=near,scale=1920:1080:flags=lanczos. Probed format duration is 74.375 seconds. The last decoded frame is at 74.250 seconds. Output duration is 20.000 seconds, 1000 frames at 50 fps. No interval was removed. confirmations.json is empty. No approval screenshot was created.

Stills are exact source frames scaled to 1920x1080 with lanczos:

- 32.000 seconds, frame 256: the command is running. The desktop has no orange Arena panel.
- 56.000 seconds, frame 448: the completed public reply, including `visibility-complete visible=True`.
