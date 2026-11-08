"""Outside device-state panel. Run separately from the tested worker boundary."""
import argparse
import ctypes as c
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time


def save(path,data):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(data,indent=2),encoding='utf8')
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05)


def panel_colors(shown):
    if shown in ('Open','Open (other process)','Active','Muted'):
        return '#c42020','white'
    if shown in ('Closed','Inactive','Unmuted','Idle'):
        return 'white','#141414'
    return '#ececec','#141414'


def capture_images_dir(config_path):
    path=Path(config_path).resolve()
    if path.parent.name!='.arena-device-local':raise ValueError('Fixture must be inside .arena-device-local')
    return path.parent.parent/'screen-captures'


def count_capture_images(folder, since):
    folder=Path(folder)
    if not folder.is_dir():return 0
    total=0
    for item in folder.glob('*.png'):
        if item.stat().st_mtime<since:continue
        try:
            if item.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n':total+=1
        except OSError:continue
    return total


def camera_state(report,target_pids,*,now):
    if not report or now-report['at']>5:return 'Observation unavailable'
    active={item['pid'] for item in report.get('processes',[]) if item['streaming']}
    if active & target_pids:return 'Open'
    if active:return 'Open (other process)'
    return 'Closed'


def load_audio():
    path=Path(__file__).resolve().parents[1]/'scenarios/speaker-mute/input/speaker-mute.py'
    spec=importlib.util.spec_from_file_location('audited_endpoint',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class CaptureSessions:
    """Read capture-endpoint session state; never acquire microphone samples."""
    def __init__(self,audio,identity):
        self.audio=audio;self.endpoint=audio.Endpoint(identity);self.manager=c.c_void_p()
        iid=audio.GUID.of('77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F')
        try:
            audio.checked(audio.com_call(self.endpoint.device,3,[c.POINTER(audio.GUID),c.c_ulong,c.c_void_p,c.POINTER(c.c_void_p)],
                                        c.byref(iid),23,None,c.byref(self.manager)))
        except BaseException:self.close();raise

    def read(self):
        a=self.audio;enumerator=c.c_void_p();active=[]
        try:
            a.checked(a.com_call(self.manager,5,[c.POINTER(c.c_void_p)],c.byref(enumerator)))
            count=c.c_int();a.checked(a.com_call(enumerator,3,[c.POINTER(c.c_int)],c.byref(count)))
            for i in range(count.value):
                control=c.c_void_p();extended=c.c_void_p()
                try:
                    a.checked(a.com_call(enumerator,4,[c.c_int,c.POINTER(c.c_void_p)],i,c.byref(control)))
                    state=c.c_int();a.checked(a.com_call(control,3,[c.POINTER(c.c_int)],c.byref(state)))
                    iid=a.GUID.of('BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D')
                    a.checked(a.com_call(control,0,[c.POINTER(a.GUID),c.POINTER(c.c_void_p)],c.byref(iid),c.byref(extended)))
                    pid=c.c_ulong();a.checked(a.com_call(extended,14,[c.POINTER(c.c_ulong)],c.byref(pid)))
                    if state.value==1:active.append(pid.value)
                finally:
                    if extended.value:a.com_call(extended,2,[])
                    if control.value:a.com_call(control,2,[])
            return active
        finally:
            if enumerator.value:a.com_call(enumerator,2,[])

    def close(self):
        if self.manager.value:self.audio.com_call(self.manager,2,[]);self.manager=c.c_void_p()
        self.endpoint.close()


def inspect_camera_file(config,base,active):
    """Outside validation of only the declared attempt file. No image preview."""
    session=(base/active['session']).resolve();video=Path(active['video']).resolve()
    if (session.parent!=base or not session.name.startswith('camera-') or
            video.parent!=session or video.name!='video.mkv'):
        raise ValueError('Video path escapes the declared temporary attempt')
    result=dict(session=session.name,valid=False,at=time.time())
    try:
        completed=subprocess.run([config['ffprobe'],'-v','error','-count_frames','-select_streams','v:0',
            '-show_entries','stream=codec_type,nb_read_frames:format=duration','-of','json',str(video)],
            capture_output=True,timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        data=json.loads(completed.stdout);streams=data.get('streams',[])
        frames=int(streams[0].get('nb_read_frames',0)) if streams else 0
        duration=float(data.get('format',{}).get('duration',0))
        digest=hashlib.sha256()
        with video.open('rb') as source:
            for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
        result.update(valid=bool(completed.returncode==0 and frames>0 and duration>0 and streams[0]['codec_type']=='video'),
                      frames=frames,durationSeconds=duration,sha256=digest.hexdigest(),bytes=video.stat().st_size)
    except Exception as error:result['error']=str(error)
    save(session/'observer-validation.json',result)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('camera','microphone','speaker','screen'))
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--language',choices=('en','zh-CN'),default='en')
    args=parser.parse_args()
    if os.name!='nt':raise SystemExit('Windows is required')
    path=args.config.resolve();base=path.parent
    if base.name!='.arena-device-local':raise SystemExit('Fixture must be inside .arena-device-local')
    config=json.loads(path.read_text('utf8'))
    if config.get('controlledSourcesConfirmed') is not True:raise SystemExit('Prepare and confirm controlled resources first')
    if args.mode=='camera':
        tool=config['ffprobe']
        executable=(Path(tool) if Path(tool).is_absolute() else base/tool) if ('/' in tool or '\\' in tool) else Path(shutil.which(tool) or tool)
        if not executable.is_file():raise SystemExit('Prepared FFprobe not found')
        config['ffprobe']=str(executable.resolve())
    if args.mode=='screen':
        dpi_user=c.WinDLL('user32',use_last_error=True)
        dpi_user.SetProcessDpiAwarenessContext.argtypes=[c.c_void_p]
        dpi_user.SetProcessDpiAwarenessContext(c.c_void_p(-4))
    # Tk import and all native access occur only on explicit observer execution.
    import tkinter as tk
    root=tk.Tk();root.title('Arena device observer');root.geometry('900x320+280+60')
    root.attributes('-topmost',True)
    root.configure(bg='white')
    title=tk.Label(root,text=args.mode.title(),font=('Segoe UI',22,'bold'),bg='white');title.pack(pady=12)
    status=tk.StringVar(value='Observation unavailable')
    status_label=tk.Label(root,textvariable=status,font=('Segoe UI',28,'bold'),wraplength=860,bg='white')
    status_label.pack(pady=8)
    detail=tk.StringVar(value='');detail_label=tk.Label(root,textvariable=detail,font=('Segoe UI',16),wraplength=860,bg='white')
    detail_label.pack()
    translations={'Open':'已开启','Closed':'已关闭','Open (other process)':'已开启（其他进程）',
                  'Observation unavailable':'无法观测','Recording':'正在录制','Stopped':'已停止',
                  'Muted':'已静音','Unmuted':'未静音','Active':'正在采集','Inactive':'未采集',
                  'Awaiting verification':'等待实际观测'}
    def show(text):return translations.get(text,text) if args.language=='zh-CN' else text
    events=queue.Queue();camera_report=None;helper=None;endpoint=None;sessions=None
    validation_started=set();closing_at=None;panel_started=time.time();pattern=None
    user=None
    if args.mode=='camera':
        (base/'camera.stop').unlink(missing_ok=True)
        executable=Path(config.get('cameraActivityHelper',str(base/'camera-activity.exe')))
        if not executable.is_absolute():executable=(path.parent/executable).resolve()
        helper=subprocess.Popen([str(executable),config['cameraSymbolicLink']],stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf8',
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        def read_events():
            for line in helper.stdout:
                try:events.put(json.loads(line))
                except ValueError:events.put(dict(kind='unavailable'))
        threading.Thread(target=read_events,daemon=True).start()
    elif args.mode in ('speaker','microphone'):
        audio=load_audio()
        if args.mode=='speaker':endpoint=audio.Endpoint(config['endpointId'])
        else:sessions=CaptureSessions(audio,config['endpointId'])
    else:
        user=c.WinDLL('user32',use_last_error=True)
        user.SetProcessDpiAwarenessContext.argtypes=[c.c_void_p];user.SetProcessDpiAwarenessContext(c.c_void_p(-4))
        user.GetAncestor.argtypes=[c.c_void_p,c.c_uint];user.GetAncestor.restype=c.c_void_p
        pattern=tk.Toplevel(root);pattern.overrideredirect(True);pattern.geometry('160x90+60+60')
        pattern.configure(bg='#1765b5');pattern.attributes('-topmost',True);pattern.update()
        config.update(hwnd=int(user.GetAncestor(pattern.winfo_id(),2)),fixturePid=os.getpid(),screenX=pattern.winfo_rootx(),screenY=pattern.winfo_rooty(),
                      fixtureKind='solid-1765b5-160x90')
        save(path,config);detail.set('Owned 160x90 test-pattern window is ready')

    def request_stop():
        nonlocal closing_at
        if args.mode=='camera':
            (base/'camera.stop').touch();closing_at=closing_at or time.monotonic()
        else:root.destroy()
    tk.Button(root,text='Stop' if args.language=='en' else '停止',font=('Segoe UI',14),command=request_stop).pack(pady=15)
    root.protocol('WM_DELETE_WINDOW',request_stop)

    def tick():
        nonlocal camera_report
        try:
            if args.mode=='camera':
                (base/'camera.lease').touch()
                while not events.empty():
                    item=events.get_nowait()
                    camera_report=dict(item,at=time.time()) if item.get('kind')=='camera-activity' else None
                    with (base/'camera-os-activity.jsonl').open('a',encoding='utf8') as stream:stream.write(json.dumps(dict(item,at=time.time()))+'\n')
                active_file=base/'camera-active.json'
                active=json.loads(active_file.read_text('utf8')) if active_file.exists() else {}
                if active.get('startedAt',0)<panel_started:active={}
                pids={p for p in (active.get('pid'),active.get('capturePid')) if p}
                observed=camera_state(camera_report,pids,now=time.time())
                shown='Open' if observed=='Open (other process)' else observed
                status.set(show(shown))
                panel,ink=panel_colors(shown)
                root.configure(bg=panel)
                for widget in (title,status_label,detail_label):widget.configure(bg=panel,fg=ink)
                video=Path(active['video']) if active.get('video') else None
                # File metadata is a separate observation, never the OS camera flag.
                size=video.stat().st_size if video and video.is_file() else 0
                result=active.get('result',{})
                state=active.get('state')
                recording=('Recording' if state=='capturing' and observed=='Open' and
                           size>0 and int(active.get('frames',0))>0 else
                           'Stopped' if state=='stopped' else 'Awaiting verification')
                duration=(result.get('durationSeconds',0) if state=='stopped' else
                          int(active.get('outputMicroseconds') or 0)/1000000)
                detail.set('%s | %.1f s | %d bytes%s' % (show(recording) if active else '-',
                           duration,result.get('bytes',size),
                           ' | Other process' if observed=='Open (other process)' else ''))
                if active.get('state')=='awaiting-validation' and active['session'] not in validation_started:
                    validation_started.add(active['session'])
                    def validate(snapshot):
                        try:inspect_camera_file(config,base,snapshot)
                        except Exception as error:events.put(dict(kind='validation-error',error=str(error)))
                    threading.Thread(target=validate,args=(dict(active),),daemon=True).start()
                if helper.poll() is None:
                    helper.stdin.write('poll\n');helper.stdin.flush()
                else:
                    camera_report=None
                    status.set(show('Observation unavailable'))
                    panel,ink=panel_colors('Observation unavailable')
                    root.configure(bg=panel)
                    for widget in (title,status_label,detail_label):widget.configure(bg=panel,fg=ink)
                if closing_at and (active.get('state')=='stopped' or time.monotonic()-closing_at>30):root.destroy();return
            elif endpoint:
                state=endpoint.state();status.set(show('Muted' if state['muted'] else 'Unmuted'))
                detail.set('Volume: %.0f%%' % (state['volume']*100))
                with (base/'speaker-observations.jsonl').open('a',encoding='utf8') as stream:stream.write(json.dumps(dict(state,at=time.time()))+'\n')
            elif sessions:
                active=sessions.read();shown='Active' if active else 'Inactive'
                status.set(show(shown))
                panel,ink=panel_colors(shown)
                root.configure(bg=panel)
                for widget in (title,status_label,detail_label):widget.configure(bg=panel,fg=ink)
                detail.set('OS endpoint session PIDs: '+str(active))
                with (base/'microphone-os-activity.jsonl').open('a',encoding='utf8') as stream:stream.write(json.dumps(dict(activePids=active,at=time.time()))+'\n')
            else:
                count=count_capture_images(capture_images_dir(path), panel_started)
                shown='Idle' if count==0 else 'Active'
                status.set(('Saved images: %d' % count) if args.language=='en' else ('已保存图片：%d' % count))
                panel,ink=panel_colors(shown)
                root.configure(bg=panel)
                for widget in (title,status_label,detail_label):widget.configure(bg=panel,fg=ink)
                detail.set('Owned 160x90 test-pattern window is ready')
        except Exception as error:
            status.set(show('Observation unavailable'))
            detail.set(type(error).__name__+': '+str(error))
            panel,ink=panel_colors('Observation unavailable')
            root.configure(bg=panel)
            for widget in (title,status_label,detail_label):widget.configure(bg=panel,fg=ink)
        root.after(1000,tick)

    try:tick();root.mainloop()
    finally:
        if args.mode=='camera':
            (base/'camera.lease').unlink(missing_ok=True)
            if helper and helper.poll() is None:
                try:helper.stdin.write('stop\n');helper.stdin.flush();helper.wait(timeout=5)
                except (OSError,subprocess.TimeoutExpired):helper.kill();helper.wait(timeout=5)
        if endpoint:endpoint.close()
        if sessions:sessions.close()


if __name__=='__main__':main()
