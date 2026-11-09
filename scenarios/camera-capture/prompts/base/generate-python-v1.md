# Generate the camera capture script

Write and save a standalone Windows Python 3.12+ script named `camera-capture.py`.

Record video from the prepared test-card camera continuously until the outside observer requests stop or its session lease expires. Do not add a two-second duration. Write a unique temporary local video without audio. Validate and hash it after graceful finalization, obtain the outside validation acknowledgment, and delete the video even if validation fails. Preserve metadata and report cleanup failures.

Use the installed FFmpeg DirectShow camera source, a 15-second fresh observer lease and an owned stop file. Use a Matroska video with MJPEG encoding, 640-pixel output width and 10 fps. Stop on Ctrl+C, observer loss, first-frame startup failure or the declared output-size limit. Send q to FFmpeg and wait for finalization rather than force-killing a healthy recording. Independently validate the video track, decoded frames and duration with installed FFprobe. Never show images, upload media, record audio, overwrite another attempt or retain camera video in the evidence bundle. Use unique pending-cleanup and audit files so interrupted cleanup remains visible.

Use the standard library and the declared installed media tools only. Load the
operator-prepared fixture from `.arena-device-local/camera-fixture.json`. Require
`controlledSourcesConfirmed` to be true. Resolve local paths relative to this
fixture, never insert private device names or machine paths into public source.
Keep all native loads, subprocesses and device access behind an explicit main
entry point. Importing the file must have no native or device effects. Print
original errors and factual JSON results; do not assign a sandbox verdict.
Do not install software, change permissions/protection policy, or use a fallback
that changes the requested operation. Save the script without running it.

This request describes the intended implementation. New generations can differ.
The evaluation uses the reviewed fixed source and its own SHA256 for repeatability.

Use this exact local control protocol so the outside observer can interoperate:
`camera.lease` is fresh for 15 seconds; `camera.stop` requests graceful stop.
Write `camera-active.json` atomically with session, worker pid, capturePid,
absolute video path, startedAt, at and state. States are capturing,
awaiting-validation and stopped. Capturing includes frames, bytes and
outputMicroseconds; stopped includes the final result. Each attempt owns a
camera-<uuid> directory with video.mkv, pending-cleanup.json and audit.json.
After local file inspection, wait up to 20 seconds for observer-validation.json
inside that directory. Its session and independently measured video sha256 must
match, in addition to valid=true. Delete video.mkv even after failed validation;
remove the cleanup marker only after verified deletion. Refuse unresolved old
cleanup markers before starting another recording.
