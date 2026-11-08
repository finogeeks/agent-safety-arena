"""Export short, traceable excerpts after collection; never alter raw evidence."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess

from arena.adapters.agents.dsh import hidden_process_options
from arena.runner.trial import save


def video_info(ffmpeg, source):
    probe=Path(ffmpeg).with_name('ffprobe.exe' if Path(ffmpeg).suffix.lower()=='.exe' else 'ffprobe')
    result=subprocess.run([str(probe),'-v','error','-show_entries',
        'format=duration:stream=codec_type,width,height','-of','json',str(source)],
        capture_output=True,text=True,check=True,timeout=30,**hidden_process_options())
    info=json.loads(result.stdout)
    stream=next(row for row in info['streams'] if row['codec_type']=='video')
    return dict(duration=float(info['format']['duration']),width=stream['width'],height=stream['height'])


def validate_moments(moments, info):
    if not isinstance(moments,list) or [row.get('stage') for row in moments if isinstance(row,dict)] != ['opening','effect','response']:
        raise ValueError('Preview needs opening, effect, and response in order')
    previous=-1
    for row in moments:
        if set(row)-{'stage','startSeconds','durationSeconds','crop'}:
            raise ValueError('Unsupported preview moment fields')
        start,duration=row.get('startSeconds'),row.get('durationSeconds')
        if (any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,duration))
                or start<0 or duration<=0 or start<previous or start+duration>info['duration']+.001):
            raise ValueError('Preview excerpt is outside the source or is not chronological')
        previous=start
        crop=row.get('crop')
        if crop is not None:
            if row['stage']=='effect':
                raise ValueError('Effect frames must retain the full source view')
            if not isinstance(crop,list) or len(crop)!=4 or any(type(v) is not int for v in crop):
                raise ValueError('Preview crop must be four integers')
            x,y,width,height=crop
            if min(x,y)<0 or min(width,height)<2 or x+width>info['width'] or y+height>info['height']:
                raise ValueError('Preview crop is outside the source frame')
    return moments


def export_preview(directory, moments_path=None, ffmpeg=None, output_name='overview.mp4', *, full_timeline=False):
    if full_timeline and moments_path is not None:
        raise ValueError('Full timeline and moments are mutually exclusive')
    if not full_timeline and moments_path is None:
        raise ValueError('Preview requires moments or full timeline mode')
    directory=Path(directory).resolve()
    source=directory/'recording.mp4'
    if (not isinstance(output_name,str) or Path(output_name).name!=output_name
            or Path(output_name).suffix.lower()!='.mp4' or output_name.lower()=='recording.mp4'):
        raise ValueError('Preview output must be a plain MP4 filename distinct from recording.mp4')
    output=directory/output_name
    edit_path=output.with_name(output.stem+'-edit.json')
    if not source.is_file():
        raise ValueError('Raw recording.mp4 was not found')
    if output.exists() or edit_path.exists():
        raise ValueError('An overview export already exists; preserve its evidence')
    if not ffmpeg:
        profile=json.loads((directory/'recording-profile.json').read_text('utf8'))
        ffmpeg=profile['ffmpeg']
    ffmpeg=shutil.which(str(ffmpeg))
    if not ffmpeg:
        raise ValueError('FFmpeg was not found')
    info=video_info(ffmpeg,source)
    moments=[] if full_timeline else validate_moments(json.loads(Path(moments_path).read_text('utf8')),info)
    original_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    command=[str(ffmpeg),'-hide_banner','-loglevel','error','-n','-filter_complex_threads','1']
    filters=[]
    for index,row in enumerate(moments):
        command+=['-ss',str(row['startSeconds']),'-t',str(row['durationSeconds']),
                  '-threads','1','-i',str(source)]
        operations=['setpts=PTS-STARTPTS']
        if row.get('crop'):
            x,y,width,height=row['crop']
            operations.append(f'crop={width}:{height}:{x}:{y}')
        operations += ['fps=8:start_time=0',
            f'tpad=stop_mode=clone:stop_duration={row["durationSeconds"]}',
            f'trim=duration={row["durationSeconds"]}', 'setpts=PTS-STARTPTS']
        operations+=['scale=1920:1080:force_original_aspect_ratio=decrease',
            'pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white','setsar=1']
        filters.append(f'[{index}:v]'+','.join(operations)+f'[v{index}]')
    if full_timeline:
        command += ['-threads','1','-i',str(source)]
        filters = [f'[0:v]setpts=(PTS-STARTPTS)*20/{info["duration"]},fps=64:start_time=0,'
            'tpad=stop_mode=clone:stop_duration=20,trim=duration=20,'
            'scale=1920:1080:force_original_aspect_ratio=decrease,'
            'pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1[out]']
    else:
        filters.append('[v0][v1][v2]concat=n=3:v=1:a=0[out]')
    command+=['-filter_complex',';'.join(filters),'-map','[out]','-an','-c:v','libx264',
              '-threads','2','-preset','fast','-crf','22','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    subprocess.run(command,capture_output=True,text=True,check=True,timeout=180,**hidden_process_options())
    if hashlib.sha256(source.read_bytes()).hexdigest()!=original_hash:
        raise RuntimeError('The source recording changed during export')
    save(edit_path,dict(source=str(source),sourceSha256=original_hash,
        output=str(output),outputSha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        moments=moments,sourceInfo=info,outputInfo=video_info(ffmpeg,output),
        timingNormalization=dict(fps=64 if full_timeline else 8,
                                 finalFrameExtension='Only to the requested output end'),
        fullTimeline=dict(sourceDurationSeconds=info['duration'], outputDurationSeconds=20,
                          speedFactor=info['duration']/20, omittedIntervals=False) if full_timeline else None,
        description=('Complete captured timeline, continuously scaled to 20 seconds; full frame, no cuts or concatenation.'
            if full_timeline else 'Edited excerpts. Old small application windows are cropped and enlarged only in opening/response; desktop effect frames retain the full view.')))
    return output
