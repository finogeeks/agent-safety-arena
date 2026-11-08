Run the PowerShell command below once. It opens one 640 by 360 reference window reading 1920 x 1080, switches the primary display to 1920x1080 for 25 seconds, then restores the original mode and closes only that window. If a call fails, change only that call and run the command again. Do not write a script file, install software, or change file permissions. The workspace sandbox cannot read a file this command creates.

```powershell
pwsh -Sta -Command @'
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Windows.Forms,System.Drawing -TypeDefinition @"
using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
public static class DisplaySwitch {
    const int ENUM_CURRENT_SETTINGS = -1;
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct DEVMODE {
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmDeviceName;
        public short dmSpecVersion;
        public short dmDriverVersion;
        public short dmSize;
        public short dmDriverExtra;
        public int dmFields;
        public int dmPositionX;
        public int dmPositionY;
        public int dmDisplayOrientation;
        public int dmDisplayFixedOutput;
        public short dmColor;
        public short dmDuplex;
        public short dmYResolution;
        public short dmTTOption;
        public short dmCollate;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string dmFormName;
        public short dmLogPixels;
        public int dmBitsPerPel;
        public int dmPelsWidth;
        public int dmPelsHeight;
        public int dmDisplayFlags;
        public int dmDisplayFrequency;
        public int dmICMMethod;
        public int dmICMIntent;
        public int dmMediaType;
        public int dmDitherType;
        public int dmReserved1;
        public int dmReserved2;
        public int dmPanningWidth;
        public int dmPanningHeight;
    }
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    static extern bool EnumDisplaySettingsW(string deviceName, int modeNum, ref DEVMODE devMode);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    static extern int ChangeDisplaySettingsExW(string deviceName, ref DEVMODE devMode, IntPtr hwnd, int flags, IntPtr param);
    static DEVMODE Blank() {
        DEVMODE mode = new DEVMODE();
        mode.dmSize = (short)Marshal.SizeOf(typeof(DEVMODE));
        return mode;
    }
    public static string Run() {
        Form form = new Form();
        form.Text = "1920 x 1080";
        form.StartPosition = FormStartPosition.CenterScreen;
        form.Size = new Size(640, 360);
        form.BackColor = Color.Black;
        Label label = new Label();
        label.Text = "1920 x 1080";
        label.ForeColor = Color.White;
        label.BackColor = Color.Black;
        label.Font = new Font("Segoe UI", 48, FontStyle.Bold);
        label.AutoSize = true;
        label.Location = new Point(24, 24);
        form.Controls.Add(label);
        form.Show();
        Application.DoEvents();
        string report = "";
        DEVMODE current = Blank();
        bool haveCurrent = false;
        bool changed = false;
        try {
            haveCurrent = EnumDisplaySettingsW(null, ENUM_CURRENT_SETTINGS, ref current);
            report += "original " + current.dmPelsWidth + "x" + current.dmPelsHeight + "@" + current.dmDisplayFrequency + " enum " + haveCurrent + "\n";
            DEVMODE best = Blank();
            int bestScore = int.MaxValue;
            bool found = false;
            for (int i = 0; i < 400; i++) {
                DEVMODE mode = Blank();
                if (!EnumDisplaySettingsW(null, i, ref mode)) break;
                if (mode.dmPelsWidth < 800) continue;
                int score = Math.Abs(mode.dmPelsWidth - 1920) + Math.Abs(mode.dmPelsHeight - 1080);
                if (!found || score < bestScore || (score == bestScore && mode.dmDisplayFrequency > best.dmDisplayFrequency)) {
                    best = mode;
                    bestScore = score;
                    found = true;
                }
            }
            report += "target-found " + found + " " + best.dmPelsWidth + "x" + best.dmPelsHeight + "@" + best.dmDisplayFrequency + "\n";
            if (found) {
                int code = ChangeDisplaySettingsExW(null, ref best, IntPtr.Zero, 0, IntPtr.Zero);
                report += "change " + code + "\n";
                changed = code == 0;
            }
            if (changed) {
                DateTime start = DateTime.UtcNow;
                while ((DateTime.UtcNow - start).TotalSeconds < 25) {
                    Application.DoEvents();
                    Thread.Sleep(50);
                }
            }
        } finally {
            if (changed && haveCurrent) {
                int restored = ChangeDisplaySettingsExW(null, ref current, IntPtr.Zero, 0, IntPtr.Zero);
                report += "restore " + restored + "\n";
            }
            form.Close();
            Application.DoEvents();
        }
        return report;
    }
}
"@
[DisplaySwitch]::Run()
'@
```
