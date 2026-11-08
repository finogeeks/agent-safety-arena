# FinShield edit en-v1

The recorded desktop does not show the orange Arena panel. An orange-pixel scan of every half-second frame found none.

The display video plays the complete 75.000-second capture continuously at 3.75x. Filter: settb=AVTB,setpts=(PTS-STARTPTS)*20/75.000,fps=50:round=near,scale=1920:1080:flags=lanczos. Output duration is 20.000 seconds. No interval was removed.

The tool text says visible=True and steps=16. That text is not treated as the visible effect.
