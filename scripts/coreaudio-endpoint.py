"""Read-only CoreAudio endpoint adapter. Importing this file is inert."""
import ctypes as c
import uuid


class GUID(c.Structure):
    _fields_=[('data',c.c_ubyte*16)]
    @classmethod
    def of(cls,text):return cls((c.c_ubyte*16).from_buffer_copy(uuid.UUID(text).bytes_le))


def checked(hr):
    if hr < 0:raise OSError(hr,'CoreAudio HRESULT 0x%08X' % (hr & 0xffffffff))


def com_call(pointer,index,types,*args):
    table=c.cast(pointer,c.POINTER(c.POINTER(c.c_void_p))).contents
    function=c.WINFUNCTYPE(c.c_long,c.c_void_p,*types)(table[index])
    return function(pointer,*args)


class Endpoint:
    def __init__(self,identity):
        self.ole=c.WinDLL('ole32',use_last_error=True)
        self.ole.CoInitializeEx.argtypes=[c.c_void_p,c.c_ulong]
        self.ole.CoCreateInstance.argtypes=[c.POINTER(GUID),c.c_void_p,c.c_ulong,c.POINTER(GUID),c.POINTER(c.c_void_p)]
        self.ole.CoTaskMemFree.argtypes=[c.c_void_p]
        self.enumerator=c.c_void_p();self.device=c.c_void_p();self.volume=c.c_void_p()
        self.initialized=False
        try:
            checked(self.ole.CoInitializeEx(None,0));self.initialized=True
            cls=GUID.of('BCDE0395-E52F-467C-8E3D-C4579291692E')
            iid=GUID.of('A95664D2-9614-4F35-A746-DE8DB63617E6')
            checked(self.ole.CoCreateInstance(c.byref(cls),None,23,c.byref(iid),c.byref(self.enumerator)))
            if not identity:raise ValueError('An exact prepared endpointId is required')
            checked(com_call(self.enumerator,5,[c.c_wchar_p,c.POINTER(c.c_void_p)],identity,c.byref(self.device)))
            iid=GUID.of('5CDF2C82-841E-4546-9722-0CF74078229A')
            checked(com_call(self.device,3,[c.POINTER(GUID),c.c_ulong,c.c_void_p,c.POINTER(c.c_void_p)],c.byref(iid),23,None,c.byref(self.volume)))
            self.context=GUID.of(str(uuid.uuid4()))
        except BaseException:
            self.close();raise

    def state(self):
        muted=c.c_int();volume=c.c_float()
        checked(com_call(self.volume,15,[c.POINTER(c.c_int)],c.byref(muted)))
        checked(com_call(self.volume,9,[c.POINTER(c.c_float)],c.byref(volume)))
        return dict(muted=bool(muted.value),volume=float(volume.value))

    def mute(self,value):
        checked(com_call(self.volume,14,[c.c_int,c.POINTER(GUID)],bool(value),c.byref(self.context)))

    def close(self):
        for name in ('volume','device','enumerator'):
            pointer=getattr(self,name,None)
            if pointer and pointer.value:
                com_call(pointer,2,[]);setattr(self,name,c.c_void_p())
        if self.initialized:self.ole.CoUninitialize();self.initialized=False
