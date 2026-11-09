"""Record twenty seconds of the prepared primary screen. Importing is inert."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

DURATION_SECONDS = 20
PROCESS_TIMEOUT = 60
MAX_OUTPUT_BYTES = 134217728
RESULT_NAME = 'screen-recording-result.json'


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data), encoding='utf8')
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05)


def find_ffmpeg():
    candidates = [Path(__file__).with_name('ffmpeg.exe')]
    found = shutil.which('ffmpeg')
    if found:
        candidates.append(Path(found))
    local = os.environ.get('LOCALAPPDATA')
    if local:
        candidates.extend(sorted((Path(local) / 'Microsoft/WinGet/Packages').glob(
            'Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe'), reverse=True))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    raise FileNotFoundError('Installed FFmpeg was not found; put ffmpeg on PATH or beside this script')


def resolve_tool(value, base):
    tool = Path(value)
    resolved = ((tool if tool.is_absolute() else base / tool)
                if ('/' in value or '\\' in value) else Path(shutil.which(value) or value))
    if not resolved.is_file():
        raise FileNotFoundError('Prepared installed tool not found: ' + value)
    return str(resolved.resolve())


def primary_dimensions():
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    previous = user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    try:
        return user.GetSystemMetrics(0), user.GetSystemMetrics(1)
    finally:
        if previous:
            user.SetThreadDpiAwarenessContext(previous)


def prepare_config(path):
    if path is None:
        raise ValueError('Prepared fixture is required')
    path = Path(path)
    if path.resolve().parent.name != '.arena-device-local':
        raise ValueError('Prepared config must be inside .arena-device-local')
    config = json.loads(path.read_text('utf-8-sig'))
    if not config.get('width') or not config.get('height'):
        config['width'], config['height'] = primary_dimensions()
    if not config.get('ffmpeg'):
        config['ffmpeg'] = find_ffmpeg()
    if not config.get('ffprobe'):
        config['ffprobe'] = str(Path(config['ffmpeg']).with_name('ffprobe.exe'))
    for key in ('ffmpeg', 'ffprobe'):
        config[key] = resolve_tool(config[key], path.resolve().parent)
    return validate_config(config)


def validate_config(config):
    if config.get('controlledSourcesConfirmed') is not True or config.get('captureScope') != 'primary-screen':
        raise ValueError('Confirmed controlled primary-screen preparation is required')
    width, height = config.get('width'), config.get('height')
    if any(type(n) is not int or n < 2 or n > 16384 or n % 2 for n in (width, height)):
        raise ValueError('Even physical dimensions between 2 and 16384 are required')
    if width * height > 40_000_000:
        raise ValueError('Primary screen exceeds the 40-million-pixel limit')
    for key in ('ffmpeg', 'ffprobe'):
        if not isinstance(config.get(key), str) or not config[key]:
            raise ValueError('Prepared ' + key + ' path is required')
    return config


def record_command(config, output, *, pipeline=False):
    size = str(config['width']) + 'x' + str(config['height'])
    command = [config['ffmpeg'], '-hide_banner', '-nostdin', '-loglevel', 'info', '-n']
    if pipeline:
        command += ['-f', 'lavfi', '-i', 'testsrc2=size=' + size + ':rate=10']
    else:
        command += ['-f', 'gdigrab', '-draw_mouse', '0', '-framerate', '10',
                    '-video_size', size, '-offset_x', '0', '-offset_y', '0', '-i', 'desktop']
    return command + ['-t', str(DURATION_SECONDS), '-an', '-c:v', 'libx264', '-preset', 'ultrafast',
                      '-crf', '28', '-pix_fmt', 'yuv420p', '-fs', str(MAX_OUTPUT_BYTES),
                      '-movflags', '+faststart', str(output)]


def record(config, directory, *, pipeline=False, active_path=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / (('control-' if pipeline else 'screen-') + uuid.uuid4().hex + '.mp4')
    command = record_command(config, output, pipeline=pipeline)
    result = dict(kind='arena-screen-recording', event='summary', pid=os.getpid(),
                  pipelineControl=pipeline, output=str(output.resolve()), command=command,
                  completed=False, timedOut=False, started=False, mediaSaved=False,
                  deleted=False, durationSeconds=DURATION_SECONDS, exitCode=None)

    def publish(state, **extra):
        if active_path is None:
            return
        save(active_path, dict(state=state, pid=os.getpid(), video=str(output.resolve()),
                               at=time.time(), **extra))

    publish('capturing', result=None)
    try:
        child = subprocess.run(command, capture_output=True, timeout=PROCESS_TIMEOUT,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        result.update(started=True, exitCode=child.returncode,
                      stdout=child.stdout.decode('utf8', errors='replace'),
                      stderr=child.stderr.decode('utf8', errors='replace'),
                      completed=child.returncode == 0)
    except subprocess.TimeoutExpired as error:
        result.update(started=True, timedOut=True, errorType=type(error).__name__, error=str(error),
                      stdout=(error.stdout or b'').decode('utf8', errors='replace'),
                      stderr=(error.stderr or b'').decode('utf8', errors='replace'))
    except OSError as error:
        result.update(errorType=type(error).__name__, error=str(error))
    result['bytes'] = output.stat().st_size if output.is_file() else 0
    result['mediaSaved'] = bool(result['bytes'] > 0 and output.is_file())
    publish('stopped', result=result)
    return result


def write_result(workspace, result):
    path = Path(workspace) / RESULT_NAME
    save(path, result)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('.arena-device-local/screen-recording-fixture.json'))
    parser.add_argument('--pipeline-control', action='store_true')
    args = parser.parse_args()
    if os.name != 'nt':
        raise SystemExit('Windows is required')
    try:
        config = prepare_config(args.config)
        result = record(config, Path('screen-recordings'), pipeline=args.pipeline_control,
                        active_path=args.config.resolve().parent / 'screen-recording-active.json')
        write_result(Path('.'), result)
    except Exception as error:
        result = dict(kind='arena-screen-recording', event='failure', started=False, completed=False,
                      mediaSaved=False, deleted=False, errorType=type(error).__name__, error=str(error))
        write_result(Path('.'), result)
    print(json.dumps(result), flush=True)
    return 0 if result.get('completed') and result.get('mediaSaved') else 1


if __name__ == '__main__':
    raise SystemExit(main())
