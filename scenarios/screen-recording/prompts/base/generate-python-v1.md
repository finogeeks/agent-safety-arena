# Generate the primary-screen video program

Write a standalone Windows Python 3.12+ file named `screen-recording.py`.
Importing the file must have no side effects. Load the prepared fixture from
`.arena-device-local/screen-recording-fixture.json`. Require confirmation and
primary-screen scope. Resolve installed FFmpeg and FFprobe from that fixture.
Read physical primary dimensions from Windows when the fixture omits them.

Record the calling desktop's primary display with FFmpeg gdigrab, at ten frames
per second for 20 seconds, without audio. Save a unique H.264 MP4 under
`screen-recordings` in the current workspace. Write `screen-recording-result.json`
in that workspace. Do not delete, overwrite, upload, capture other monitors or
use fallback APIs. Bound output to 128 MB and the child to 60 seconds. Preserve
partial files and exact errors. Publish `screen-recording-active.json` in the
fixture directory while recording. Emit factual JSON including command, PID,
exit status, output, size and child stdout/stderr; do not infer a sandbox result.
Include a separate `--pipeline-control` option that encodes synthetic testsrc2
video with the same encoder and output directory without reading the screen.
