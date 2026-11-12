"""Read and write only a declared native CLI console, in a short-lived process."""
import ctypes as c
from ctypes import wintypes as w
import json
import sys

def pack_coord(x,y):
    return (int(y)<<16)|(int(x)&0xFFFF)

class Coord(c.Structure):
    _fields_=[('x',c.c_short),('y',c.c_short)]
class Rect(c.Structure):
    _fields_=[('left',c.c_short),('top',c.c_short),('right',c.c_short),('bottom',c.c_short)]
class Info(c.Structure):
    _fields_=[('size',Coord),('cursor',Coord),('attributes',w.WORD),('window',Rect),('maximum',Coord)]
class Character(c.Union):
    _fields_=[('unicode',w.WCHAR),('ascii',c.c_char)]
class Cell(c.Structure):
    _fields_=[('char',Character),('attributes',w.WORD)]
class Key(c.Structure):
    _fields_=[('down',w.BOOL),('repeat',w.WORD),('virtual',w.WORD),('scan',w.WORD),('char',w.WCHAR),('control',w.DWORD)]
class Event(c.Union):
    _fields_=[('key',Key),('padding',c.c_byte*16)]
class Input(c.Structure):
    _fields_=[('type',w.WORD),('event',Event)]

def main(request):
    kernel=c.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,c.c_void_p,w.DWORD,w.DWORD,w.HANDLE]
    kernel.CreateFileW.restype=w.HANDLE
    kernel.AttachConsole.argtypes=[w.DWORD]
    kernel.GetConsoleScreenBufferInfo.argtypes=[w.HANDLE,c.POINTER(Info)]
    kernel.ReadConsoleOutputW.argtypes=[w.HANDLE,c.POINTER(Cell),w.DWORD,w.DWORD,c.POINTER(Rect)]
    kernel.WriteConsoleInputW.argtypes=[w.HANDLE,c.POINTER(Input),w.DWORD,c.POINTER(w.DWORD)]
    kernel.CloseHandle.argtypes=[w.HANDLE]
    kernel.FreeConsole()
    if not kernel.AttachConsole(int(request['pid'])):raise c.WinError(c.get_last_error())
    output=None;input_handle=None
    try:
        if request['action']=='read':
            output=kernel.CreateFileW('CONOUT$',0x80000000,3,None,3,0,None)
            info=Info()
            if not kernel.GetConsoleScreenBufferInfo(output,c.byref(info)):raise c.WinError(c.get_last_error())
            width=info.size.x;height=info.window.bottom-info.window.top+1
            remaining=info.size.y-info.window.top
            if remaining>0:height=min(height,remaining)
            if not 1<=width*height<=250000:raise RuntimeError('Native console dimensions are invalid')
            buffer=(Cell*(width*height))()
            region=Rect(0,info.window.top,width-1,info.window.top+height-1)
            if not kernel.ReadConsoleOutputW(output,buffer,pack_coord(width,height),pack_coord(0,0),c.byref(region)):raise c.WinError(c.get_last_error())
            rows=[]
            for row in range(height):
                cells=buffer[row*width:(row+1)*width]
                rows.append(''.join(cell.char.unicode or ' ' for cell in cells
                                    if not cell.attributes&0x200).rstrip())
            return {'text':'\n'.join(rows), 'columns':width,'rows':height}
        input_handle=kernel.CreateFileW('CONIN$',0xC0000000,3,None,3,0,None)
        events=[]
        def add(char,virtual=0,control=0):
            for down in [True,False]:events.append(Input(1,Event(key=Key(down,1,virtual,0,char,control))))
        if request['action']=='paste':
            raw=request['text'].encode('utf-16-le')
            for i in range(0,len(raw),2):
                char=chr(int.from_bytes(raw[i:i+2],'little'))
                if char=='\n':add('\r',13,0x10)
                elif char!='\r':add(char)
        elif request['action']=='key':
            name=request['key'];keys={'enter':('\r',13,0),'ctrl-enter':('\r',13,8),'ctrl-c':('\x03',67,8),'ctrl-d':('\x04',68,8),'escape':('\x1b',27,0),'down':('\0',40,0),'up':('\0',38,0),'y':('y',89,0),'1':('1',49,0)}
            add(*keys[name])
        else:raise ValueError('Unknown console action')
        array=(Input*len(events))(*events);written=w.DWORD()
        if not kernel.WriteConsoleInputW(input_handle,array,len(events),c.byref(written)) or written.value!=len(events):raise c.WinError(c.get_last_error())
        return {'written':written.value}
    finally:
        if output:kernel.CloseHandle(output)
        if input_handle:kernel.CloseHandle(input_handle)
        kernel.FreeConsole()

if __name__=='__main__':
    try:print(json.dumps({'ok':True,'value':main(json.load(sys.stdin))},ensure_ascii=True))
    except Exception as error:print(json.dumps({'ok':False,'error':str(error)},ensure_ascii=True))
