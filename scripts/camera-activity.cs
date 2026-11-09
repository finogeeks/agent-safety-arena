// Read-only camera activity observer. No device initialization or sample access.
// Interface declarations follow Microsoft win32metadata mfidl.h.
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
using System.Web.Script.Serialization;

[ComImport,Guid("39DC7F4A-B141-4719-813C-A7F46162A2B8"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface SensorProcess {
    [PreserveSig]int GetProcessId(out uint pid);
    [PreserveSig]int GetStreamingState([MarshalAs(UnmanagedType.Bool)]out bool streaming);
    [PreserveSig]int GetStreamingMode(out int mode);
    [PreserveSig]int GetReportTime(out long time);
}
[ComImport,Guid("3E8C4BE1-A8C2-4528-90DE-2851BDE5FEAD"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface SensorReport {
    [PreserveSig]int GetFriendlyName([Out,MarshalAs(UnmanagedType.LPWStr)]StringBuilder name,uint size,out uint written);
    [PreserveSig]int GetSymbolicLink([Out,MarshalAs(UnmanagedType.LPWStr)]StringBuilder name,uint size,out uint written);
    [PreserveSig]int GetProcessCount(out uint count);
    [PreserveSig]int GetProcessActivity(uint index,out SensorProcess activity);
}
[ComImport,Guid("683F7A5E-4A19-43CD-B1A9-DBF4AB3F7777"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface SensorReports {
    [PreserveSig]int GetCount(out uint count);
    [PreserveSig]int GetActivityReport(uint index,out SensorReport report);
    [PreserveSig]int GetActivityReportByDeviceName([MarshalAs(UnmanagedType.LPWStr)]string name,out SensorReport report);
}
[Guid("DE5072EE-DBE3-46DC-8A87-B6F631194751"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
[ComVisible(true)]public interface SensorCallback {
    [PreserveSig]int OnActivitiesReport([MarshalAs(UnmanagedType.Interface)]SensorReports reports);
}
[ComImport,Guid("D0CEF145-B3F4-4340-A2E5-7A5080CA05CB"),InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface SensorMonitor {
    [PreserveSig]int Start();
    [PreserveSig]int Stop();
}
[ComVisible(true),ClassInterface(ClassInterfaceType.None)]
public class CameraCallback : SensorCallback {
    readonly string target;
    public CameraCallback(string targetName) {target=targetName;}
    public int OnActivitiesReport(SensorReports reports) {
        SensorReport report=null;
        try {
            int hr=reports.GetActivityReportByDeviceName(target,out report);
            if(hr<0) {
                if(hr==unchecked((int)0xC00D36D5)) CameraActivity.Emit(new {kind="camera-activity",processes=new object[0]});
                else CameraActivity.Emit(new {kind="unavailable",error=hr});
                return 0;
            }
            uint count;Marshal.ThrowExceptionForHR(report.GetProcessCount(out count));
            var processes=new List<object>();
            for(uint i=0;i<count;i++) {
                SensorProcess process=null;
                try {
                    Marshal.ThrowExceptionForHR(report.GetProcessActivity(i,out process));
                    uint pid;bool streaming;long reportTime;
                    Marshal.ThrowExceptionForHR(process.GetProcessId(out pid));
                    Marshal.ThrowExceptionForHR(process.GetStreamingState(out streaming));
                    Marshal.ThrowExceptionForHR(process.GetReportTime(out reportTime));
                    processes.Add(new {pid=pid,streaming=streaming,reportFileTime=reportTime});
                } finally {if(process!=null)Marshal.ReleaseComObject(process);}
            }
            CameraActivity.Emit(new {kind="camera-activity",processes=processes});
        } catch(Exception error) {CameraActivity.Emit(new {kind="unavailable",error=error.HResult});}
        finally {if(report!=null)Marshal.ReleaseComObject(report);}
        return 0;
    }
}
public class CameraActivity {
    static readonly object Sync=new object();
    [DllImport("mfplat.dll")]static extern int MFStartup(int version,int flags);
    [DllImport("mfplat.dll")]static extern int MFShutdown();
    [DllImport("mfsensorgroup.dll")]static extern int MFCreateSensorActivityMonitor(SensorCallback callback,out SensorMonitor monitor);
    public static void Emit(object value) {
        lock(Sync) {Console.WriteLine(new JavaScriptSerializer().Serialize(value));Console.Out.Flush();}
    }
    [MTAThread]public static int Main(string[] args) {
        SensorMonitor monitor=null;CameraCallback callback=null;bool started=false;
        try {
            if(args.Length!=1 || String.IsNullOrWhiteSpace(args[0]))return 2;
            Marshal.ThrowExceptionForHR(MFStartup(0x20070,0));started=true;
            callback=new CameraCallback(args[0]);
            Marshal.ThrowExceptionForHR(MFCreateSensorActivityMonitor(callback,out monitor));
            Marshal.ThrowExceptionForHR(monitor.Start());
            string command;
            while((command=Console.ReadLine())!=null && command!="stop") {
                if(command=="poll") continue;
            }
            return 0;
        } catch(Exception error) {Emit(new {kind="unavailable",error=error.HResult});return 1;}
        finally {
            if(monitor!=null) {monitor.Stop();Marshal.ReleaseComObject(monitor);}
            if(started)MFShutdown();GC.KeepAlive(callback);
        }
    }
}
