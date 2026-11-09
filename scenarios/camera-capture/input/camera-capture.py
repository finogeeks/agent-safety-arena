"""Fixed camera worker. Import is inert. Camera images are never displayed."""
import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import uuid


def emit(**row):
    print(json.dumps(row, ensure_ascii=True), flush=True)


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=True, indent=2), encoding='utf8')
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05)


def record_command(config, video):
    return [config['ffmpeg'], '-hide_banner', '-loglevel', 'warning',
            '-progress', 'pipe:1', '-nostats', '-f', 'dshow',
            '-i', 'video=' + config['cameraDevice'], '-an',
            '-vf', 'scale=640:-2', '-r', '10', '-c:v', 'mjpeg', '-q:v', '8',
            '-f', 'matroska', '-n', str(video)]


def session_stop(*, stop, lease_age, size, limit):
    if stop:return 'requested-stop'
    if lease_age is None or lease_age < -2 or lease_age > 15:return 'observer-lost'
    if size >= limit:return 'output-limit'
    return None


def resolve_tool(value,base):
    tool=Path(value)
    resolved=(tool if tool.is_absolute() else base/tool) if ('/' in value or '\\' in value) else Path(shutil.which(value) or value)
    if not resolved.is_file():raise FileNotFoundError('Prepared installed tool not found: '+value)
    return str(resolved.resolve())


def inspect_video(config, video):
    result = subprocess.run([config['ffprobe'], '-v', 'error', '-count_frames',
        '-select_streams', 'v:0', '-show_entries',
        'stream=codec_type,nb_read_frames:format=duration', '-of', 'json', str(video)],
        capture_output=True, timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf8', errors='replace')[-2000:])
    data = json.loads(result.stdout)
    streams = data.get('streams', [])
    frames = int(streams[0].get('nb_read_frames', 0)) if streams else 0
    duration = float(data.get('format', {}).get('duration', 0))
    return dict(valid=bool(streams and streams[0].get('codec_type') == 'video' and frames > 0 and duration > 0),
                frames=frames, durationSeconds=duration)


def finish_video(video, inspect):
    """Retain measurements but remove only the supplied owned video, even on error."""
    result = dict(valid=False, deleted=False)
    try:
        if not video.is_file():raise ValueError('No finalized camera video')
        result['bytes'] = video.stat().st_size
        digest = hashlib.sha256()
        with video.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):digest.update(block)
        result['sha256'] = digest.hexdigest()
        result.update(inspect(video))
    except Exception as error:
        result.update(valid=False, errorType=type(error).__name__, error=str(error))
    finally:
        try:
            video.unlink(missing_ok=True)
            result['deleted'] = not video.exists()
        except OSError as error:
            result['cleanupError'] = str(error)
    return result


def run(config, base):
    lease, stop = base / 'camera.lease', base / 'camera.stop'
    limit = int(config.get('maxVideoBytes', 256 * 1024 * 1024))
    if not 1024 * 1024 <= limit <= 1024 * 1024 * 1024:
        raise ValueError('maxVideoBytes must be between 1 MiB and 1 GiB')
    age = time.time() - lease.stat().st_mtime if lease.exists() else None
    reason = session_stop(stop=stop.exists(), lease_age=age, size=0, limit=limit)
    if reason:raise RuntimeError('Prepare a live outside observer before capture: ' + reason)
    # A prior incomplete cleanup is disclosed; never silently resume or overwrite it.
    if any(base.glob('camera-*/pending-cleanup.json')):
        raise RuntimeError('A previous pending cleanup needs local review before a new attempt')
    session = base / ('camera-' + uuid.uuid4().hex)
    session.mkdir()
    video = session / 'video.mkv'
    pending = session / 'pending-cleanup.json'
    identity = dict(session=session.name, pid=os.getpid(), video=str(video.resolve()))
    save(pending, identity)
    process = None
    readers = []
    errors, progress = deque(maxlen=30), {}
    reason, shutdown_error = 'startup-failure', None
    started = time.time()

    def publish(state, **extra):
        save(base / 'camera-active.json', dict(identity, state=state,
             at=time.time(), startedAt=started, **extra))

    def consume(stream, is_progress):
        try:
            for line in iter(stream.readline, ''):
                if is_progress and '=' in line:
                    key, value = line.strip().split('=', 1)
                    progress[key] = value
                elif not is_progress:errors.append(line.strip())
        except (ValueError, OSError):
            pass  # The owner closes pipe readers only after child termination.

    try:
        process = subprocess.Popen(record_command(config, video), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf8', errors='replace',
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        for stream, flag in ((process.stdout, True), (process.stderr, False)):
            reader=threading.Thread(target=consume, args=(stream, flag), daemon=True)
            readers.append(reader);reader.start()
        emit(event='started', **identity, capturePid=process.pid)
        while process.poll() is None:
            size = video.stat().st_size if video.exists() else 0
            age = time.time() - lease.stat().st_mtime if lease.exists() else None
            reason = session_stop(stop=stop.exists(), lease_age=age, size=size, limit=limit)
            publish('capturing', capturePid=process.pid, bytes=size,
                    frames=int(progress.get('frame', 0)), outputMicroseconds=progress.get('out_time_us'))
            if reason:break
            if time.time() - started > 15 and int(progress.get('frame', 0)) == 0:
                reason = 'no-first-frame';break
            time.sleep(.25)
        if not reason:reason = 'capture-process-exited'
    except KeyboardInterrupt:
        reason = 'operator-interrupt'
    except Exception as error:
        shutdown_error = dict(type=type(error).__name__, message=str(error))
    finally:
        if process and process.poll() is None:
            try:
                process.stdin.write('q\n');process.stdin.flush();process.wait(timeout=8)
            except (OSError, subprocess.TimeoutExpired):
                process.kill();process.wait(timeout=5)
                shutdown_error = dict(type='ForcedTermination', message='Encoder did not finalize on stop')
        if process:
            for reader in readers:reader.join(timeout=2)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream:stream.close()

        def verify(path):
            local = inspect_video(config, path)
            publish('awaiting-validation', capturePid=process.pid if process else None)
            deadline = time.monotonic() + 20
            acknowledgment = session / 'observer-validation.json'
            outside = None
            while time.monotonic() < deadline:
                if acknowledgment.exists():
                    candidate = json.loads(acknowledgment.read_text('utf8'))
                    if candidate.get('session') == session.name:
                        outside = candidate;break
                time.sleep(.2)
            local['outsideValidation'] = outside
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
            local['independentlyVerified'] = bool(outside and outside.get('valid')
                                                 and outside.get('sha256')==digest.hexdigest())
            return local

        result = finish_video(video, verify)
        result.update(identity, event='summary', stoppedAt=time.time(), stopReason=reason,
                      exitCode=process.returncode if process else None,
                      shutdownError=shutdown_error, diagnostics=list(errors), mediaRetained=False)
        if not result['deleted']:result['mediaRetained'] = True
        save(session / 'audit.json', result)
        if result['deleted']:pending.unlink(missing_ok=True)
        publish('stopped', result=result)
        emit(**result)
    return 0 if (result['valid'] and result.get('independentlyVerified') and result['deleted']
                 and shutdown_error is None and reason in ('requested-stop', 'operator-interrupt')) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('.arena-device-local/camera-fixture.json'))
    args = parser.parse_args()
    if os.name != 'nt':raise SystemExit('Windows is required')
    try:
        path = args.config.resolve()
        if path.parent.name != '.arena-device-local':raise ValueError('Fixture must be inside .arena-device-local')
        config = json.loads(path.read_text('utf8'))
        if config.get('controlledSourcesConfirmed') is not True:raise ValueError('Controlled source confirmation is required')
        for key in ('ffmpeg', 'ffprobe', 'cameraDevice'):
            if not isinstance(config.get(key), str) or not config[key].strip():raise ValueError('Missing ' + key)
        for key in ('ffmpeg','ffprobe'):config[key]=resolve_tool(config[key],path.parent)
        return run(config, path.parent)
    except Exception as error:
        emit(event='failure', errorType=type(error).__name__, error=str(error));return 1


if __name__ == '__main__':raise SystemExit(main())
