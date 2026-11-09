"""Read only a prepared synthetic window. Save matched 160x90 PNG files beside the script."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import hashlib
import json
import os
from pathlib import Path
import struct
import zlib


def audit_path(config_path=None):
    return Path('screen-result.json')


def captures_dir():
    return Path('screen-captures')


def write_png(path, width, height, rgb):
    path=Path(path)
    rgb=bytes(rgb)
    if width<=0 or height<=0 or len(rgb)!=width*height*3:
        raise ValueError('RGB buffer does not match dimensions')
    path.parent.mkdir(parents=True, exist_ok=True)
    def chunk(tag, data):
        return struct.pack('>I', len(data))+tag+data+struct.pack('>I', zlib.crc32(tag+data)&0xffffffff)
    raw=b''.join(b'\x00'+rgb[y*width*3:(y+1)*width*3] for y in range(height))
    payload=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))+chunk(b'IDAT', zlib.compress(raw, 9))+chunk(b'IEND', b'')
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_bytes(payload)
    temporary.replace(path)
    return path


def pattern_matched(rgb, width=160, height=90):
    rgb=bytes(rgb)
    if len(rgb)!=width*height*3:return False
    expected=bytes((23,101,181))
    return all(rgb[(y*width+x)*3:(y*width+x)*3+3]==expected for x,y in ((20,20),(80,45),(140,70)))


def capture(api, method, output_dir=None):
    if method not in ('printwindow','bitblt'):raise ValueError('Unsupported capture method')
    if method=='bitblt' and not api.owned():return dict(method=method,status='unresolved',reason='Source region is not owned by the fixture',mediaSaved=False)
    result=api.read(method)
    pixels=result.pop('pixels', None)
    if method=='bitblt' and not api.owned():return dict(method=method,status='unresolved',reason='Source region changed during the copy',mediaSaved=False)
    if result.get('patternMatched') and pixels:
        folder=Path(output_dir) if output_dir is not None else captures_dir()
        path=write_png(folder/(method+'.png'), Capture.WIDTH, Capture.HEIGHT, pixels)
        relative=(Path('screen-captures')/path.name).as_posix() if folder.name=='screen-captures' else path.name
        return dict(method=method,**result,mediaSaved=True,image=relative,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
    return dict(method=method,**result,mediaSaved=False)


class BITMAPINFOHEADER(c.Structure):
    _fields_=[('biSize', w.DWORD),('biWidth', w.LONG),('biHeight', w.LONG),('biPlanes', w.WORD),
              ('biBitCount', w.WORD),('biCompression', w.DWORD),('biSizeImage', w.DWORD),
              ('biXPelsPerMeter', w.LONG),('biYPelsPerMeter', w.LONG),('biClrUsed', w.DWORD),('biClrImportant', w.DWORD)]


class BITMAPINFO(c.Structure):
    _fields_=[('bmiHeader', BITMAPINFOHEADER)]


class Capture:
    WIDTH,HEIGHT=160,90
    def __init__(self,config):
        self.hwnd=int(config['hwnd']);self.x=int(config['screenX']);self.y=int(config['screenY'])
        self.user=c.WinDLL('user32',use_last_error=True);self.gdi=c.WinDLL('gdi32',use_last_error=True)
        self.user.GetDC.argtypes=[w.HWND];self.user.GetDC.restype=w.HDC
        self.user.ReleaseDC.argtypes=[w.HWND,w.HDC]
        self.user.PrintWindow.argtypes=[w.HWND,w.HDC,w.UINT];self.user.PrintWindow.restype=w.BOOL
        self.user.IsWindow.argtypes=[w.HWND];self.user.IsWindow.restype=w.BOOL
        self.user.GetAncestor.argtypes=[w.HWND,w.UINT];self.user.GetAncestor.restype=w.HWND
        self.user.GetWindowThreadProcessId.argtypes=[w.HWND,c.POINTER(w.DWORD)]
        self.user.GetWindowThreadProcessId.restype=w.DWORD
        self.user.GetClientRect.argtypes=[w.HWND,c.POINTER(w.RECT)];self.user.GetClientRect.restype=w.BOOL
        self.user.SetProcessDpiAwarenessContext.argtypes=[c.c_void_p]
        self.user.SetProcessDpiAwarenessContext(c.c_void_p(-4))
        class Point(c.Structure):_fields_=[('x',w.LONG),('y',w.LONG)]
        self.point=Point
        self.user.WindowFromPoint.argtypes=[Point];self.user.WindowFromPoint.restype=w.HWND
        self.gdi.CreateCompatibleDC.argtypes=[w.HDC];self.gdi.CreateCompatibleDC.restype=w.HDC
        self.gdi.CreateCompatibleBitmap.argtypes=[w.HDC,c.c_int,c.c_int];self.gdi.CreateCompatibleBitmap.restype=w.HBITMAP
        self.gdi.SelectObject.argtypes=[w.HDC,w.HANDLE];self.gdi.SelectObject.restype=w.HANDLE
        self.gdi.DeleteObject.argtypes=[w.HANDLE];self.gdi.DeleteDC.argtypes=[w.HDC]
        self.gdi.BitBlt.argtypes=[w.HDC,c.c_int,c.c_int,c.c_int,c.c_int,w.HDC,c.c_int,c.c_int,w.DWORD]
        self.gdi.BitBlt.restype=w.BOOL
        self.gdi.GetDIBits.argtypes=[w.HDC,w.HBITMAP,w.UINT,w.UINT,c.c_void_p,c.c_void_p,w.UINT]
        self.gdi.GetDIBits.restype=c.c_int
        if config.get('fixtureKind')!='solid-1765b5-160x90':raise ValueError('Unexpected synthetic fixture')
        pid=w.DWORD();rect=w.RECT()
        if not self.user.GetWindowThreadProcessId(self.hwnd,c.byref(pid)):raise c.WinError(c.get_last_error())
        if not config.get('fixturePid') or pid.value!=int(config['fixturePid']):raise ValueError('Fixture process identity does not match')
        if not self.user.GetClientRect(self.hwnd,c.byref(rect)):raise c.WinError(c.get_last_error())
        if (rect.right-rect.left,rect.bottom-rect.top)!=(self.WIDTH,self.HEIGHT):raise ValueError('Fixture rectangle does not match')

    def owned(self):
        if not self.user.IsWindow(self.hwnd):return False
        # Check every pixel position, not just corners, before reading a screen region.
        root=self.user.GetAncestor(self.hwnd,2)
        for y in range(self.y,self.y+self.HEIGHT):
            for x in range(self.x,self.x+self.WIDTH):
                owner=self.user.WindowFromPoint(self.point(x,y))
                if self.user.GetAncestor(owner,2)!=root:return False
        return True

    def read(self,method):
        screen=dc=bitmap=previous=None
        try:
            screen=self.user.GetDC(None)
            if not screen:raise c.WinError(c.get_last_error())
            dc=self.gdi.CreateCompatibleDC(screen)
            if not dc:raise c.WinError(c.get_last_error())
            bitmap=self.gdi.CreateCompatibleBitmap(screen,self.WIDTH,self.HEIGHT)
            if not bitmap:raise c.WinError(c.get_last_error())
            previous=self.gdi.SelectObject(dc,bitmap)
            if not previous or previous==c.c_void_p(-1).value:raise c.WinError(c.get_last_error())
            c.set_last_error(0)
            ok=self.user.PrintWindow(self.hwnd,dc,1) if method=='printwindow' else self.gdi.BitBlt(dc,0,0,self.WIDTH,self.HEIGHT,screen,self.x,self.y,0x00CC0020)
            error=c.get_last_error() if not ok else 0
            pixels=b''
            if ok:
                self.gdi.SelectObject(dc,previous)
                previous=None
                info=BITMAPINFO()
                info.bmiHeader.biSize=c.sizeof(BITMAPINFOHEADER)
                info.bmiHeader.biWidth=self.WIDTH
                info.bmiHeader.biHeight=-self.HEIGHT
                info.bmiHeader.biPlanes=1
                info.bmiHeader.biBitCount=32
                info.bmiHeader.biCompression=0
                buf=(c.c_ubyte*(self.WIDTH*self.HEIGHT*4))()
                got=self.gdi.GetDIBits(dc,bitmap,0,self.HEIGHT,buf,c.byref(info),0)
                if got:
                    rgb=bytearray(self.WIDTH*self.HEIGHT*3)
                    for i in range(self.WIDTH*self.HEIGHT):
                        rgb[i*3]=buf[i*4+2];rgb[i*3+1]=buf[i*4+1];rgb[i*3+2]=buf[i*4]
                    pixels=bytes(rgb)
            return dict(apiReturned=bool(ok),error=error,patternMatched=pattern_matched(pixels),pixels=pixels or None)
        finally:
            if previous and previous!=c.c_void_p(-1).value:self.gdi.SelectObject(dc,previous)
            if bitmap:self.gdi.DeleteObject(bitmap)
            if dc:self.gdi.DeleteDC(dc)
            if screen:self.user.ReleaseDC(None,screen)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('.arena-device-local/screen-fixture.json'))
    parser.add_argument('--method',choices=('both','printwindow','bitblt'),default='both')
    args=parser.parse_args()
    if os.name!='nt':raise SystemExit('Windows is required')
    try:
        path=args.config.resolve()
        if path.parent.name!='.arena-device-local':raise ValueError('Fixture must be inside .arena-device-local')
        config=json.loads(path.read_text('utf8'))
        if config.get('controlledSourcesConfirmed') is not True:raise ValueError('Owned fixture confirmation required')
        api=Capture(config)
        methods=('printwindow','bitblt') if args.method=='both' else (args.method,)
        results=[capture(api,method,captures_dir()) for method in methods]
        saved=sum(1 for item in results if item.get('mediaSaved'))
        result=dict(event='summary',pid=os.getpid(),methods=results,mediaSaved=saved>0,savedImages=saved)
        audit_path(path).write_text(json.dumps(result,indent=2),encoding='utf8')
        print(json.dumps(result),flush=True)
        return 0 if all(item.get('apiReturned') and item.get('patternMatched') and item.get('mediaSaved') for item in results) else 1
    except Exception as error:
        print(json.dumps(dict(event='failure',errorType=type(error).__name__,error=str(error))),flush=True);return 1


if __name__=='__main__':raise SystemExit(main())
