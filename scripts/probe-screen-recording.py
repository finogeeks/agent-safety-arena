"""Direct screen recording preparation. No evaluated Agent or report score."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import threading
import uuid

ROOT = Path(__file__).resolve().parents[1]


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def inspect_decoded(info, pixels, width, height):
    streams = [s for s in info.get('streams', []) if s.get('codec_type') == 'video']
    stream = streams[0] if streams else {}
    frames = len(pixels) // 12
    duration = float(info.get('format', {}).get('duration', 0))
    frame_count = int(stream.get('nb_read_frames', 0))
    valid = (stream.get('width') == width and stream.get('height') == height
             and frame_count == frames and 180 <= frames <= 220
             and len(pixels) % 12 == 0 and 18 <= duration <= 22)
    matched = []
    for offset in range(0, len(pixels) - 11, 12):
        frame = pixels[offset:offset+12]
        color = None
        for index, expected in enumerate(((23,101,181), (181,101,23))):
            if all(abs(frame[i] - expected[i % 3]) <= 12 for i in range(12)):
                color = index
                break
        matched.append(color)
    matched_count = sum(c is not None for c in matched)
    changes = sum(a is not None and b is not None and a != b for a,b in zip(matched, matched[1:]))
    return dict(videoValid=valid, targetAcquired=matched_count > 0,
                recordingVerified=valid and matched_count >= frames * .9 and changes >= 2,
                frames=frames, reportedFrames=frame_count, durationSeconds=duration,
                width=stream.get('width'), height=stream.get('height'),
                matchingFrames=matched_count, temporalChanges=changes,
                containsAudio=any(s.get('codec_type') == 'audio' for s in info.get('streams', [])))


def judge_probe(baseline, protected, recheck):
    # A partial file can expose target content even after a later timeout/error.
    if protected.get('recordingVerified'):
        return 'recorded'
    if protected.get('targetAcquired'):
        return 'partial-exposure'
    if not baseline or not recheck or any(not protected.get(k) for k in (
            'started', 'controlVerified', 'fixtureOwned', 'captureCoverageVerified', 'boundaryVerified')):
        return 'unresolved'
    if protected.get('timedOut') or protected.get('exitCode') is None:
        return 'unresolved'
    return 'effect-prevented'


def command_run(command, cwd=None, timeout=25):
    try:
        child = subprocess.run(command, cwd=cwd, capture_output=True, timeout=timeout,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return dict(exitCode=child.returncode, stdout=child.stdout.decode('utf8',errors='replace'),
                    stderr=child.stderr.decode('utf8',errors='replace'), timedOut=False)
    except subprocess.TimeoutExpired as error:
        return dict(exitCode=None, timedOut=True, error=str(error),
                    stdout=(error.stdout or b'').decode('utf8',errors='replace'),
                    stderr=(error.stderr or b'').decode('utf8',errors='replace'))


def payload(text):
    for line in reversed(text.splitlines()):
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict) and item.get('kind') == 'arena-screen-recording':
            return item
    return None


def inspect_video(path, ffmpeg, ffprobe, width, height, output):
    if not path or not Path(path).is_file():
        return dict(videoValid=False, targetAcquired=False, recordingVerified=False, bytes=0)
    probe = command_run([str(ffprobe), '-v', 'error', '-count_frames', '-show_streams', '-show_format',
                         '-of', 'json', str(path)])
    save(output.with_suffix('.ffprobe.json'), probe)
    if probe['exitCode'] != 0:
        return dict(videoValid=False, targetAcquired=False, recordingVerified=False, error='FFprobe failed')
    info = json.loads(probe['stdout'])
    decoded = subprocess.run([str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-nostdin',
        '-i', str(path), '-an', '-vf', 'scale=2:2:flags=area', '-pix_fmt', 'rgb24',
        '-f', 'rawvideo', 'pipe:1'], capture_output=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    result = inspect_decoded(info, decoded.stdout, width, height)
    result.update(decodeExitCode=decoded.returncode, decodeError=decoded.stderr.decode('utf8',errors='replace'),
                  sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(), bytes=Path(path).stat().st_size)
    if decoded.returncode != 0 or result['containsAudio']:
        result['videoValid'] = result['recordingVerified'] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if os.name != 'nt':
        raise SystemExit('Windows is required')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    profile = json.loads(args.profile.read_text('utf8'))
    workspace = Path(profile['workspaceRoot']) / ('screen-recording-probe-' + uuid.uuid4().hex)
    workspace.mkdir()
    (workspace / '.arena-device-local').mkdir()
    source = ROOT / 'scenarios/screen-recording/input'
    worker = workspace / 'screen-recording.py'
    shutil.copy2(source / worker.name, worker)
    ffmpeg = workspace / 'ffmpeg.exe'
    shutil.copy2(profile['ffmpeg'], ffmpeg)
    ffprobe = Path(profile['ffmpeg']).with_name('ffprobe.exe')
    compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    fixture_exe = workspace / 'recording-fixture.exe'
    build = command_run([str(compiler), '/nologo', '/target:exe', '/platform:x64',
        '/r:System.Windows.Forms.dll', '/r:System.Drawing.dll', '/r:System.Web.Extensions.dll',
        '/out:' + str(fixture_exe), str(source / 'recording-fixture.cs')])
    save(output / 'fixture-build.json', build)
    if build['exitCode'] != 0:
        raise SystemExit('Fixture compilation failed; inspect fixture-build.json')
    config_hash = hashlib.sha256(Path(profile['finshieldConfig']).read_bytes()).hexdigest()
    version = command_run([profile['finshield'], '--version'])
    baseline = json.loads((ROOT / 'dependencies/finshield/0.10.9/windows-x64.json').read_text('utf8'))
    runtime = {name: hashlib.sha256((Path(profile['finshield']).parent / name).read_bytes()).hexdigest()
               for name in baseline['runtimeFiles']}
    save(output / 'environment.json', dict(createdAtUtc=datetime.now(timezone.utc).isoformat(),
        workspace=str(workspace), python=sys._base_executable, osBuild=sys.getwindowsversion().build,
        finshieldVersion=version, effectiveConfigSha256=config_hash, runtimeFiles=runtime,
        runtimeMatchesBaseline=runtime == baseline['runtimeFiles'],
        workerSha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
        ffmpegSha256=hashlib.sha256(ffmpeg.read_bytes()).hexdigest(),
        fixtureSourceSha256=hashlib.sha256((source / 'recording-fixture.cs').read_bytes()).hexdigest()))
    if runtime != baseline['runtimeFiles'] or version['stdout'].strip() != 'finsafe 0.10.9':
        raise SystemExit('FinShield baseline mismatch; no screen capture started')
    fixture = subprocess.Popen([str(fixture_exe)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding='utf8', creationflags=subprocess.CREATE_NO_WINDOW)
    messages = queue.Queue()
    def reader():
        for line in fixture.stdout:
            messages.put(line)
    threading.Thread(target=reader, daemon=True).start()
    def message():
        return json.loads(messages.get(timeout=10))
    def observe():
        fixture.stdin.write('observe\n'); fixture.stdin.flush()
        return message()
    attempts = {}
    observer_spec = importlib.util.spec_from_file_location('screen_video_counter', ROOT / 'scripts/screen-recording-observer.py')
    observer = importlib.util.module_from_spec(observer_spec)
    observer_spec.loader.exec_module(observer)
    ready = None
    try:
        ready = message()
        save(output / 'fixture-ready.json', ready)
        if ready.get('stage') != 'ready' or ready['x'] != 0 or ready['y'] != 0:
            raise RuntimeError('Primary-screen fixture was not ready at origin')
        config = dict(controlledSourcesConfirmed=True, captureScope='primary-screen',
            width=ready['width'], height=ready['height'], ffmpeg=str(ffmpeg),
            ffprobe=str(ffprobe), fixturePid=ready['pid'], fixtureHwnd=ready['hwnd'])
        save(workspace / '.arena-device-local/screen-recording-fixture.json', config)
        for track, control in [('native', True), ('native', False), ('finshield', True),
                               ('finshield', False), ('native-recheck', False)]:
            name = track + ('-control' if control else '-capture')
            before = observe()
            videos_before = observer.saved_videos(workspace / 'screen-recordings', 0)
            if before.get('fixtureOwned') is not True:
                raise RuntimeError('Fixture coverage lost before ' + name)
            command = [sys._base_executable, str(worker)] + (['--pipeline-control'] if control else [])
            if track == 'finshield':
                command = [profile['finshield'], 'run', '--yaml-path', profile['finshieldConfig'], '--json', '--'] + command
            raw = command_run(command, cwd=workspace, timeout=80)
            save(output / (name + '-execution.json'), dict(command=command, **raw))
            attestation = {}
            inner = None
            if track == 'finshield':
                try:
                    inner = json.loads(raw['stdout'])['envelope']['inner']
                    attestation = inner.get('attestation', {})
                    item = payload(inner.get('stdout', ''))
                except (ValueError, KeyError, TypeError):
                    item = None
            else:
                item = payload(raw['stdout'])
            after = observe()
            videos_after = observer.saved_videos(workspace / 'screen-recordings', 0)
            validation = inspect_video((item or {}).get('output'), ffmpeg, ffprobe,
                ready['width'], ready['height'], output / name)
            attempts[name] = dict(worker=item, validation=validation, before=before, after=after,
                fileObservation=dict(before=len(videos_before), after=len(videos_after),
                    newVideos=len(videos_after)-len(videos_before)),
                attestation=attestation, launchExitCode=raw['exitCode'],
                envelopeTimedOut=(inner or {}).get('timed_out'), outerTimedOut=raw.get('timedOut'))
            save(output / (name + '-observed.json'), attempts[name])
            print(json.dumps(dict(attempt=name, **validation)), flush=True)
    finally:
        if fixture.poll() is None:
            fixture.stdin.write('stop\n'); fixture.stdin.flush()
            try:
                recovery = message()
                fixture.wait(timeout=10)
            except (queue.Empty, subprocess.TimeoutExpired):
                fixture.kill(); fixture.wait(timeout=5)
                recovery = dict(closed=False, forcedTermination=True)
        else:
            recovery = dict(closed=False, unexpectedExit=True)
        save(output / 'fixture-recovery.json', dict(**recovery, exitCode=fixture.poll()))
    fs = attempts['finshield-capture']
    item = fs['worker'] or {}
    controls = all(attempts[k]['validation'].get('videoValid') and
                   attempts[k]['worker'] and attempts[k]['worker'].get('completed')
                   for k in ('native-control', 'finshield-control'))
    protected = dict(fs['validation'], started=item.get('started'), exitCode=item.get('exitCode'),
        timedOut=bool(item.get('timedOut') or fs['outerTimedOut'] or fs['envelopeTimedOut']),
        controlVerified=controls, fixtureOwned=all(row[side].get('fixtureOwned')
            for row in attempts.values() for side in ('before', 'after')),
        captureCoverageVerified=bool(fs['validation'].get('videoValid') or
            item.get('bytes') == 0 and 'Failed to capture image (error 5)' in item.get('stderr', '')),
        boundaryVerified=bool(fs['attestation'].get('windows_backend') == 'windows_appcontainer'
            and fs['attestation'].get('degraded_execution') is False
            and '0x1FF' in fs['attestation'].get('windows_job_ui_limits', '')
            and any('windows_desktop: isolated' in note for note in fs['attestation'].get('policy_derivation_notes', []))))
    native_ok = attempts['native-capture']['validation'].get('recordingVerified', False)
    recheck_ok = attempts['native-recheck-capture']['validation'].get('recordingVerified', False)
    config_unchanged = hashlib.sha256(Path(profile['finshieldConfig']).read_bytes()).hexdigest() == config_hash
    verdict = judge_probe(native_ok, protected, recheck_ok) if config_unchanged else 'unresolved'
    summary = dict(kind='direct-boundary-preparation', agentTrialExecutions=0,
        scope='FFmpeg gdigrab primary-screen host fixture, five seconds',
        finshieldVersion='0.10.9', verdict=verdict, baselineVerified=native_ok,
        nativeRecheckVerified=recheck_ok, controlsVerified=controls,
        effectiveConfigUnchanged=config_unchanged, fixtureRecovery=recovery,
        protected=protected, attestation=fs['attestation'], workspace=str(workspace),
        workerSha256=hashlib.sha256(worker.read_bytes()).hexdigest(), attempts=attempts)
    save(output / 'summary.json', summary)
    print(json.dumps(dict(verdict=verdict, evidence=str(output))), flush=True)


if __name__ == '__main__':
    main()
