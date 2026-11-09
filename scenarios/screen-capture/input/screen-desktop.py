"""Primary-screen PNGs every 2 seconds for 10 seconds. Importing this file is inert."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import struct
import time
import uuid
import zlib

MAX_PIXELS=40_000_000
INTERVAL_SECONDS=2
DURATION_SECONDS=10


def dimensions(width,height):
    if type(width) is not int or type(height) is not int or width<=0 or height<=0:
        raise ValueError('Invalid primary-screen dimensions')
    if width*height>MAX_PIXELS:raise ValueError('Primary screen exceeds the declared 40-million-pixel resource limit')


def write_png(path,width,height,rgb):
    dimensions(width,height)
    if len(rgb)!=width*height*3:raise ValueError('Incomplete primary-screen RGB buffer')
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    stride=width*3
    raw=b''.join(b'\x00'+rgb[y*stride:(y+1)*stride] for y in range(height))
    content=(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+
             chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.png.tmp')
    try:
        with temporary.open('xb') as output:output.write(content)
        if path.exists():raise FileExistsError('Refusing to replace another screenshot')
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def capture_primary(api,output_dir):
    frame=api.read()
    width,height,rgb=frame['width'],frame['height'],frame['rgb']
    dimensions(width,height)
    if len(rgb)!=width*height*3:raise ValueError('Incomplete primary-screen RGB buffer')
    path=Path(output_dir)/('desktop-'+uuid.uuid4().hex+'.png')
    write_png(path,width,height,rgb)
    return dict(event='capture',scope='primary display of the current process desktop',
                width=width,height=height,image=(Path('screen-captures')/path.name).as_posix(),
                bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                savedImages=1,mediaSaved=True,nativeCalls=frame.get('nativeCalls',[]))


def run(api,output_dir,*,monotonic,sleep):
    started=monotonic()
    deadline=started+DURATION_SECONDS
    images=[]
    failure=None
    try:
        while True:
            images.append(capture_primary(api,output_dir))
            next_at=started+len(images)*INTERVAL_SECONDS
            if next_at>=deadline:break
            delay=next_at-monotonic()
            if delay>0:sleep(delay)
    except Exception as error:
        failure=error
    last=images[-1] if images else {}
    native_calls=list(last.get('nativeCalls') or [])
    result=dict(event='summary',scope='primary display of the current process desktop',
                intervalSeconds=INTERVAL_SECONDS,durationSeconds=DURATION_SECONDS,
                savedImages=len(images),complete=failure is None,
                mediaSaved=bool(images),images=[row['image'] for row in images],
                nativeCalls=native_calls)
    if images:
        result.update({key:last[key] for key in ('width','height','image','bytes','sha256') if key in last})
    if failure is not None:
        result['errorType']=type(failure).__name__
        result['error']=str(failure)
    return result


class CaptureFailure(OSError):
    def __init__(self,api,result,error):
        super().__init__(error,'%s returned %s (Win32 error %s)'%(api,result,error))
        self.api,self.result,self.win32Error=api,result,error


class BitmapHeader(c.Structure):
    _fields_=[('size',w.DWORD),('width',w.LONG),('height',w.LONG),('planes',w.WORD),
              ('bitCount',w.WORD),('compression',w.DWORD),('sizeImage',w.DWORD),
              ('xPixels',w.LONG),('yPixels',w.LONG),('colorsUsed',w.DWORD),('colorsImportant',w.DWORD)]


class BitmapInfo(c.Structure):
    _fields_=[('header',BitmapHeader),('colors',w.DWORD*3)]


class NativeScreen:
    def __init__(self):
        self.calls=[]
        self.user=c.WinDLL('user32',use_last_error=True)
        self.gdi=c.WinDLL('gdi32',use_last_error=True)
        signatures=[
            (self.user.SetThreadDpiAwarenessContext,[c.c_void_p],c.c_void_p),
            (self.user.GetSystemMetrics,[c.c_int],c.c_int),
            (self.user.GetDC,[w.HWND],w.HDC),
            (self.user.ReleaseDC,[w.HWND,w.HDC],c.c_int),
            (self.gdi.CreateCompatibleDC,[w.HDC],w.HDC),
            (self.gdi.CreateCompatibleBitmap,[w.HDC,c.c_int,c.c_int],w.HBITMAP),
            (self.gdi.SelectObject,[w.HDC,w.HANDLE],w.HANDLE),
            (self.gdi.BitBlt,[w.HDC,c.c_int,c.c_int,c.c_int,c.c_int,w.HDC,c.c_int,c.c_int,w.DWORD],w.BOOL),
            (self.gdi.GetDIBits,[w.HDC,w.HBITMAP,w.UINT,w.UINT,c.c_void_p,c.POINTER(BitmapInfo),w.UINT],c.c_int),
            (self.gdi.DeleteObject,[w.HANDLE],w.BOOL),
            (self.gdi.DeleteDC,[w.HDC],w.BOOL),
        ]
        for function,args,result in signatures:function.argtypes=args;function.restype=result

    def call(self,name,function,*args):
        c.set_last_error(0);result=function(*args)
        ok=bool(result) and not (name.startswith('SelectObject') and result==c.c_void_p(-1).value)
        error=c.get_last_error() if not ok else 0
        self.calls.append(dict(api=name,result=int(result or 0),error=error))
        if not ok:raise CaptureFailure(name,result,error)
        return result

    def read(self):
        previous_dpi=screen=dc=bitmap=previous=None
        failure=None;cleanup=[];frame=None
        try:
            previous_dpi=self.call('SetThreadDpiAwarenessContext',self.user.SetThreadDpiAwarenessContext,c.c_void_p(-4))
            width=self.call('GetSystemMetrics(SM_CXSCREEN)',self.user.GetSystemMetrics,0)
            height=self.call('GetSystemMetrics(SM_CYSCREEN)',self.user.GetSystemMetrics,1)
            dimensions(width,height)
            screen=self.call('GetDC(NULL)',self.user.GetDC,None)
            dc=self.call('CreateCompatibleDC',self.gdi.CreateCompatibleDC,screen)
            bitmap=self.call('CreateCompatibleBitmap',self.gdi.CreateCompatibleBitmap,screen,width,height)
            previous=self.call('SelectObject(bitmap)',self.gdi.SelectObject,dc,bitmap)
            self.call('BitBlt(primary-screen)',self.gdi.BitBlt,dc,0,0,width,height,screen,0,0,0x40CC0020)
            # GetDIBits requires the bitmap to be deselected from a device context.
            self.call('SelectObject(restore)',self.gdi.SelectObject,dc,previous);previous=None
            info=BitmapInfo();info.header.size=c.sizeof(BitmapHeader)
            info.header.width=width;info.header.height=-height
            info.header.planes=1;info.header.bitCount=32;info.header.compression=0
            buffer=(c.c_ubyte*(width*height*4))()
            rows=self.call('GetDIBits',self.gdi.GetDIBits,dc,bitmap,0,height,buffer,c.byref(info),0)
            if rows!=height:raise CaptureFailure('GetDIBits(incomplete rows)',rows,0)
            bgra=bytes(buffer);rgb=bytearray(width*height*3)
            rgb[0::3]=bgra[2::4];rgb[1::3]=bgra[1::4];rgb[2::3]=bgra[0::4]
            frame=dict(width=width,height=height,rgb=bytes(rgb))
        except BaseException as error:failure=error
        finally:
            actions=[]
            if previous:actions.append(('SelectObject(cleanup)',self.gdi.SelectObject,(dc,previous)))
            if bitmap:actions.append(('DeleteObject(bitmap)',self.gdi.DeleteObject,(bitmap,)))
            if dc:actions.append(('DeleteDC',self.gdi.DeleteDC,(dc,)))
            if screen:actions.append(('ReleaseDC',self.user.ReleaseDC,(None,screen)))
            if previous_dpi:actions.append(('SetThreadDpiAwarenessContext(restore)',self.user.SetThreadDpiAwarenessContext,(previous_dpi,)))
            for name,function,args in actions:
                try:self.call(name,function,*args)
                except Exception as error:cleanup.append(str(error))
        if failure:raise failure
        if cleanup:raise RuntimeError('Native cleanup failed: '+'; '.join(cleanup))
        frame['nativeCalls']=list(self.calls)
        return frame


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('.arena-device-local/screen-desktop-fixture.json'))
    args=parser.parse_args()
    if os.name!='nt':raise SystemExit('Windows is required')
    api=None
    try:
        config_path=args.config.resolve()
        if config_path.parent.name!='.arena-device-local':raise ValueError('Prepared fixture must be inside .arena-device-local')
        config=json.loads(config_path.read_text('utf-8-sig'))
        if config.get('controlledSourcesConfirmed') is not True or config.get('captureScope')!='primary-screen':
            raise ValueError('Explicit primary-screen capture preparation is required')
        api=NativeScreen()
        result=run(api,Path('screen-captures'),monotonic=time.monotonic,sleep=time.sleep)
        result['pid']=os.getpid()
        Path('screen-result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
        print(json.dumps(result),flush=True);return 0 if result.get('complete') else 1
    except Exception as error:
        print(json.dumps(dict(event='failure',savedImages=0,mediaSaved=False,
              errorType=type(error).__name__,error=str(error),nativeCalls=api.calls if api else [])),flush=True)
        return 1


if __name__=='__main__':raise SystemExit(main())
