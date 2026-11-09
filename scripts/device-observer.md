# Outside device observer

Status: Generated and compiled offline, not executed on a device or desktop.

The [Python panel](device-observer.py) is preparation equipment. Launch it in
the host context, separately from the tested Agent and its operation program.
It uses [camera-activity.cs](camera-activity.cs) for read-only Media Foundation
camera activity, and the inert [CoreAudio adapter](coreaudio-endpoint.py)
for audio state/session inspection. No camera/microphone samples are read by
the panel. It creates only the declared synthetic window in screen mode.

Prepare each candidate's example configuration in its workspace under
`.arena-device-local`. The example has confirmation disabled and placeholder
identifiers. Fill the exact controlled device/endpoint and absolute installed
media-tool paths before a separately authorized run. The camera symbolic link
is the Media Foundation sensor device identity, not a guessed friendly name.
Do not treat a missing activity report as a closed camera.

For camera preparation, compile the helper without starting it:

```powershell
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$source = (Resolve-Path 'scripts/camera-activity.cs').Path
# Replace this example workspace with the declared local trial workspace.
$fixtureDir = 'C:\example-trial-workspace\.arena-device-local'
$observerExe = Join-Path $fixtureDir 'camera-activity.exe'
& $compiler /nologo /target:exe /platform:x64 /r:System.Web.Extensions.dll "/out:$observerExe" $source
```

The fixture directory must already exist. A successful compiler result is not a
native camera test. Set `cameraActivityHelper` in the local fixture to this
executable. The observer starts that helper only when explicitly launched later.

```powershell
python scripts/device-observer.py camera --config 'C:\example-trial-workspace\.arena-device-local\camera-fixture.json'
```

Replace the example path. Other modes are `microphone` and `screen`,
each with its own prepared fixture. `--language zh-CN` localizes the principal
state labels; default display text is English. Some audit details retain exact
API terms. The screen mode fills the prepared fixture's HWND, owning PID and
coordinates; the tested worker must use that same file.

The camera observer supplies a fresh lease and writes its own OS activity log.
Stop requests graceful worker shutdown. Keep the panel open while it verifies
the finalized temporary video with FFprobe and writes an acknowledgment. The
worker then deletes the camera video. The panel itself does not retain media.
A forced worker termination may leave a pending-cleanup marker and local video;
resolve this exact owned attempt before another run. Never include such camera
media in a result bundle or GitHub commit.

Camera state is OS activity, recording progress is worker telemetry plus file
observation, and finalized video validation is a separate outside check. Audio
session activity proves an active endpoint session, not that specific samples
reached the tested worker. Speaker state proves a mute flag, not acoustic silence.
These boundaries and native API/driver compatibility need live validation later.
