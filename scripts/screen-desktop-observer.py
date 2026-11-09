"""Primary-screen case count panel. It never reads screen pixels or creates a target."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import time


def support():
    path=Path(__file__).with_name('device-observer.py')
    spec=importlib.util.spec_from_file_location('shared_count_observer',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def count_saved(folder,since):
    # Reuse the existing criterion, including its signature and freshness checks.
    return support().count_capture_images(folder,since)


def panel_geometry(screen_width,screen_height):
    width=max(480,screen_width//2)
    height=max(240,screen_height//2)
    return dict(width=width,height=height,
                x=max(0,(screen_width-width)//2),y=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--language',choices=('en','zh-CN'),default='en')
    parser.add_argument('--ready-file',type=Path)
    args=parser.parse_args()
    if os.name!='nt':raise SystemExit('Windows is required')
    # Preserve a workspace junction's lexical path when locating image output.
    path=args.config
    if path.parent.name!='.arena-device-local':raise SystemExit('Prepared fixture directory is required')
    config=json.loads(path.read_text('utf-8-sig'))
    if config.get('controlledSourcesConfirmed') is not True or config.get('captureScope')!='primary-screen':
        raise SystemExit('Primary-screen capture scope has not been prepared')
    images=path.parent.parent/'screen-captures'
    common=support()
    import ctypes
    user=ctypes.WinDLL('user32',use_last_error=True)
    user.SetProcessDpiAwarenessContext.argtypes=[ctypes.c_void_p]
    user.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    import tkinter as tk
    root=tk.Tk();root.title('');root.configure(bg='white')
    root.attributes('-topmost',True);root.update_idletasks()
    box=panel_geometry(root.winfo_screenwidth(),root.winfo_screenheight())
    root.geometry('%dx%d+%d+%d'%(box['width'],box['height'],box['x'],box['y']))
    status=tk.StringVar(value=common.screen_status(0,args.language))
    label=tk.Label(root,textvariable=status,font=('Segoe UI',36,'bold'),bg='white',fg='#141414',
                   wraplength=box['width']-48,justify='center',anchor='center')
    label.pack(expand=True,fill='both')
    started=time.time()
    def tick():
        try:
            count=common.count_capture_images(images,started)
            background,ink=common.panel_colors('Active' if count else 'Idle')
            status.set(common.screen_status(count,args.language))
        except Exception:
            background,ink=common.panel_colors('Observation unavailable')
            status.set('Observation unavailable' if args.language=='en' else '无法观测')
        root.configure(bg=background);label.configure(bg=background,fg=ink)
        root.after(1000,tick)
    tick();root.update_idletasks()
    if args.ready_file:
        temporary=args.ready_file.with_suffix('.tmp')
        temporary.write_text(json.dumps(dict(pid=os.getpid(),startedAt=started)),encoding='utf8')
        temporary.replace(args.ready_file)
    root.mainloop()


if __name__=='__main__':main()
