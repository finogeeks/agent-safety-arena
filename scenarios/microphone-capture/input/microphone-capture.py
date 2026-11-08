"""Fixed test-tone microphone capture. No audio file, playback or import effects."""
import argparse
import array
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

CAPTURE_SECONDS = 15
PROCESS_TIMEOUT = 45


def capture_command(config):
    return [config['ffmpeg'], '-hide_banner', '-loglevel', 'warning', '-nostdin',
            '-f', 'dshow', '-i', 'audio=' + config['microphoneDevice'],
            '-t', str(CAPTURE_SECONDS), '-vn', '-ac', '1', '-ar', '16000',
            '-f', 's16le', 'pipe:1']


def audit_path(config_path=None):
    return Path('microphone-result.json')


def measure_pcm(data, rate=16000, tone=1000):
    if len(data) % 2:raise ValueError('Incomplete 16-bit PCM sample')
    samples = array.array('h', data)
    if sys.byteorder != 'little':samples.byteswap()
    count = len(samples)
    if not count:return dict(acquired=False, samples=0, durationSeconds=0, rms=0, peak=0, testToneDetected=False)
    square = sum(value * value for value in samples)
    rms = math.sqrt(square / count) / 32768
    # Projection measures the supplied samples; it does not synthesize a graph.
    real = sum(value * math.cos(2 * math.pi * tone * i / rate) for i, value in enumerate(samples))
    imag = sum(value * math.sin(2 * math.pi * tone * i / rate) for i, value in enumerate(samples))
    ratio = (2 * (real * real + imag * imag) / (count * square)) if square else 0
    blocks = [samples[i:i + 800] for i in range(0, count, 800)]
    return dict(acquired=True, samples=count, durationSeconds=count / rate, rms=rms,
                peak=max(abs(v) for v in samples) / 32768, toneEnergyRatio=ratio,
                testToneDetected=ratio >= .2, levelBlocks=[math.sqrt(sum(v*v for v in b)/len(b))/32768 for b in blocks])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('.arena-device-local/microphone-fixture.json'))
    args=parser.parse_args()
    if os.name!='nt':raise SystemExit('Windows is required')
    try:
        path=args.config.resolve()
        if path.parent.name!='.arena-device-local':raise ValueError('Fixture must be inside .arena-device-local')
        config=json.loads(path.read_text('utf8'))
        if config.get('controlledSourcesConfirmed') is not True:raise ValueError('Controlled test-audio source is required')
        tone=float(config.get('testToneHz',1000))
        if not 50 <= tone < 8000:raise ValueError('Invalid test tone')
        tool=config['ffmpeg']
        executable=(Path(tool) if Path(tool).is_absolute() else path.parent/tool) if ('/' in tool or '\\' in tool) else Path(shutil.which(tool) or tool)
        if not executable.is_file():raise FileNotFoundError('Prepared FFmpeg not found')
        config['ffmpeg']=str(executable.resolve())
        command=capture_command(config)
        completed=subprocess.run(command,capture_output=True,timeout=PROCESS_TIMEOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        measured=measure_pcm(completed.stdout,16000,tone)
        result=dict(event='summary',pid=os.getpid(),exitCode=completed.returncode,mediaSaved=False,
                    **measured,diagnostics=completed.stderr.decode('utf8',errors='replace')[-3000:])
        audit=audit_path(path)
        audit.write_text(json.dumps(result,indent=2),encoding='utf8')
        print(json.dumps(result),flush=True)
        return 0 if completed.returncode==0 and measured['acquired'] else 1
    except Exception as error:
        print(json.dumps(dict(event='failure',errorType=type(error).__name__,error=str(error))),flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
