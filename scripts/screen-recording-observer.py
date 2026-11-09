"""Outside recording panel. FFprobe the workspace MP4; never preview or delete it."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import threading
import time


def save(path, data):
    path = Path(path)
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


def support():
    path = Path(__file__).with_name('device-observer.py')
    spec = importlib.util.spec_from_file_location('shared_recording_observer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def saved_videos(folder, since):
    folder = Path(folder)
    if not folder.is_dir():
        return []
    files = []
    for path in sorted(folder.glob('screen-*.mp4')):
        try:
            if not path.is_file():
                continue
            stat = path.stat()
        except FileNotFoundError:
            continue
        if stat.st_mtime >= since and stat.st_size > 0:
            files.append(dict(path=str(path), bytes=stat.st_size, modifiedAt=stat.st_mtime))
    return files


def panel_layout():
    return dict(height=480, textSide='top', bottomPad=96, bottomExpand=True)


def panel_geometry(screen_width, screen_height):
    layout = panel_layout()
    width = max(480, screen_width // 2)
    height = layout['height']
    return dict(width=width, height=height,
                x=max(0, (screen_width - width) // 2), y=0)


def recording_status(active):
    active = active or {}
    state = active.get('state')
    if state == 'capturing':
        return 'Recording'
    result = active.get('result') or {}
    if state == 'stopped' and result.get('mediaSaved'):
        return 'Saved'
    return 'Closed'


def recording_label(status, language='en'):
    labels = {
        'en': {
            'Recording': 'Recording',
            'Saved': 'Saved',
            'Closed': 'Closed',
            'Observation unavailable': 'Observation unavailable',
        },
        'zh-CN': {
            'Recording': '正在录制',
            'Saved': '已保存',
            'Closed': '已关闭',
            'Observation unavailable': '无法观测',
        },
    }
    return labels.get(language, labels['en']).get(status, status)


def inspect_recording_file(config, base, video):
    """Outside validation of the declared workspace MP4. No preview or deletion."""
    video = Path(video).resolve()
    workspace = Path(base).resolve().parent
    folder = (workspace / 'screen-recordings').resolve()
    if video.parent != folder or not video.name.startswith('screen-') or video.suffix != '.mp4':
        raise ValueError('Video path escapes the declared workspace recordings')
    result = dict(valid=False, deleted=False, at=time.time(), video=str(video))
    try:
        completed = subprocess.run(
            [config['ffprobe'], '-v', 'error', '-count_frames', '-select_streams', 'v:0',
             '-show_entries', 'stream=codec_type,nb_read_frames:format=duration',
             '-of', 'json', str(video)],
            capture_output=True, timeout=60,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        data = json.loads(completed.stdout)
        streams = data.get('streams', [])
        frames = int(streams[0].get('nb_read_frames', 0)) if streams else 0
        duration = float(data.get('format', {}).get('duration', 0))
        digest = hashlib.sha256()
        with video.open('rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
        result.update(
            valid=bool(completed.returncode == 0 and frames > 0 and duration > 0
                       and streams and streams[0].get('codec_type') == 'video'),
            frames=frames, durationSeconds=duration, sha256=digest.hexdigest(),
            bytes=video.stat().st_size, deleted=False)
    except Exception as error:
        result['error'] = str(error)
    save(Path(base) / 'observer-validation.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--language', choices=('en', 'zh-CN'), default='en')
    parser.add_argument('--ready-file', type=Path)
    args = parser.parse_args()
    if os.name != 'nt':
        raise SystemExit('Windows is required')
    path = args.config
    if path.parent.name != '.arena-device-local':
        raise SystemExit('Prepared fixture directory is required')
    config = json.loads(path.read_text('utf-8-sig'))
    if config.get('controlledSourcesConfirmed') is not True or config.get('captureScope') != 'primary-screen':
        raise SystemExit('Primary-screen capture scope has not been prepared')
    tool = config.get('ffprobe')
    if not tool:
        raise SystemExit('Prepared FFprobe is required')
    executable = ((Path(tool) if Path(tool).is_absolute() else path.parent / tool)
                  if ('/' in str(tool) or '\\' in str(tool)) else Path(__import__('shutil').which(tool) or tool))
    if not executable.is_file():
        raise SystemExit('Prepared FFprobe not found')
    config['ffprobe'] = str(executable.resolve())
    common = support()
    import ctypes
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    import tkinter as tk
    root = tk.Tk()
    root.title('')
    root.configure(bg='white')
    root.attributes('-topmost', True)
    root.update_idletasks()
    box = panel_geometry(root.winfo_screenwidth(), root.winfo_screenheight())
    root.geometry('%dx%d+%d+%d' % (box['width'], box['height'], box['x'], box['y']))
    layout = panel_layout()
    text = tk.Frame(root, bg='white')
    title = tk.Label(text, text='Screen recording' if args.language == 'en' else '录屏',
                     font=('Segoe UI', 22, 'bold'), bg='white')
    status = tk.StringVar(value=recording_label('Closed', args.language))
    status_label = tk.Label(text, textvariable=status, font=('Segoe UI', 28, 'bold'),
                            wraplength=box['width'] - 48, bg='white')
    detail = tk.StringVar(value='')
    detail_label = tk.Label(text, textvariable=detail, font=('Segoe UI', 16),
                            wraplength=box['width'] - 48, bg='white')
    title.pack(side='top', pady=(28, 10))
    status_label.pack(side='top', pady=10)
    detail_label.pack(side='top', pady=(8, 0))
    text.pack(side='top', fill='x')
    spacer = tk.Frame(root, bg='white', height=layout['bottomPad'])
    spacer.pack(side='top', fill='both', expand=layout['bottomExpand'])
    spacer.pack_propagate(False)
    validated = set()
    active_path = path.parent / 'screen-recording-active.json'

    def tick():
        try:
            active = json.loads(active_path.read_text('utf8')) if active_path.is_file() else {}
            shown = recording_status(active)
            if shown == 'Saved':
                video = Path(active.get('video') or (active.get('result') or {}).get('output') or '')
                if video and str(video) not in validated:
                    validated.add(str(video))
                    threading.Thread(
                        target=inspect_recording_file,
                        args=(config, path.parent, video),
                        daemon=True).start()
            validation = {}
            report = path.parent / 'observer-validation.json'
            if report.is_file():
                validation = json.loads(report.read_text('utf8'))
            result = active.get('result') or {}
            duration = validation.get('durationSeconds', result.get('durationSeconds') or 0)
            frames = validation.get('frames', 0)
            size = validation.get('bytes', result.get('bytes') or 0)
            detail.set('%.1f s | %s frames | %s bytes' % (float(duration or 0), frames, size))
            color_key = 'Active' if shown in ('Recording', 'Saved') else 'Idle'
            background, ink = common.panel_colors(color_key)
            status.set(recording_label(shown, args.language))
        except Exception:
            background, ink = common.panel_colors('Observation unavailable')
            status.set(recording_label('Observation unavailable', args.language))
            detail.set('')
        root.configure(bg=background)
        text.configure(bg=background)
        spacer.configure(bg=background)
        for widget in (title, status_label, detail_label):
            widget.configure(bg=background, fg=ink)
        root.after(500, tick)

    tick()
    root.update_idletasks()
    if args.ready_file:
        temporary = args.ready_file.with_suffix('.tmp')
        temporary.write_text(json.dumps(dict(pid=os.getpid(), startedAt=time.time(),
                                             directory=str((path.parent.parent / 'screen-recordings').absolute()))),
                             encoding='utf8')
        temporary.replace(args.ready_file)
    root.mainloop()


if __name__ == '__main__':
    main()
