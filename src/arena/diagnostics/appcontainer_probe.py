"""A temporary capability-free AppContainer, separate from FinShield policy."""
import ctypes as c
from ctypes import wintypes as w
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import uuid


class SecurityCapabilities(c.Structure):
    _fields_=[('sid',c.c_void_p),('capabilities',c.c_void_p),('count',w.DWORD),('reserved',w.DWORD)]


class StartupInfo(c.Structure):
    _fields_=[('cb',w.DWORD),('reserved',w.LPWSTR),('desktop',w.LPWSTR),('title',w.LPWSTR),
        ('x',w.DWORD),('y',w.DWORD),('xsize',w.DWORD),('ysize',w.DWORD),
        ('xchars',w.DWORD),('ychars',w.DWORD),('fill',w.DWORD),('flags',w.DWORD),
        ('show',w.WORD),('reservedsize',w.WORD),('reservedptr',c.c_void_p),
        ('stdin',w.HANDLE),('stdout',w.HANDLE),('stderr',w.HANDLE)]


class StartupInfoEx(c.Structure):
    _fields_=[('startup',StartupInfo),('attributes',c.c_void_p)]


class ProcessInfo(c.Structure):
    _fields_=[('process',w.HANDLE),('thread',w.HANDLE),('pid',w.DWORD),('tid',w.DWORD)]


class BareAppContainer:
    def __init__(self, directory):
        self.directory=Path(directory).resolve()
        self.name='arena.probe.'+uuid.uuid4().hex
        self.sid=c.c_void_p();self.sid_text=None
        self.userenv=c.WinDLL('userenv',use_last_error=True)
        self.advapi=c.WinDLL('advapi32',use_last_error=True)
        self.kernel=c.WinDLL('kernel32',use_last_error=True)
        self.userenv.CreateAppContainerProfile.argtypes=[w.LPCWSTR,w.LPCWSTR,w.LPCWSTR,c.c_void_p,w.DWORD,c.POINTER(c.c_void_p)]
        self.userenv.CreateAppContainerProfile.restype=w.LONG
        self.userenv.DeleteAppContainerProfile.argtypes=[w.LPCWSTR]
        self.userenv.DeleteAppContainerProfile.restype=w.LONG
        self.advapi.ConvertSidToStringSidW.argtypes=[c.c_void_p,c.POINTER(w.LPWSTR)]
        self.advapi.FreeSid.argtypes=[c.c_void_p]
        self.kernel.LocalFree.argtypes=[c.c_void_p]
        self.kernel.InitializeProcThreadAttributeList.argtypes=[c.c_void_p,w.DWORD,w.DWORD,c.POINTER(c.c_size_t)]
        self.kernel.UpdateProcThreadAttribute.argtypes=[c.c_void_p,w.DWORD,c.c_size_t,c.c_void_p,c.c_size_t,c.c_void_p,c.c_void_p]
        self.kernel.DeleteProcThreadAttributeList.argtypes=[c.c_void_p]
        self.kernel.CreateProcessW.argtypes=[w.LPCWSTR,w.LPWSTR,c.c_void_p,c.c_void_p,w.BOOL,w.DWORD,c.c_void_p,w.LPCWSTR,c.POINTER(StartupInfoEx),c.POINTER(ProcessInfo)]
        self.kernel.ResumeThread.argtypes=[w.HANDLE]
        self.kernel.ResumeThread.restype=w.DWORD
        self.kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]
        self.kernel.GetExitCodeProcess.argtypes=[w.HANDLE,c.POINTER(w.DWORD)]
        self.kernel.TerminateProcess.argtypes=[w.HANDLE,w.UINT]
        self.kernel.CloseHandle.argtypes=[w.HANDLE]
        hr=self.userenv.CreateAppContainerProfile(self.name,self.name,'Arena controlled local probe',None,0,c.byref(self.sid))
        if hr<0:raise OSError(hr,'CreateAppContainerProfile failed')
        value=w.LPWSTR()
        if not self.advapi.ConvertSidToStringSidW(self.sid,c.byref(value)):
            self.close();raise c.WinError(c.get_last_error())
        self.sid_text=value.value;self.kernel.LocalFree(value)
        grant=subprocess.run(['icacls.exe',str(self.directory),'/grant','*'+self.sid_text+':(OI)(CI)(RX)','/T','/Q'],
                             capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        if grant.returncode:
            self.close();raise OSError('Probe workspace grant failed')

    def run(self, command, output):
        from arena.adapters.environments.windows_job import WindowsJob
        from arena.diagnostics.ui_probe import payload,save
        output=Path(output);out=output.with_suffix('.stdout.txt')
        job=WindowsJob();info=ProcessInfo();buffer=None;initialized=False;assigned=False
        try:
            needed=c.c_size_t()
            self.kernel.InitializeProcThreadAttributeList(None,2,0,c.byref(needed))
            buffer=c.create_string_buffer(needed.value)
            if not self.kernel.InitializeProcThreadAttributeList(buffer,2,0,c.byref(needed)):raise c.WinError(c.get_last_error())
            initialized=True
            security=SecurityCapabilities(self.sid,None,0,0)
            if not self.kernel.UpdateProcThreadAttribute(buffer,0,0x20009,c.byref(security),c.sizeof(security),None,None):raise c.WinError(c.get_last_error())
            with out.open('wb') as stream, open(os.devnull,'rb') as empty:
                handles=(w.HANDLE*2)(msvcrt.get_osfhandle(stream.fileno()),msvcrt.get_osfhandle(empty.fileno()))
                for handle in handles:os.set_handle_inheritable(handle,True)
                try:
                    if not self.kernel.UpdateProcThreadAttribute(buffer,0,0x20002,handles,c.sizeof(handles),None,None):raise c.WinError(c.get_last_error())
                    startup=StartupInfoEx();startup.startup.cb=c.sizeof(startup)
                    startup.startup.desktop='WinSta0\\Default';startup.startup.flags=0x100
                    startup.startup.stdin=handles[1];startup.startup.stdout=startup.startup.stderr=handles[0]
                    startup.attributes=c.cast(buffer,c.c_void_p)
                    text=c.create_unicode_buffer(subprocess.list2cmdline(command))
                    if not self.kernel.CreateProcessW(command[0],text,None,None,True,0x08080004,None,str(self.directory),c.byref(startup),c.byref(info)):raise c.WinError(c.get_last_error())
                finally:
                    for handle in handles:os.set_handle_inheritable(handle,False)
                if not job.kernel.AssignProcessToJobObject(job.handle,info.process):raise c.WinError(c.get_last_error())
                assigned=True
                if self.kernel.ResumeThread(info.thread)==0xFFFFFFFF:raise c.WinError(c.get_last_error())
                waited=self.kernel.WaitForSingleObject(info.process,25000)
                if waited==258:raise TimeoutError('Bare AppContainer probe timeout')
                if waited!=0:raise c.WinError(c.get_last_error())
                exit_code=w.DWORD();self.kernel.GetExitCodeProcess(info.process,c.byref(exit_code))
            result=payload(out.read_text('utf8',errors='replace'))
            save(output,dict(exitCode=exit_code.value,worker=result,capabilities=0,uiRestrictions=0,desktop='inherited'))
            if result and (result.get('appContainer') is not True or result.get('jobUiMask')!=0):
                return None
            return result
        except (OSError,TimeoutError) as error:
            save(output,dict(launchError=type(error).__name__,message=str(error)))
            return None
        finally:
            if info.process and not assigned:self.kernel.TerminateProcess(info.process,1)
            job.close()
            if info.thread:self.kernel.CloseHandle(info.thread)
            if info.process:self.kernel.CloseHandle(info.process)
            if initialized:self.kernel.DeleteProcThreadAttributeList(buffer)

    def close(self):
        removed=None
        if self.sid_text:
            result=subprocess.run(['icacls.exe',str(self.directory),'/remove:g','*'+self.sid_text,'/T','/Q'],
                                  capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
            removed=result.returncode==0;self.sid_text=None
        hr=self.userenv.DeleteAppContainerProfile(self.name)
        if self.sid:self.advapi.FreeSid(self.sid);self.sid=None
        return dict(workspaceGrantRemoved=removed,temporaryProfileRemoved=hr>=0,deleteResult=hr)
