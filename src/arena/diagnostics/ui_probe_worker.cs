// Fixed, bounded API probes. Never capture personal desktop, audio, or video.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Text;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using System.Windows.Forms;

class ArenaUiProbe {
    static JavaScriptSerializer Json = new JavaScriptSerializer();
    static void Emit(object value) { Console.WriteLine(Json.Serialize(value)); Console.Out.Flush(); }
    delegate IntPtr Hook(int code, IntPtr w, IntPtr l);
    [DllImport("user32.dll", SetLastError=true)] static extern IntPtr SetWindowsHookExW(int id, Hook callback, IntPtr module, uint thread);
    [DllImport("user32.dll")] static extern IntPtr CallNextHookEx(IntPtr hook, int code, IntPtr w, IntPtr l);
    [DllImport("user32.dll", SetLastError=true)] static extern bool UnhookWindowsHookEx(IntPtr hook);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern IntPtr GetModuleHandleW(string name);
    [DllImport("user32.dll", SetLastError=true)] static extern bool BlockInput(bool block);
    [DllImport("user32.dll", SetLastError=true)] static extern bool RegisterHotKey(IntPtr hwnd, int id, uint modifiers, uint key);
    [DllImport("user32.dll", SetLastError=true)] static extern bool UnregisterHotKey(IntPtr hwnd, int id);
    [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CreateDesktopW(string name, IntPtr device, IntPtr mode, uint flags, uint access, IntPtr security);
    [DllImport("user32.dll")] static extern bool CloseDesktop(IntPtr desktop);
    [DllImport("user32.dll", SetLastError=true)] static extern bool OpenClipboard(IntPtr hwnd);
    [DllImport("user32.dll")] static extern bool CloseClipboard();
    [DllImport("user32.dll", SetLastError=true)] static extern IntPtr GetClipboardData(uint format);
    [DllImport("kernel32.dll", SetLastError=true)] static extern IntPtr GlobalLock(IntPtr handle);
    [DllImport("kernel32.dll")] static extern bool GlobalUnlock(IntPtr handle);
    [DllImport("user32.dll", SetLastError=true)] static extern bool SystemParametersInfoW(uint action, uint param, IntPtr value, uint flags);
    [DllImport("user32.dll", SetLastError=true)] static extern bool PrintWindow(IntPtr hwnd, IntPtr dc, uint flags);
    [DllImport("user32.dll", SetLastError=true)] static extern IntPtr GetDC(IntPtr hwnd);
    [DllImport("user32.dll")] static extern int ReleaseDC(IntPtr hwnd, IntPtr dc);
    [DllImport("gdi32.dll", SetLastError=true)] static extern bool BitBlt(IntPtr destination,int x,int y,int width,int height,IntPtr source,int sx,int sy,uint operation);
    [DllImport("user32.dll")] static extern IntPtr WindowFromPoint(Point point);
    [DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
    [DllImport("advapi32.dll", SetLastError=true)] static extern bool OpenProcessToken(IntPtr process, uint access, out IntPtr token);
    [DllImport("advapi32.dll", SetLastError=true)] static extern bool GetTokenInformation(IntPtr token, int info, out int value, int length, out int returned);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job, int kind, out uint flags, uint length, IntPtr returned);

    [ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface DeviceEnumerator {
        [PreserveSig] int EnumAudioEndpoints(int flow, uint mask, out IntPtr collection);
        [PreserveSig] int GetDefaultAudioEndpoint(int flow, int role, out Device device);
    }
    [ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface Device {
        [PreserveSig] int Activate(ref Guid iid, uint context, IntPtr parameters, [MarshalAs(UnmanagedType.IUnknown)] out object endpoint);
    }
    [ComImport, Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface EndpointVolume {
        [PreserveSig] int RegisterControlChangeNotify(IntPtr callback);
        [PreserveSig] int UnregisterControlChangeNotify(IntPtr callback);
        [PreserveSig] int GetChannelCount(out uint count);
        [PreserveSig] int SetMasterVolumeLevel(float value, ref Guid context);
        [PreserveSig] int SetMasterVolumeLevelScalar(float value, ref Guid context);
        [PreserveSig] int GetMasterVolumeLevel(out float value);
        [PreserveSig] int GetMasterVolumeLevelScalar(out float value);
        [PreserveSig] int SetChannelVolumeLevel(uint channel, float value, ref Guid context);
        [PreserveSig] int SetChannelVolumeLevelScalar(uint channel, float value, ref Guid context);
        [PreserveSig] int GetChannelVolumeLevel(uint channel, out float value);
        [PreserveSig] int GetChannelVolumeLevelScalar(uint channel, out float value);
        [PreserveSig] int SetMute([MarshalAs(UnmanagedType.Bool)] bool value, ref Guid context);
        [PreserveSig] int GetMute([MarshalAs(UnmanagedType.Bool)] out bool value);
    }

    static string Quote(string value) {
        var output=new StringBuilder("\"");int slashes=0;
        foreach(char c in value) {
            if(c=='\\') {slashes++;continue;}
            if(c=='\"') {output.Append('\\',slashes*2+1);output.Append(c);slashes=0;continue;}
            output.Append('\\',slashes);slashes=0;output.Append(c);
        }
        output.Append('\\',slashes*2);output.Append('"');return output.ToString();
    }
    static Dictionary<string,object> MediaCommand(string executable, string[] arguments) {
        var output=new StringBuilder();var errors=new StringBuilder();
        var quoted=new List<string>();foreach(string arg in arguments)quoted.Add(Quote(arg));
        var info=new ProcessStartInfo(executable,String.Join(" ",quoted.ToArray()));
        info.UseShellExecute=false;info.CreateNoWindow=true;info.RedirectStandardOutput=true;info.RedirectStandardError=true;
        using(var process=new Process()) {
            process.StartInfo=info;
            process.OutputDataReceived+=delegate(object sender,DataReceivedEventArgs e) {if(e.Data!=null)lock(output)output.AppendLine(e.Data);};
            process.ErrorDataReceived+=delegate(object sender,DataReceivedEventArgs e) {if(e.Data!=null)lock(errors)errors.AppendLine(e.Data);};
            process.Start();process.BeginOutputReadLine();process.BeginErrorReadLine();
            bool completed=process.WaitForExit(10000);
            if(!completed)process.Kill();process.WaitForExit();
            return new Dictionary<string,object>{{"exitCode",process.ExitCode},{"timedOut",!completed},{"progress",output.ToString()},{"diagnostics",errors.ToString()}};
        }
    }
    static void MediaProbe(string name,string configPath,Dictionary<string,object> result) {
        var config=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(configPath));
        string executable=(string)config["ffmpeg"];
        var startup=MediaCommand(executable,new string[]{"-version"});
        bool ready=(int)startup["exitCode"]==0 && !(bool)startup["timedOut"];
        result["backendProgramReady"]=ready;result["stage"]="media-program-start";
        if(!ready) {result["startup"]=startup;return;}
        bool camera=name.StartsWith("camera-");bool generated=name.EndsWith("pipeline");
        var args=new List<string>{"-hide_banner","-nostdin","-nostats","-progress","pipe:1"};
        if(generated)args.AddRange(new string[]{"-f","lavfi","-i",camera ? "color=c=blue:s=64x64:r=1" : "sine=frequency=1000:sample_rate=16000"});
        else {
            if(!config.ContainsKey("controlledSourcesConfirmed") || !Object.Equals(config["controlledSourcesConfirmed"],true))throw new InvalidOperationException("Controlled sources required");
            string device=(string)config[camera ? "cameraDevice" : "microphoneDevice"];
            if(String.IsNullOrWhiteSpace(device)) {result["stage"]="missing-controlled-source";return;}
            args.AddRange(new string[]{"-f","dshow","-i",(camera ? "video=" : "audio=")+device});
        }
        args.AddRange(camera ? new string[]{"-frames:v","1","-an","-f","null","-"} : new string[]{"-t","0.15","-vn","-ac","1","-ar","16000","-f","null","-"});
        var capture=MediaCommand(executable,args.ToArray());
        string progress=(string)capture["progress"],diagnostics=(string)capture["diagnostics"];
        long frames=0,duration=0;
        foreach(Match match in Regex.Matches(progress,@"(?m)^frame=(\d+)"))frames=Math.Max(frames,long.Parse(match.Groups[1].Value));
        foreach(Match match in Regex.Matches(progress,@"(?m)^out_time_us=(\d+)"))duration=Math.Max(duration,long.Parse(match.Groups[1].Value));
        bool ok=(int)capture["exitCode"]==0 && !(bool)capture["timedOut"] && (camera ? frames>=1 : duration>0);
        result["ok"]=ok;result["stage"]=generated ? "synthetic-pipeline" : "device-capture";
        result["framesDecoded"]=frames;result["outputDurationMicroseconds"]=duration;
        result["syntheticPipeline"]=generated;result["mediaSaved"]=false;result["capture"]=capture;
        if(!ok && (diagnostics.IndexOf("0x80070005",StringComparison.OrdinalIgnoreCase)>=0 || diagnostics.IndexOf("Access is denied",StringComparison.OrdinalIgnoreCase)>=0))result["error"]=5;
    }
    static Dictionary<string,object> Probe(string name, string nonce, IntPtr hwnd, string mediaConfig) {
        var result = new Dictionary<string,object>();
        result["kind"]="arena-ui-probe"; result["case"]=name; result["ok"]=false;
        uint mask; bool queried=QueryInformationJobObject(IntPtr.Zero,4,out mask,4,IntPtr.Zero);
        result["jobUiMask"]=queried ? (object)mask : null;
        IntPtr token; int ac=0, returned;
        if (OpenProcessToken(GetCurrentProcess(),8,out token)) {
            try { GetTokenInformation(token,29,out ac,4,out returned); } finally { CloseHandle(token); }
        }
        result["appContainer"]=ac!=0;
        try {
            if(name=="camera-capture" || name=="microphone-capture" || name=="camera-pipeline" || name=="microphone-pipeline") {
                MediaProbe(name,mediaConfig,result);
            } else if(name=="keyboard-hook" || name=="mouse-hook") {
                Hook callback = delegate(int code, IntPtr w, IntPtr l) { return CallNextHookEx(IntPtr.Zero,code,w,l); };
                IntPtr hook=SetWindowsHookExW(name=="keyboard-hook" ? 13 : 14,callback,GetModuleHandleW(null),0);
                int error=Marshal.GetLastWin32Error();result["ok"]=hook!=IntPtr.Zero; result["error"]=hook==IntPtr.Zero ? error : 0;
                if(hook!=IntPtr.Zero) result["recovered"]=UnhookWindowsHookEx(hook);
                GC.KeepAlive(callback);result["scope"]="pass-through hook installation only";
            } else if(name=="shortcut-register") {
                bool ok=RegisterHotKey(IntPtr.Zero,0x7341,0x4000,0x87);int error=Marshal.GetLastWin32Error();
                result["ok"]=ok;result["error"]=ok ? 0 : error;
                if(ok) result["recovered"]=UnregisterHotKey(IntPtr.Zero,0x7341);
            } else if(name=="input-block") {
                bool ok=false;
                try { ok=BlockInput(true);int error=Marshal.GetLastWin32Error();result["ok"]=ok;result["error"]=ok ? 0 : error; }
                finally { if(ok) result["recovered"]=BlockInput(false); }
                result["scope"]="immediate same-thread recovery, no held input disruption";
            } else if(name=="desktop-create") {
                IntPtr desktop=CreateDesktopW("ArenaProbe_"+Guid.NewGuid().ToString("N"),IntPtr.Zero,IntPtr.Zero,0,0xF01FF,IntPtr.Zero);
                int error=Marshal.GetLastWin32Error();result["ok"]=desktop!=IntPtr.Zero;result["error"]=desktop==IntPtr.Zero ? error : 0;
                if(desktop!=IntPtr.Zero) result["recovered"]=CloseDesktop(desktop);
            } else if(name=="clipboard-read") {
                if(!OpenClipboard(IntPtr.Zero)) { result["error"]=Marshal.GetLastWin32Error(); return result; }
                try {
                    IntPtr data=GetClipboardData(13);int error=Marshal.GetLastWin32Error();
                    if(data==IntPtr.Zero) { result["error"]=error;return result; }
                    IntPtr text=GlobalLock(data);
                    try { result["ok"]=text!=IntPtr.Zero && Marshal.PtrToStringUni(text)==nonce; }
                    finally { if(text!=IntPtr.Zero) GlobalUnlock(data); }
                } finally { CloseClipboard(); }
            } else if(name=="clipboard-write") {
                Clipboard.SetText(nonce+"_REPLACED");result["ok"]=true;
            } else if(name=="system-parameter") {
                IntPtr value=Marshal.AllocHGlobal(4);
                try {
                    if(!SystemParametersInfoW(0x70,0,value,0)) { result["error"]=Marshal.GetLastWin32Error();return result; }
                    int original=Marshal.ReadInt32(value);
                    bool ok=SystemParametersInfoW(0x71,0,new IntPtr(original),0);int error=Marshal.GetLastWin32Error();
                    result["ok"]=ok;result["error"]=ok ? 0 : error;result["sameValueWrite"]=true;
                } finally { Marshal.FreeHGlobal(value); }
            } else if(name=="speaker-mute") {
                object enumerator=Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")));
                Device device=null;object raw=null;
                try {
                    Marshal.ThrowExceptionForHR(((DeviceEnumerator)enumerator).GetDefaultAudioEndpoint(0,0,out device));
                    Guid iid=new Guid("5CDF2C82-841E-4546-9722-0CF74078229A");
                    Marshal.ThrowExceptionForHR(device.Activate(ref iid,23,IntPtr.Zero,out raw));
                    EndpointVolume volume=(EndpointVolume)raw;bool original;
                    Marshal.ThrowExceptionForHR(volume.GetMute(out original));Guid context=Guid.Empty;
                    int hr=volume.SetMute(original,ref context);result["ok"]=hr>=0;result["error"]=hr<0 ? hr : 0;
                    result["sameValueWrite"]=true;
                } finally {
                    if(raw!=null)Marshal.ReleaseComObject(raw);if(device!=null)Marshal.ReleaseComObject(device);Marshal.ReleaseComObject(enumerator);
                }
            } else if(name=="screen-capture") {
                var config=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(mediaConfig));
                int x=Convert.ToInt32(config["screenX"]),y=Convert.ToInt32(config["screenY"]);
                IntPtr screen=GetDC(IntPtr.Zero);int error=Marshal.GetLastWin32Error();
                if(screen==IntPtr.Zero) {result["error"]=error;return result;}
                try {
                    using(Bitmap bitmap=new Bitmap(160,90))using(Graphics graphics=Graphics.FromImage(bitmap)) {
                        IntPtr target=graphics.GetHdc();bool ok;
                        try {ok=BitBlt(target,0,0,160,90,screen,x,y,0x00CC0020);error=Marshal.GetLastWin32Error();}
                        finally {graphics.ReleaseHdc(target);}
                        Color pixel=bitmap.GetPixel(80,45);
                        bool matched=pixel.R==23 && pixel.G==101 && pixel.B==181;
                        result["ok"]=ok && matched;result["apiReturned"]=ok;result["patternMatched"]=matched;result["error"]=ok ? 0 : error;
                        result["scope"]="160x90 controlled test-window region only; no image saved";
                    }
                }finally {ReleaseDC(IntPtr.Zero,screen);}
            } else if(name=="window-capture") {
                using(Bitmap bitmap=new Bitmap(320,180)) using(Graphics graphics=Graphics.FromImage(bitmap)) {
                    IntPtr dc=graphics.GetHdc();bool ok;int error;
                    try { ok=PrintWindow(hwnd,dc,2);error=Marshal.GetLastWin32Error(); }
                    finally { graphics.ReleaseHdc(dc); }
                    Color pixel=bitmap.GetPixel(80,80);
                    bool pattern=pixel.R==23 && pixel.G==101 && pixel.B==181;
                    result["ok"]=ok && pattern;result["apiReturned"]=ok;result["patternMatched"]=pattern;result["error"]=ok ? 0 : error;
                }
            } else { result["error"]="unknown-case"; }
        } catch(Exception error) { result["ok"]=false;result["error"]=error.HResult;result["errorType"]=error.GetType().Name; }
        return result;
    }

    class PatternForm : Form {
        protected override bool ShowWithoutActivation { get { return true; } }
    }
    static void Fixture(string nonce,bool useClipboard) {
        IDataObject previous=useClipboard ? Clipboard.GetDataObject() : null;DataObject saved=new DataObject();
        if(previous!=null) foreach(string format in previous.GetFormats(false)) {
            object value=previous.GetData(format,false);
            if(value is MemoryStream) value=new MemoryStream(((MemoryStream)value).ToArray());
            else if(value is Bitmap) value=((Bitmap)value).Clone();
            if(value!=null)saved.SetData(format,false,value);
        }
        bool restored=false, concurrent=false;
        try {
            if(useClipboard)Clipboard.SetText(nonce);
            using(PatternForm form=new PatternForm()) {
                form.Text="Arena controlled test pattern";form.ClientSize=new Size(320,180);form.BackColor=Color.FromArgb(23,101,181);
                form.StartPosition=FormStartPosition.Manual;form.Location=new Point(30,30);form.ShowInTaskbar=false;
                form.TopMost=true;
                form.Shown+=delegate {
                    Point origin=form.PointToScreen(new Point(40,40));
                    Emit(new {stage="ready",hwnd=form.Handle.ToInt64(),clipboardSynthetic=useClipboard,screenX=origin.X,screenY=origin.Y});
                    Thread input=new Thread(delegate() {
                        string line;while((line=Console.ReadLine())!=null) {
                            string command=line;
                            if(form.IsDisposed)break;
                            form.BeginInvoke(new Action(delegate {
                                string text=useClipboard && Clipboard.ContainsText() ? Clipboard.GetText() : "";
                                bool owned=!useClipboard || text==nonce || text==nonce+"_REPLACED";
                                if(command=="stop")form.Close();
                                else if(command=="reset") {
                                    if(useClipboard && owned)Clipboard.SetText(nonce);
                                    Emit(new {stage="reset",owned=owned});
                                } else if(command=="observe") Emit(new {stage="observed",replacementObserved=text==nonce+"_REPLACED",owned=owned,patternRegionOwned=WindowFromPoint(new Point(origin.X+80,origin.Y+45))==form.Handle});
                            }));
                            if(command=="stop")break;
                        }
                    });input.IsBackground=true;input.Start();
                };
                var watchdog=new System.Windows.Forms.Timer();watchdog.Interval=180000;watchdog.Tick+=delegate {form.Close();};watchdog.Start();
                Application.Run(form);watchdog.Dispose();
            }
        } finally {
            string current=useClipboard && Clipboard.ContainsText() ? Clipboard.GetText() : "";
            if(!useClipboard)restored=true;
            else if(current==nonce || current==nonce+"_REPLACED") { Clipboard.SetDataObject(saved,true);restored=true; }
            else concurrent=true;
            Emit(new {stage="recovered",clipboardRestored=restored,preservedConcurrentChange=concurrent});
        }
    }

    [STAThread] static int Main(string[] args) {
        Console.OutputEncoding=new System.Text.UTF8Encoding(false);
        try {
            if(args.Length>=2 && args[0]=="fixture") { Fixture(args[1],args.Length<3 || args[2]!="no-clipboard");return 0; }
            if(args.Length<3)return 2;
            if(args.Length>3 && args[args.Length-1]=="gate" && Console.ReadLine()!="GO")return 3;
            Emit(Probe(args[0],args[1],new IntPtr(long.Parse(args[2])),args.Length>3 && args[3]!="gate" ? args[3] : null));return 0;
        } catch(Exception error) { Emit(new {stage="error",errorType=error.GetType().Name,error=error.HResult});return 1; }
    }
}
